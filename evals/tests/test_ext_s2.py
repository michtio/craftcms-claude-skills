"""Gate tests for extension-points slice S2 (R3, R8; AC3) and the lock-check fix.

Contract: evals/fixtures/handback/CONTRACT.md. Standard library only.
Run: python3 -m unittest discover -s evals/tests -p 'test_ext_s2.py' -v
"""

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HB = "evals/fixtures/handback"
BRIEF = f"{HB}/brief.md"

BROKEN = {
    "missing-lock-line.md": "missing line: Lock check (working tree)",
    "missing-gate-flow.md": "missing line: Gate flow",
    "missing-r-line.md": "missing line: R5",
    "bad-status.md": "bad status: R2",
    "missing-builder.md": "missing line: Builder",
    "lock-nonzero.md": "gate touched",
}

NEW_LOCK = "git diff --quiet <gate commit> -- <gate files>"
OLD_LOCK = "git diff --quiet -- <gate files>"
AGENT_FILES = ["agents/craft-feature-builder.md", "agents/craft-code-reviewer.md",
               "agents/craft-code-reviewer-deep.md"]


def run(*args):
    return subprocess.run(["python3", *args], cwd=REPO, capture_output=True,
                          text=True, timeout=120)


def text(rel):
    p = REPO / rel
    assert p.is_file(), f"{rel} missing"
    return p.read_text(encoding="utf-8")


class HandbackChecker(unittest.TestCase):
    def test_complete_exits_0(self):
        r = run("bin/handback_check.py", "--brief", BRIEF, f"{HB}/complete.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_each_broken_exits_1_and_names_line(self):
        for name, needle in BROKEN.items():
            with self.subTest(fixture=name):
                r = run("bin/handback_check.py", "--brief", BRIEF, f"{HB}/{name}")
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn(needle, r.stdout + r.stderr)

    def test_ac3_missing_lock_line_is_not_a_pass(self):
        r = run("bin/handback_check.py", "--brief", BRIEF, f"{HB}/missing-lock-line.md")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Lock check", r.stdout + r.stderr)

    def test_usage_errors_exit_2(self):
        for label, args in {
            "no arguments": [],
            "no --brief": [f"{HB}/complete.md"],
            "no hand-back": ["--brief", BRIEF],
            "missing hand-back file": ["--brief", BRIEF, f"{HB}/does-not-exist.md"],
            "missing brief file": ["--brief", f"{HB}/nope.md", f"{HB}/complete.md"],
        }.items():
            with self.subTest(case=label):
                r = run("bin/handback_check.py", *args)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_brief_without_r_ids_exits_2(self):
        # complete.md has no "## R<n>" headings, so as a brief it has no R ids.
        r = run("bin/handback_check.py", "--brief", f"{HB}/complete.md", f"{HB}/complete.md")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_r_ids_come_from_the_brief(self):
        # Same hand-back, a brief that also expects R7: R7 is reported missing.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "brief.md"
            b.write_text(text(BRIEF) + "\n## R7\n\nAn extra requirement.\n")
            r = run("bin/handback_check.py", "--brief", str(b), f"{HB}/complete.md")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("missing line: R7", r.stdout + r.stderr)


class CheckShWiring(unittest.TestCase):
    def test_check_sh_has_gate_and_six_must_fail_lines(self):
        sh = text("bin/check.sh")
        lines = [l for l in sh.splitlines() if "handback_check.py" in l]
        self.assertTrue(any(l.startswith("gate") and "complete.md" in l for l in lines),
                        "no gate line for complete.md")
        for name in BROKEN:
            with self.subTest(fixture=name):
                self.assertTrue(
                    any(l.startswith("must_fail") and name in l and "--brief" in l
                        for l in lines), f"no must_fail line for {name}")


class Docs(unittest.TestCase):
    def test_outside_builders_has_protocol(self):
        t = text("docs/outside-builders.md")
        self.assertIn("<command> <brief-file> <handback-file>", t)
        self.assertIn("handback_check.py", t)
        self.assertRegex(t, r"(?m)^\|\s*0\s*\|.*done")
        self.assertRegex(t, r"(?m)^\|\s*3\s*\|.*unavailable")
        self.assertRegex(t, r"(?mi)^\|.*other.*\|.*failed")
        self.assertRegex(t, r"timeout_minutes")

    def test_brief_format_has_fields_and_handback_lines(self):
        t = text("docs/brief-format.md")
        for field in ("Slice:", "Gate commit:", "Gate files:", "Pest command:",
                      "Project root:", "Craft version:", "## R<n>"):
            with self.subTest(field=field):
                self.assertIn(field, t)
        for line in ("Gate flow:", "Lock check (committed): exit",
                     "Lock check (working tree): exit", "R<n>: PASS|FAIL|PENDING",
                     "Builder:"):
            with self.subTest(line=line):
                self.assertIn(line, t)

    def test_docs_are_standalone(self):
        # Readable by a builder that is not Claude: no "Claude" in the format docs.
        for rel in ("docs/brief-format.md", "docs/outside-builders.md"):
            with self.subTest(doc=rel):
                self.assertNotIn("claude", text(rel).lower())


class LockFix(unittest.TestCase):
    def test_new_form_in_agents_and_docs(self):
        for rel in AGENT_FILES + ["docs/agents.md"]:
            with self.subTest(file=rel):
                self.assertIn(NEW_LOCK, text(rel))

    def test_old_working_tree_form_gone(self):
        for rel in AGENT_FILES + ["docs/agents.md"]:
            with self.subTest(file=rel):
                self.assertNotIn(OLD_LOCK, text(rel))
        for p in sorted((REPO / "agents").glob("*.md")):
            with self.subTest(file=p.name):
                self.assertNotIn(OLD_LOCK, p.read_text(encoding="utf-8"))

    def test_committed_form_stays(self):
        for rel in ("agents/craft-feature-builder.md", "docs/agents.md"):
            with self.subTest(file=rel):
                self.assertIn("git diff --quiet <gate commit> HEAD -- <gate files>", text(rel))

    def test_facts_pin_the_new_form(self):
        j = text("evals/behavior-sets/agents.json")
        self.assertIn("git diff --quiet <gate commit> -- <gate files>", j)


if __name__ == "__main__":
    unittest.main()
