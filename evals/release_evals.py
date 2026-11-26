#!/usr/bin/env python3
"""Release-time AI evals, scoped to what changed. Run locally, at release time only.

The deterministic gates (bin/check.sh) run on every push. This script is the
other tier: it runs `claude -p` on the maintainer's seat, so it is built to
spend as few calls as possible:

  - Selection: only cases that depend on files changed since the last release
    tag (or --since REF), plus the smoke set in evals/smoke.json.
      behaviour case -> the skills named by its "facts" files, its "cwd"
                        fixture, and bin/craft-version.sh / hooks/ for all
      trigger set    -> the skill's listing (description + when_to_use) changed,
                        or the query is new
  - Cache: a passing result is stored under evals/.cache/ by a hash of the
    case and every file it depends on; unchanged cases are not rerun.
  - One run per case; a failure is retried once (--retries).
  - Repeated runs (--runs N, at most 3): only cases that opt in with "runs": N
    run more than once, and only when selected (diff-scoped or --only). The
    result shows the pass count out of N and the tokens per run; a repeated case
    passes only when every run passes, with no retries. Builder cases never opt
    in (evals/facts_check.py fails CI when one does).
  - A usage-limit message is an ERROR, not a failure: the run stops at the
    first one and reports what didn't run. Timeouts and empty answers are
    harness errors, also not failures.
  - The model-call count is printed at the end (and by --dry-run, up front).

Usage:
    python3 evals/release_evals.py --dry-run          # what would run, zero calls
    python3 evals/release_evals.py                    # run it
    python3 evals/release_evals.py --since v1.25.0 --no-cache
    python3 evals/release_evals.py --all --dry-run    # every case (no diff scoping)
    python3 evals/release_evals.py --only review-weakened-tests --runs 3

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
import tempfile
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))
from behavior_check import score  # noqa: E402  (same assertions as the standalone runner)

CACHE = REPO / "evals" / ".cache" / "release-evals.json"
SMOKE = REPO / "evals" / "smoke.json"
GLOBAL_DEPS = ("bin/craft-version.sh", "hooks/")
MAX_RUNS = 3
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
    if case.get("overlay"):
        deps.add(case["overlay"].rstrip("/") + "/")
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


ASSUME = "assume"  # --assume-changed: only the assumed files count, cases are unchanged


def case_changed(c: dict, since: str | None) -> bool:
    """New or edited since `since`. `facts` don't reach the model, so they don't count."""
    if since == ASSUME:
        return False
    if not since:
        return True
    if c["kind"] == "behaviour":
        old = old_cases(since, "behavior-sets", c["set"])
        before = next((o for o in old or [] if o.get("id") == c["id"]), None)
        strip = lambda d: {k: v for k, v in (d or {}).items() if k != "facts"}
        return before is None or strip(before) != strip(c["case"])
    old = old_cases(since, "trigger-sets", c["set"])
    return c["case"] not in (old or [])


def listing_changed(skill: str, since: str | None) -> bool:
    """Routing sees only the listing (description + when_to_use), not the body."""
    if not since or since == ASSUME:
        return True
    sys.path.insert(0, str(REPO / "evals"))
    from lexical_route import frontmatter_value
    def listing(text: str) -> tuple[str, str]:
        head = text.split("\n---", 1)[0]
        return frontmatter_value(head, "description"), frontmatter_value(head, "when_to_use")
    path = REPO / "skills" / skill / "SKILL.md"
    now = listing(path.read_text(encoding="utf-8")) if path.exists() else None
    before = git("show", f"{since}:skills/{skill}/SKILL.md")
    return now != (listing(before) if before else None)


def select(cases: list[dict], changed: set[str], smoke: set[str], everything: bool,
           since: str | None = None) -> list[dict]:
    out = []
    for c in cases:
        if everything or c["id"] in smoke:
            out.append(c)
        elif c["kind"] == "behaviour" and (touched(c["deps"], changed) or case_changed(c, since)):
            out.append(c)
        elif c["kind"] == "trigger" and (
                (touched({f"skills/{c['skill']}/SKILL.md"}, changed)
                 and (since is None or listing_changed(c["skill"], since)))
                or case_changed(c, since)):
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


def runs_for(c: dict, runs: int) -> int:
    """Runs for a selected case: --runs applies only to cases that opt in with "runs"."""
    return max(1, min(runs, int(c["case"].get("runs", 1)), MAX_RUNS)) if c["kind"] == "behaviour" else 1


def case_key(c: dict, model: str, runs: int = 1) -> str:
    h = hashlib.sha256()
    h.update(f"runs={runs}".encode())
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

def result_tokens(ev: dict) -> int:
    """Input (cache included) plus output tokens from a stream-json result event."""
    keys = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")
    per_model = ev.get("modelUsage") or {}
    if per_model:
        return sum(int(u.get(k, 0) or 0) for u in per_model.values() for k in keys)
    u = ev.get("usage") or {}
    return sum(int(u.get(k, 0) or 0) for k in
               ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


class Runner:
    def __init__(self, claude_bin: str, model: str | None, timeout: int, plugin_dir: bool):
        self.claude_bin, self.model, self.timeout, self.plugin_dir = claude_bin, model, timeout, plugin_dir
        self.calls = 0
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self.tokens: dict[int, int] = {}

    def claude(self, prompt: str, cwd: str, tools: str, max_turns: int,
               timeout: int | None = None) -> tuple[str, set[str], str, list[str]]:
        """One claude -p call: (answer text, skills invoked, error class or '', agent types started).

        Tokens for the call (every model, nested agents included) land in self.tokens[thread]."""
        with self.lock:
            self.calls += 1
        cmd = [self.claude_bin, "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--max-turns", str(max_turns), "--allowed-tools", tools]
        if tools == "Skill":
            # Routing only: with no other built-in tools the first move is a skill or an
            # answer, not two turns of Bash exploration that end the run before routing.
            cmd += ["--tools", "Skill"]
        if self.model:
            cmd += ["--model", self.model]
        if self.plugin_dir:
            cmd += ["--plugin-dir", str(REPO)]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout or self.timeout, env=env,
                                  stdin=subprocess.DEVNULL, cwd=cwd)
        except subprocess.TimeoutExpired:
            return "", set(), "harness: timeout", []
        except OSError as e:
            return "", set(), f"harness: {e.strerror or e}", []
        text, result, skills, agents = [], "", set(), []
        for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "result":
                result = ev.get("result") or ""
                self.tokens[threading.get_ident()] = result_tokens(ev)
            elif ev.get("type") == "assistant":
                for item in ev.get("message", {}).get("content", []):
                    if item.get("type") == "text":
                        text.append(item.get("text", ""))
                    elif item.get("type") == "tool_use" and item.get("name") == "Skill":
                        skills.add(item.get("input", {}).get("skill", "").split(":")[-1])
                    elif item.get("type") == "tool_use" and item.get("name") in ("Agent", "Task"):
                        # nested agents stream too (with a parent_tool_use_id), so this counts the team
                        agents.append(item.get("input", {}).get("subagent_type", "?").split(":")[-1])
        answer = result or "\n".join(text)
        stderr = proc.stderr.decode("utf-8", errors="replace")
        # A limit message can arrive as the whole answer, a result error or on stderr.
        if LIMIT_RE.search(stderr) or (LIMIT_RE.search(answer) and len(answer) < 400):
            return answer, skills, "usage limit", agents
        return answer, skills, "", agents

    def run_case(self, c: dict) -> dict:
        if c["kind"] == "behaviour":
            case = c["case"]
            cwd = str(REPO / case["cwd"]) if case.get("cwd") else "/tmp"
            tmp = None
            if case.get("copy_cwd"):
                # A builder case writes files: run in a throwaway git copy of the fixture
                # (plus an optional overlay, e.g. an approved spec), so the repo stays clean
                # and the builder can diff its own work against one commit.
                tmp = tempfile.mkdtemp(prefix="release-eval-")
                cwd = shutil.copytree(cwd, os.path.join(tmp, "project"))
                if case.get("overlay"):
                    shutil.copytree(REPO / case["overlay"], cwd, dirs_exist_ok=True)
                for git in (["init", "-q"], ["add", "-A"],
                            ["-c", "user.name=eval", "-c", "user.email=eval@example.com", "commit", "-qm", "fixture"]):
                    subprocess.run(["git", *git], cwd=cwd, check=True, capture_output=True)
            # An agent case sets its own tools and turns (e.g. "Agent,Skill,Read,Grep,Glob").
            try:
                text, skills, err, agents = self.claude(case["prompt"], cwd, case.get("tools", "Skill,Read,Grep,Glob"),
                                                        case.get("max_turns", 12), case.get("timeout"))
            finally:
                if tmp:
                    shutil.rmtree(tmp, ignore_errors=True)
            if err:
                return {"status": "error", "error": err}
            if not text.strip():
                return {"status": "error", "error": "harness: no answer text"}
            failures = score(case, text)
            if "max_agents" in case and len(agents) > case["max_agents"]:
                failures.append(f"started {len(agents)} agents, at most {case['max_agents']} allowed: {agents}")
            for want in ([case["expect_agent"]] if case.get("expect_agent") else []) + case.get("expect_agents", []):
                if want not in agents:
                    failures.append(f"agent {want} never started (started: {agents or 'none'})")
            return {"status": "fail" if failures else "pass", "failures": failures, "skills": sorted(skills),
                    "agents": agents, "answer": text, "tokens": self.tokens.pop(threading.get_ident(), 0)}
        q = c["case"]
        text, skills, err, _ = self.claude(q["query"], "/tmp", "Skill", 2)
        if err:
            return {"status": "error", "error": err}
        hit = c["skill"] in skills
        ok = hit == q["should_trigger"]
        return {"status": "pass" if ok else "fail", "skills": sorted(skills),
                "failures": [] if ok else [f"expected trigger={q['should_trigger']}, got {sorted(skills) or 'none'}"]}

    def repeat(self, c: dict, runs: int) -> dict:
        """N independent runs, no retries: pass only when every run passes."""
        results = []
        for _ in range(runs):
            if self.stopped.is_set():
                break
            r = self.run_case(c)
            results.append(r)
            if r["status"] == "error" and r["error"] == "usage limit":
                self.stopped.set()
                break
        passed = sum(r["status"] == "pass" for r in results)
        if not results:
            return {"status": "not run"}
        errors = [r for r in results if r["status"] == "error"]
        failed = any(r["status"] == "fail" for r in results)
        status = "pass" if passed == runs else "fail" if failed else "error" if errors else "not run"
        out = {"status": status, "runs": runs, "passed": passed, "tokens": [r.get("tokens", 0) for r in results],
               "failures": [f"run {i + 1}: {f}" for i, r in enumerate(results) for f in r.get("failures", [])],
               "agents": results[-1].get("agents", []), "results": results}
        if errors:
            out["error"] = errors[0]["error"]
            out["failures"] += [f"run {results.index(r) + 1}: {r['error']}" for r in errors]
        return out

    def attempt(self, c: dict, retries: int, runs: int = 1) -> dict:
        if runs > 1:
            return self.repeat(c, runs)
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
    ap.add_argument("--runs", type=int, default=1,
                    help=f"repeat cases that opt in with \"runs\" up to N times (max {MAX_RUNS}; default 1)")
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

    if not 1 <= args.runs <= MAX_RUNS:
        ap.error(f"--runs must be between 1 and {MAX_RUNS}")
    since = args.since or last_tag()
    if args.assume_changed:
        changed = set(args.assume_changed.split(","))
    else:
        changed = changed_files(since) if since else set()
    smoke = set(json.loads(SMOKE.read_text(encoding="utf-8"))) if SMOKE.exists() else set()
    cases = load_cases()
    chosen = ([c for c in cases if c["id"] in set(args.only.split(","))] if args.only
              else select(cases, changed, smoke, args.all, ASSUME if args.assume_changed else since))

    model_key = args.model or "cli-default"
    cache = {} if args.no_cache else load_cache()
    runs = {c["id"]: runs_for(c, args.runs) for c in chosen}
    keys = {c["id"]: case_key(c, model_key, runs[c["id"]]) for c in chosen}
    cached = [c for c in chosen if cache.get(keys[c["id"]], {}).get("status") == "pass"]
    to_run = [c for c in chosen if c not in cached]

    skills_changed = sorted({s for s in (skill_of(f) for f in changed) if s})
    print(f"since {since or '(no tag)'}: {len(changed)} changed file(s); skills: {', '.join(skills_changed) or 'none'}")
    nb = sum(c["kind"] == "behaviour" for c in to_run)
    print(f"selected {len(chosen)} case(s) ({len([c for c in chosen if c['id'] in smoke])} smoke), "
          f"{len(cached)} cached pass(es), {len(to_run)} to run: {nb} behaviour, {len(to_run) - nb} trigger")
    once = [c for c in to_run if runs[c["id"]] == 1]
    repeated = sum(runs[c["id"]] for c in to_run if runs[c["id"]] > 1)
    print(f"model calls: {len(once) + repeated} minimum, {len(once) * (1 + args.retries) + repeated} at most "
          f"(retries {args.retries}; repeated runs are not retried)")
    if args.dry_run:
        for c in to_run:
            print(f"  {c['kind']:9} {c['id']}" + (f"  runs: {runs[c['id']]}" if c["kind"] == "behaviour" else ""))
        return 0
    if not to_run:
        print("nothing to run")
        return 0

    claude_bin = str(Path(args.claude_bin).resolve()) if args.claude_bin else (shutil.which("claude") or "/opt/homebrew/bin/claude")
    runner = Runner(claude_bin, args.model, args.timeout, not args.no_plugin_dir)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = dict(zip([c["id"] for c in to_run], pool.map(lambda c: runner.attempt(c, args.retries, runs[c["id"]]), to_run)))

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
        if r.get("runs", 1) > 1:
            tokens = ", ".join(f"{n:,}" for n in r["tokens"])
            print(f"  {r['status'].upper():8} {c['kind']:9} {c['id']}  passed {r['passed']}/{r['runs']} | tokens per run: {tokens}")
            for f in r.get("failures", []):
                print(f"           {f}")
        elif r["status"] != "pass":
            detail = r.get("error") or "; ".join(r.get("failures", []))
            print(f"  {r['status'].upper():8} {c['kind']:9} {c['id']}  {detail}")
        elif r.get("agents"):
            print(f"  PASS     {c['kind']:9} {c['id']}  agents started: {len(r['agents'])} ({', '.join(r['agents'])})"
                  + (f" | tokens: {r['tokens']:,}" if r.get("tokens") else ""))
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
