"""Gate tests for extension-points slice S3 (R2, R4, R7; AC2, AC4, AC7): the craft-gated-build skill.

The model-run cases (gated-build-outside, gated-build-fallback) are release-tier;
this file is the deterministic tier. The Pest stand-in is sh and never runs php. Body size and listing length are checked here and
also by bin/validate-skills.sh (12 KB body, 1,300 character listing).
Standard library only.
Run: python3 -m unittest discover -s evals/tests -p 'test_ext_s3.py' -v
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIX = REPO / "evals/fixtures/gated-build"
FALLBACK = REPO / "evals/fixtures/gated-build-fallback"
SKILL = REPO / "skills/craft-gated-build/SKILL.md"
AGENTS = REPO / "evals/behavior-sets/agents.json"
SCENARIOS = REPO / "evals/scenarios.json"

GATE_TEST = """<?php

use acme\\hello\\services\\GreetingService;

it('greets by name', function () {
    // expect-file: src/services/GreetingService.php
    // expect-contains: src/services/GreetingService.php Hello, Ada!
    expect((new GreetingService())->greet('Ada'))->toBe('Hello, Ada!');
});

it('greets the world for an empty name', function () {
    // expect-file: src/services/GreetingService.php
    // expect-contains: src/services/GreetingService.php Hello, world!
    expect((new GreetingService())->greet(''))->toBe('Hello, world!');
});
"""

BRIEF = """# Brief: S1 greeting service

Slice: S1
Project root: {root}
Craft version: 5.12.0
Gate commit: {gate}
Gate files: tests/Feature/S1GateTest.php
Pest command: vendor/bin/pest

## R1

The plugin MUST have a GreetingService with a greet method.
AC1: Given the name Ada, when greet('Ada') is called, then it returns Hello, Ada!.
AC2: Given an empty name, when greet('') is called, then it returns Hello, world!.

## Pointers

- skills/craftcms/references/pitfalls.md

## Rules

- Never edit a gate file.
- Stop at a passing gate.
- At most 3 rounds.
"""

FACTS = [
    ("craft-gate-writer", r"craft-gate-writer"),
    ("hand-back checker", r"bin/handback_check\.py"),
    ("git reset --hard", r"git reset --hard"),
    ("git clean -fd", r"git clean -fd"),
    ("3-round cap", r"Stop after 3 rounds"),
    ("fallback", r"craft-feature-builder"),
    ("lock check", r"git diff --quiet <gate commit> -- <gate files>"),
    ("profile file", r"skills-profile\.json"),
]


def run(cmd, cwd=REPO, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120, **kw)


def git(root, *args):
    return run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=root)


def skill_text():
    assert SKILL.is_file(), "skills/craft-gated-build/SKILL.md missing"
    return SKILL.read_text(encoding="utf-8")


def cases():
    return {c["id"]: c for c in json.loads(AGENTS.read_text(encoding="utf-8"))}


class Skill(unittest.TestCase):
    def test_skill_exists(self):
        self.assertTrue(SKILL.is_file())

    def test_body_at_most_12_kb(self):
        text = skill_text()
        body = text.split("\n---", 1)[1] if text.startswith("---") else text
        self.assertLessEqual(len(body.encode("utf-8")), 12 * 1024)

    def test_listing_at_most_1300_chars(self):
        sys.path.insert(0, str(REPO / "evals"))
        import lexical_route
        listing = lexical_route.listings(REPO / "skills").get("craft-gated-build")
        self.assertIsNotNone(listing, "no listing for craft-gated-build")
        self.assertLessEqual(len(listing), 1300)

    def test_validate_skills_passes(self):
        if not shutil.which("ruby"):
            self.skipTest("ruby missing")
        r = run(["bash", "bin/validate-skills.sh"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_facts_present(self):
        text = skill_text()
        for label, pat in FACTS:
            with self.subTest(label):
                self.assertRegex(text, pat)

    def test_reset_before_each_builder(self):
        self.assertRegex(skill_text(), r"(?im)^#+ .*before (each|every) builder|(reset|clean)[^\n]*before (each|every|the next) builder|before (each|every) builder[^\n]*(reset|clean)")

    def test_listing_keyed_on_profile_builders(self):
        head = skill_text().split("\n---", 1)[0]
        self.assertRegex(head, r"skills-profile\.json")
        self.assertRegex(head, r"(?is)\bonly\b[^.]{0,160}skills-profile\.json|skills-profile\.json[^.]{0,160}\bonly\b|skills-profile\.json[^.\n]{0,120}\bbuilders\b")


class Fixture(unittest.TestCase):
    def test_stubs_executable(self):
        for name in ("stub-unavailable", "stub-fail", "stub-ok"):
            p = FIX / "bin" / name
            with self.subTest(name):
                self.assertTrue(p.is_file())
                self.assertTrue(os.access(p, os.X_OK), f"{p} not executable")
                self.assertTrue(p.read_text().startswith("#!/bin/sh"))
        self.assertTrue(os.access(FIX / "vendor/bin/pest", os.X_OK))

    def test_isolated_pest_suite_as_the_pack_detects_it(self):
        self.assertTrue((FIX / "tests/Pest.php").is_file())
        self.assertRegex((FIX / "phpunit.xml.dist").read_text(), r'CRAFT_DB_DATABASE')
        self.assertNotRegex((FIX / "CLAUDE.md").read_text(), r"Gate tests: builder-written")

    def test_profiles_name_builders_in_order(self):
        for root, names in ((FIX, ["stub-unavailable", "stub-ok"]), (FALLBACK, ["stub-unavailable", "stub-fail"])):
            p = root / ".ai/skills-profile.json"
            with self.subTest(str(root.name)):
                self.assertEqual(run(["python3", "bin/profile_check.py", str(p)]).returncode, 0)
                prof = json.loads(p.read_text())
                self.assertEqual([b["name"] for b in prof["builders"]], names)
                for b in prof["builders"]:
                    self.assertEqual(b["command"], "./bin/" + b["name"])
                    self.assertTrue((FIX / "bin" / b["name"]).is_file())

    def test_fallback_overlay_only_replaces_the_profile(self):
        files = sorted(str(p.relative_to(FALLBACK)) for p in FALLBACK.rglob("*") if p.is_file())
        self.assertEqual(files, [".ai/skills-profile.json"])

    def test_spec_is_approved_with_one_slice_and_two_acs(self):
        prd = (FIX / "specs/2026-11-27-greeting/prd.md").read_text()
        plan = (FIX / "specs/2026-11-27-greeting/plan.md").read_text()
        for doc in (prd, plan):
            self.assertRegex(doc, r"(?m)^status: approved$")
        self.assertEqual(len(re.findall(r"(?m)^- \*\*AC\d", prd)), 2)
        self.assertEqual(len(re.findall(r"(?m)^### S\d", plan)), 1)

    def test_pest_stand_in_runs_no_php(self):
        r = run(["grep", "-rn", "php ", "evals/fixtures/gated-build/vendor/bin/pest"])
        self.assertEqual(r.returncode, 1, r.stdout)  # no match
        self.assertFalse((FIX / "vendor/pest-lite.php").exists())
        self.assertNotRegex((FIX / "vendor/bin/pest").read_text(), r"(?m)^\s*(exec\s+)?php\b")

    def test_claude_md_documents_the_markers(self):
        text = (FIX / "CLAUDE.md").read_text()
        for needle in ("expect-file:", "expect-contains:"):
            self.assertIn(needle, text)

    def test_stub_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.md"
            proj = Path(tmp) / "proj"
            shutil.copytree(FIX, proj)
            git(proj, "init", "-q")
            git(proj, "add", "-A")
            git(proj, "commit", "-qm", "fixture")
            brief.write_text(BRIEF.format(root=proj, gate="none"))
            hb = Path(tmp) / "hb.md"
            self.assertEqual(run([str(proj / "bin/stub-unavailable"), str(brief), str(hb)]).returncode, 3)
            self.assertFalse(hb.exists())
            self.assertEqual(run([str(proj / "bin/stub-fail"), str(brief), str(hb)]).returncode, 1)
            self.assertFalse(hb.exists())
            status = git(proj, "status", "--short").stdout
            self.assertIn("STUB-FAIL-PARTIAL.txt", status)
            self.assertIn("README.md", status)


class StubOkHandback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.proj = Path(self.tmp) / "proj"
        shutil.copytree(FIX, self.proj)
        git(self.proj, "init", "-q")
        git(self.proj, "add", "-A")
        git(self.proj, "commit", "-qm", "fixture")
        (self.proj / "tests/Feature/S1GateTest.php").write_text(GATE_TEST)
        git(self.proj, "add", "tests/Feature/S1GateTest.php")
        git(self.proj, "commit", "-qm", "test(gate): S1")
        self.gate = git(self.proj, "rev-parse", "--short", "HEAD").stdout.strip()
        self.brief = Path(self.tmp) / "brief.md"
        self.brief.write_text(BRIEF.format(root=self.proj, gate=self.gate))
        self.hb = Path(self.tmp) / "handback.md"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_gate_is_red_before_the_builder(self):
        r = run(["vendor/bin/pest"], cwd=self.proj)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("missing src/services/GreetingService.php", r.stdout)
        self.assertIn("Tests: 2 failed, 1 passed", r.stdout)
        # --filter matches the test name.
        f = run(["vendor/bin/pest", "--filter=empty name"], cwd=self.proj)
        self.assertEqual(f.returncode, 1)
        self.assertIn("greets the world for an empty name", f.stdout)
        self.assertNotIn("greets by name", f.stdout)
        ok = run(["vendor/bin/pest", "--filter=declares the hello handle"], cwd=self.proj)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        # A missing text reason, with the file present but wrong.
        (self.proj / "src/services").mkdir(parents=True, exist_ok=True)
        (self.proj / "src/services/GreetingService.php").write_text("<?php\n")
        t = run(["vendor/bin/pest", "--filter=empty name"], cwd=self.proj)
        self.assertEqual(t.returncode, 1)
        self.assertIn("missing text 'Hello, world!' in src/services/GreetingService.php", t.stdout)

    def test_stub_ok_handback_passes_the_checker_and_the_gate(self):
        r = run([str(self.proj / "bin/stub-ok"), str(self.brief), str(self.hb)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        chk = run(["python3", "bin/handback_check.py", "--brief", str(self.brief), str(self.hb)])
        self.assertEqual(chk.returncode, 0, chk.stdout + chk.stderr)
        text = self.hb.read_text()
        self.assertIn(f"Gate flow: locked ({self.gate})", text)
        self.assertIn("R1: PASS", text)
        self.assertIn("Builder: stub-ok", text)
        # The caller reruns the gate and the lock checks itself; both must hold.
        self.assertEqual(run(["vendor/bin/pest"], cwd=self.proj).returncode, 0)
        self.assertEqual(git(self.proj, "diff", "--quiet", self.gate, "HEAD", "--", "tests/Feature/S1GateTest.php").returncode, 0)
        self.assertEqual(git(self.proj, "diff", "--quiet", self.gate, "--", "tests/Feature/S1GateTest.php").returncode, 0)
        log = git(self.proj, "log", "--reverse", "--format=%s").stdout.splitlines()
        self.assertEqual(log[-2:], ["test(gate): S1", "feat(S1): greeting service (stub-ok)"])

    def test_stub_ok_handback_in_builder_written_flow(self):
        self.brief.write_text(BRIEF.format(root=self.proj, gate="none"))
        self.assertEqual(run([str(self.proj / "bin/stub-ok"), str(self.brief), str(self.hb)]).returncode, 0)
        chk = run(["python3", "bin/handback_check.py", "--brief", str(self.brief), str(self.hb)])
        self.assertEqual(chk.returncode, 0, chk.stdout + chk.stderr)
        self.assertIn("Gate flow: builder-written", self.hb.read_text())

    def test_checker_rejects_a_handback_missing_the_lock_line(self):
        run([str(self.proj / "bin/stub-ok"), str(self.brief), str(self.hb)])
        text = "\n".join(l for l in self.hb.read_text().splitlines() if not l.startswith("Lock check (working tree)"))
        self.hb.write_text(text + "\n")
        chk = run(["python3", "bin/handback_check.py", "--brief", str(self.brief), str(self.hb)])
        self.assertEqual(chk.returncode, 1)
        self.assertIn("missing line: Lock check (working tree)", chk.stdout)


class ReleaseCases(unittest.TestCase):
    def test_outside_case(self):
        c = cases()["gated-build-outside"]
        self.assertTrue(c["copy_cwd"])
        self.assertEqual(c["runs"], 1)
        self.assertEqual(c["cwd"], "evals/fixtures/gated-build")
        self.assertTrue((REPO / c["cwd"]).is_dir())
        self.assertIn("craft-gate-writer", c["expect_agents"])
        self.assertIn("craft-review-checker", c["expect_agents"])
        self.assertIsInstance(c["max_agents"], int)
        self.assertTrue(c["max_turns"] >= 20 and c["timeout"] >= 900)
        for tool in ("Agent", "Skill", "Bash"):
            self.assertIn(tool, c["tools"])
        pats = " ".join(p for g in c["must_match"] for p in g)
        for needle in ("test\\(gate\\)", "stub-ok", "stub-unavailable", "handback_check"):
            self.assertIn(needle, pats)

    def test_outside_case_order_regex_bites(self):
        c = cases()["gated-build-outside"]
        pat = c["must_match"][0][0]
        good = "LOG|fixture\nLOG|test(gate): S1\nLOG|feat(S1): greeting service (stub-ok)\n"
        bad = "LOG|fixture\nLOG|feat(S1): greeting service (stub-ok)\nLOG|test(gate): S1\n"
        self.assertTrue(re.search(pat, good, re.I | re.S))
        self.assertFalse(re.search(pat, bad, re.I | re.S))

    def test_fallback_case(self):
        c = cases()["gated-build-fallback"]
        self.assertTrue(c["copy_cwd"])
        self.assertEqual(c["overlay"], "evals/fixtures/gated-build-fallback")
        self.assertTrue((REPO / c["overlay"]).is_dir())
        self.assertIn("craft-feature-builder", c["expect_agents"])
        self.assertIn("craft-gate-writer", c["expect_agents"])
        self.assertLessEqual(c.get("runs", 1), 1)  # builder cases never repeat
        self.assertIsInstance(c["max_agents"], int)
        self.assertTrue(any("STUB-FAIL-PARTIAL" in p for p in c["must_not_match"]))

    def test_cases_pin_the_skill_facts(self):
        for cid in ("gated-build-outside", "gated-build-fallback"):
            facts = [f for f in cases()[cid]["facts"] if f["file"] == "skills/craft-gated-build/SKILL.md"]
            self.assertTrue(facts, cid)
            joined = " ".join(facts[0]["contains"])
            for needle in ("craft-gate-writer", "handback_check", "git reset --hard", "git clean -fd",
                           "Stop after 3 rounds", "craft-feature-builder", "skills-profile"):
                self.assertIn(needle, joined, f"{cid}: {needle}")

    def test_facts_check_passes(self):
        r = run(["python3", "evals/facts_check.py"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_release_evals_selects_the_cases(self):
        r = run(["python3", "evals/release_evals.py", "--dry-run", "--no-cache",
                 "--only", "gated-build-outside,gated-build-fallback"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("gated-build-outside", r.stdout)
        self.assertIn("gated-build-fallback", r.stdout)


class Scenarios(unittest.TestCase):
    def setUp(self):
        self.s = {s["id"]: s for s in json.loads(SCENARIOS.read_text(encoding="utf-8"))}

    def test_positive(self):
        s = self.s["gated-build-profile-builders"]
        self.assertEqual(s["expect_any"], ["craft-gated-build"])
        self.assertTrue((REPO / s["cwd"] / ".ai/skills-profile.json").is_file())

    def test_negative(self):
        s = self.s["plain-build-no-profile"]
        self.assertEqual(s["expect_none"], ["craft-gated-build"])
        self.assertFalse((REPO / s["cwd"] / ".ai/skills-profile.json").exists())
        self.assertNotIn("craft-gated-build", s["expect_any"])

    def test_scenario_check_honours_expect_none(self):
        src = (REPO / "evals/scenario_check.py").read_text(encoding="utf-8")
        self.assertIn("expect_none", src)

    def test_scenario_check_lists_both(self):
        r = run(["python3", "evals/scenario_check.py", "--dry-run", "--only",
                 "gated-build-profile-builders,plain-build-no-profile"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("2 scenario(s)", r.stdout)


if __name__ == "__main__":
    unittest.main()
