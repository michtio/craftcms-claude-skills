#!/usr/bin/env python3
"""Release-time AI evals, scoped to what changed. Run locally, at release time only.

The deterministic gates (bin/check.sh) run on every push. This script is the
other tier: it runs `claude -p` on the maintainer's seat, so it is built to
spend as few calls as possible:

  - Selection: only cases that depend on files changed since the last release
    tag (or --since REF), plus the smoke set in evals/smoke.json.
      behaviour case -> the skills named by its "facts" files, its "cwd"
                        fixture, and bin/craft-version.sh / hooks/ for all
      trigger set    -> skills/<set>/SKILL.md (its listing) changed
  - Cache: a passing result is stored under evals/.cache/ by a hash of the
    case and every file it depends on; unchanged cases are not rerun.
  - One run per case; a failure is retried once (--retries).
  - A usage-limit message is an ERROR, not a failure: the run stops at the
    first one and reports what didn't run. Timeouts and empty answers are
    harness errors, also not failures.
  - The model-call count is printed at the end (and by --dry-run, up front).

Usage:
    python3 evals/release_evals.py --dry-run          # what would run, zero calls
    python3 evals/release_evals.py                    # run it
    python3 evals/release_evals.py --since v1.25.0 --no-cache
    python3 evals/release_evals.py --all --dry-run    # every case (no diff scoping)

Route A/B for changed listings is separate: python3 evals/route.py --changed-only
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))
from behavior_check import score  # noqa: E402  (same assertions as the standalone runner)

CACHE = REPO / "evals" / ".cache" / "release-evals.json"
SMOKE = REPO / "evals" / "smoke.json"
GLOBAL_DEPS = ("bin/craft-version.sh", "hooks/")
LIMIT_RE = re.compile(
    r"(hit your (?:\d+-hour |weekly |session )?limit|usage limit|rate[ _-]?limit(?:ed)?|"
    r"limit (?:reached|resets)|overloaded_error|quota exceeded)", re.I)


# ----------------------------------------------------------------------------
# selection
# ----------------------------------------------------------------------------

def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout


def last_tag() -> str:
    return git("describe", "--tags", "--abbrev=0", "--match", "v*").strip()


def changed_files(since: str) -> set[str]:
    files = set(git("diff", "--name-only", since).split())          # committed + unstaged vs the tag
    files |= set(git("ls-files", "--others", "--exclude-standard").split())  # new, untracked
    return files


def skill_of(path: str) -> str | None:
    parts = path.split("/")
    return parts[1] if len(parts) > 2 and parts[0] == "skills" else None


def behaviour_deps(case: dict) -> set[str]:
    deps = set(GLOBAL_DEPS)
    for fact in case.get("facts", []):
        s = skill_of(fact["file"])
        deps.add(f"skills/{s}/" if s else fact["file"])
    if case.get("cwd"):
        deps.add(case["cwd"].rstrip("/") + "/")
    return deps


def touched(deps: set[str], changed: set[str]) -> bool:
    return any(c == d or (d.endswith("/") and c.startswith(d)) for d in deps for c in changed)


def load_cases() -> list[dict]:
    """Every behaviour case and trigger query as a uniform job description."""
    cases = []
    for f in sorted((REPO / "evals" / "behavior-sets").glob("*.json")):
        for c in json.loads(f.read_text(encoding="utf-8")):
            cases.append({"kind": "behaviour", "id": c["id"], "set": f.name, "case": c, "deps": behaviour_deps(c)})
    for f in sorted((REPO / "evals" / "trigger-sets").glob("*.json")):
        skill = f.stem
        if not (REPO / "skills" / skill / "SKILL.md").exists():
            continue
        for i, q in enumerate(json.loads(f.read_text(encoding="utf-8"))):
            cases.append({"kind": "trigger", "id": f"{skill}#{i}", "set": f.name, "skill": skill, "case": q,
                          "deps": {f"skills/{skill}/SKILL.md", f"evals/trigger-sets/{f.name}"}})
    return cases


def old_cases(since: str | None, kind_dir: str, set_name: str, cache: dict = {}) -> list | None:
    """The set file's cases at `since`, or None when it didn't exist there."""
    key = (since, kind_dir, set_name)
    if key not in cache:
        raw = git("show", f"{since}:evals/{kind_dir}/{set_name}") if since else ""
        try:
            cache[key] = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            cache[key] = None
    return cache[key]


def case_changed(c: dict, since: str | None) -> bool:
    """New or edited since `since`. `facts` don't reach the model, so they don't count."""
    if not since:
        return True
    if c["kind"] == "behaviour":
        old = old_cases(since, "behavior-sets", c["set"])
        before = next((o for o in old or [] if o.get("id") == c["id"]), None)
        strip = lambda d: {k: v for k, v in (d or {}).items() if k != "facts"}
        return before is None or strip(before) != strip(c["case"])
    old = old_cases(since, "trigger-sets", c["set"])
    return c["case"] not in (old or [])


def select(cases: list[dict], changed: set[str], smoke: set[str], everything: bool,
           since: str | None = None) -> list[dict]:
    out = []
    for c in cases:
        if everything or c["id"] in smoke:
            out.append(c)
        elif c["kind"] == "behaviour" and (touched(c["deps"], changed) or case_changed(c, since)):
            out.append(c)
        elif c["kind"] == "trigger" and (touched({f"skills/{c['skill']}/SKILL.md"}, changed) or case_changed(c, since)):
            out.append(c)
    return out


# ----------------------------------------------------------------------------
# cache
# ----------------------------------------------------------------------------

def file_digest(path: Path, h) -> None:
    if path.is_dir():
        for p in sorted(path.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                h.update(str(p.relative_to(REPO)).encode())
                h.update(p.read_bytes())
    elif path.is_file():
        h.update(path.read_bytes())


def case_key(c: dict, model: str) -> str:
    h = hashlib.sha256()
    h.update(json.dumps(c["case"], sort_keys=True).encode())
    h.update(model.encode())
    for d in sorted(c["deps"]):
        file_digest(REPO / d, h)
    return h.hexdigest()


def load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


# ----------------------------------------------------------------------------
# running
# ----------------------------------------------------------------------------

class Runner:
    def __init__(self, claude_bin: str, model: str | None, timeout: int, plugin_dir: bool):
        self.claude_bin, self.model, self.timeout, self.plugin_dir = claude_bin, model, timeout, plugin_dir
        self.calls = 0
        self.stopped = threading.Event()
        self.lock = threading.Lock()

    def claude(self, prompt: str, cwd: str, tools: str, max_turns: int) -> tuple[str, set[str], str]:
        """One claude -p call: (answer text, skills invoked, error class or '')."""
        with self.lock:
            self.calls += 1
        cmd = [self.claude_bin, "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--max-turns", str(max_turns), "--allowed-tools", tools]
        if self.model:
            cmd += ["--model", self.model]
        if self.plugin_dir:
            cmd += ["--plugin-dir", str(REPO)]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=self.timeout, env=env,
                                  stdin=subprocess.DEVNULL, cwd=cwd)
        except subprocess.TimeoutExpired:
            return "", set(), "harness: timeout"
        except OSError as e:
            return "", set(), f"harness: {e.strerror or e}"
        text, result, skills = [], "", set()
        for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "result":
                result = ev.get("result") or ""
            elif ev.get("type") == "assistant":
                for item in ev.get("message", {}).get("content", []):
                    if item.get("type") == "text":
                        text.append(item.get("text", ""))
                    elif item.get("type") == "tool_use" and item.get("name") == "Skill":
                        skills.add(item.get("input", {}).get("skill", "").split(":")[-1])
        answer = result or "\n".join(text)
        stderr = proc.stderr.decode("utf-8", errors="replace")
        # A limit message can arrive as the whole answer, a result error or on stderr.
        if LIMIT_RE.search(stderr) or (LIMIT_RE.search(answer) and len(answer) < 400):
            return answer, skills, "usage limit"
        return answer, skills, ""

    def run_case(self, c: dict) -> dict:
        if c["kind"] == "behaviour":
            case = c["case"]
            cwd = str(REPO / case["cwd"]) if case.get("cwd") else "/tmp"
            text, skills, err = self.claude(case["prompt"], cwd, "Skill,Read,Grep,Glob", 12)
            if err:
                return {"status": "error", "error": err}
            if not text.strip():
                return {"status": "error", "error": "harness: no answer text"}
            failures = score(case, text)
            return {"status": "fail" if failures else "pass", "failures": failures, "skills": sorted(skills)}
        q = c["case"]
        text, skills, err = self.claude(q["query"], "/tmp", "Skill", 2)
        if err:
            return {"status": "error", "error": err}
        hit = c["skill"] in skills
        ok = hit == q["should_trigger"]
        return {"status": "pass" if ok else "fail", "skills": sorted(skills),
                "failures": [] if ok else [f"expected trigger={q['should_trigger']}, got {sorted(skills) or 'none'}"]}

    def attempt(self, c: dict, retries: int) -> dict:
        r = {"status": "not run"}
        for n in range(1 + retries):
            if self.stopped.is_set():
                return r if n else {"status": "not run"}
            r = self.run_case(c)
            r["attempts"] = n + 1
            if r["status"] == "error" and r["error"] == "usage limit":
                self.stopped.set()
                return r
            if r["status"] == "pass":
                return r
        return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="git ref to diff against (default: the last v* tag)")
    ap.add_argument("--all", action="store_true", help="every case, no diff scoping (expensive)")
    ap.add_argument("--dry-run", action="store_true", help="list what would run and the call count; zero model calls")
    ap.add_argument("--no-cache", action="store_true", help="ignore cached passes")
    ap.add_argument("--retries", type=int, default=1, help="retries for a failed case (default: 1)")
    ap.add_argument("--workers", type=int, default=3, help="concurrent claude -p calls (default: 3)")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--model", default=None, help="model alias for claude -p (default: the CLI default)")
    ap.add_argument("--claude-bin", default=None)
    ap.add_argument("--no-plugin-dir", action="store_true",
                    help="don't load this working tree with --plugin-dir (then the INSTALLED plugin is tested)")
    ap.add_argument("--only", help="comma-separated case ids (behaviour id or skill#index)")
    ap.add_argument("--assume-changed", help="comma-separated paths to treat as the changed files (tests, what-ifs)")
    ap.add_argument("--out", help="write full results JSON here")
    args = ap.parse_args()

    since = args.since or last_tag()
    if args.assume_changed:
        changed = set(args.assume_changed.split(","))
    else:
        changed = changed_files(since) if since else set()
    smoke = set(json.loads(SMOKE.read_text(encoding="utf-8"))) if SMOKE.exists() else set()
    cases = load_cases()
    chosen = ([c for c in cases if c["id"] in set(args.only.split(","))] if args.only
              else select(cases, changed, smoke, args.all, None if args.assume_changed else since))

    model_key = args.model or "cli-default"
    cache = {} if args.no_cache else load_cache()
    keys = {c["id"]: case_key(c, model_key) for c in chosen}
    cached = [c for c in chosen if cache.get(keys[c["id"]], {}).get("status") == "pass"]
    to_run = [c for c in chosen if c not in cached]

    skills_changed = sorted({s for s in (skill_of(f) for f in changed) if s})
    print(f"since {since or '(no tag)'}: {len(changed)} changed file(s); skills: {', '.join(skills_changed) or 'none'}")
    nb = sum(c["kind"] == "behaviour" for c in to_run)
    print(f"selected {len(chosen)} case(s) ({len([c for c in chosen if c['id'] in smoke])} smoke), "
          f"{len(cached)} cached pass(es), {len(to_run)} to run: {nb} behaviour, {len(to_run) - nb} trigger")
    print(f"model calls: {len(to_run)} minimum, {len(to_run) * (1 + args.retries)} at most (retries {args.retries})")
    if args.dry_run:
        for c in to_run:
            print(f"  {c['kind']:9} {c['id']}")
        return 0
    if not to_run:
        print("nothing to run")
        return 0

    claude_bin = str(Path(args.claude_bin).resolve()) if args.claude_bin else (shutil.which("claude") or "/opt/homebrew/bin/claude")
    runner = Runner(claude_bin, args.model, args.timeout, not args.no_plugin_dir)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = dict(zip([c["id"] for c in to_run], pool.map(lambda c: runner.attempt(c, args.retries), to_run)))

    for c in to_run:
        r = results[c["id"]]
        if r["status"] == "pass":
            cache[keys[c["id"]]] = {"status": "pass", "id": c["id"]}
    if not args.no_cache:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        (CACHE.parent / ".gitignore").write_text("*\n")  # local only, never committed
        CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    counts = {"pass": 0, "fail": 0, "error": 0, "not run": 0}
    limit_errors = 0
    for c in to_run:
        r = results[c["id"]]
        counts[r["status"]] += 1
        limit_errors += r.get("error") == "usage limit"
        if r["status"] != "pass":
            detail = r.get("error") or "; ".join(r.get("failures", []))
            print(f"  {r['status'].upper():8} {c['kind']:9} {c['id']}  {detail}")
    if args.out:
        Path(args.out).write_text(json.dumps({c["id"]: results[c["id"]] for c in to_run}, indent=2), encoding="utf-8")

    errs = f"errors: {counts['error']}" + (f" ({limit_errors} usage limit)" if limit_errors else "")
    print(f"passed: {counts['pass'] + len(cached)} ({len(cached)} cached) | failed: {counts['fail']} | {errs} | "
          f"not run: {counts['not run']} | model calls: {runner.calls}")
    if runner.stopped.is_set():
        print("stopped at a usage limit: rerun after the reset; cached passes are kept")
        return 3
    return 1 if counts["fail"] or counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
