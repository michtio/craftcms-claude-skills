"""Gate tests for extension-points slice S4 (R5, R6, R7; AC5, AC6, AC7): craft-project-setup reads the profile.

The model-run cases (setup-with-profile, setup-rerun-update) are release-tier;
this file is the deterministic tier. Nothing here runs php or a model.
Standard library only.
Run: python3 -m unittest discover -s evals/tests -p 'test_ext_s4.py' -v
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WITH = REPO / "evals/fixtures/setup-profile"
RERUN = REPO / "evals/fixtures/setup-rerun"
AGENTS = REPO / "evals/behavior-sets/agents.json"
SKILL = "skills/craft-project-setup/SKILL.md"
REFS = {
    "detection": "skills/craft-project-setup/references/detection.md",
    "generation": "skills/craft-project-setup/references/generation.md",
    "attribution": "skills/craft-project-setup/references/attribution-and-upgrades.md",
}
CASES = ("setup-with-profile", "setup-rerun-update")


def run(cmd, cwd=REPO, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120, **kw)


def cases():
    return {c["id"]: c for c in json.loads(AGENTS.read_text(encoding="utf-8"))}


def listing_fields(text):
    out = {}
    head = text.split("\n---", 1)[0]
    for key in ("description", "when_to_use"):
        m = re.search(rf"(?m)^{key}:\s*(.*)$", head)
        out[key] = m.group(1) if m else None
    return out


class Fixtures(unittest.TestCase):
    def test_both_profiles_validate(self):
        for root in (WITH, RERUN):
            with self.subTest(root.name):
                r = run(["python3", "bin/profile_check.py", str(root / ".ai/skills-profile.json")])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_both_are_plugins_with_an_isolated_pest_suite(self):
        for root in (WITH, RERUN):
            with self.subTest(root.name):
                self.assertEqual(json.loads((root / "composer.json").read_text())["type"], "craft-plugin")
                self.assertTrue((root / "tests/Pest.php").is_file())
                self.assertRegex((root / "phpunit.xml.dist").read_text(), r'name="CRAFT_DB_DATABASE"')

    def test_with_profile_answers_the_opposite_of_the_default(self):
        p = json.loads((WITH / ".ai/skills-profile.json").read_text())
        self.assertEqual(p["gate_tests"], "builder-written")
        self.assertTrue(p["craft"]["answers"]["dev_root"])
        self.assertEqual(p["setup"]["steps"], [{"name": "team-step", "command": "./bin/team-step"}])
        self.assertFalse((WITH / "CLAUDE.md").exists())  # first-time setup
        self.assertFalse((WITH / ".claude").exists())

    def test_rerun_is_configured_and_the_profile_changes_one_choice(self):
        p = json.loads((RERUN / ".ai/skills-profile.json").read_text())
        self.assertEqual(p["gate_tests"], "locked")
        self.assertNotIn("steps", p.get("setup", {}))
        md = (RERUN / "CLAUDE.md").read_text()
        self.assertTrue(md.startswith("<!-- craftcms-claude-skills v"))
        self.assertEqual(len(re.findall(r"(?m)^.*Gate tests:.*$", md)), 1)
        self.assertIn("Gate tests: builder-written", md)
        rules = sorted((RERUN / ".claude/rules").glob("*.md"))
        self.assertTrue(rules)
        for f in rules:
            self.assertTrue(f.read_text().startswith("<!-- craftcms-claude-skills -->"))
        self.assertIn("craftcms-claude-skills", json.loads((RERUN / "composer.json").read_text())["extra"])

    def test_rerun_has_one_hand_edited_section_outside_the_generated_ones(self):
        md = (RERUN / "CLAUDE.md").read_text()
        self.assertEqual(md.count("HAND-EDITED"), 1)
        self.assertRegex(md, r"(?ms)^## Team notes\n\nHAND-EDITED:[^\n]+\n?\Z")

    def test_no_model_machine_or_vendor_names(self):
        deny = re.compile(r"qwen|mistral|glm|ollama|llama|deepseek|gpt|gemini|claude-3|openai|codex|copilot", re.I)
        for root in (WITH, RERUN):
            for f in root.rglob("*"):
                if f.is_file():
                    with self.subTest(str(f.relative_to(REPO))):
                        self.assertIsNone(deny.search(f.read_text()))


class TeamStep(unittest.TestCase):
    def test_executable_sh_script(self):
        p = WITH / "bin/team-step"
        self.assertTrue(os.access(p, os.X_OK))
        self.assertTrue(p.read_text().startswith("#!/bin/sh"))

    def test_writes_only_the_marker_and_records_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "p"
            shutil.copytree(WITH, proj)
            before = sorted(str(f.relative_to(proj)) for f in proj.rglob("*") if f.is_file())
            r = run(["./bin/team-step"], cwd=proj)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")
            after = sorted(str(f.relative_to(proj)) for f in proj.rglob("*") if f.is_file())
            self.assertEqual(sorted(set(after) - set(before)), [".team-step-ran"])
            self.assertEqual(sorted(set(before) - set(after)), [])
            self.assertIn("CLAUDE.md present: no; rules files: 0", (proj / ".team-step-ran").read_text())
            # Run after generation: the marker shows what existed.
            (proj / ".claude/rules").mkdir(parents=True)
            (proj / "CLAUDE.md").write_text("x\n")
            (proj / ".claude/rules/a.md").write_text("x\n")
            (proj / ".claude/rules/b.md").write_text("x\n")
            run(["./bin/team-step"], cwd=proj)
            self.assertEqual((proj / ".team-step-ran").read_text().strip(),
                             "team-step ran; CLAUDE.md present: yes; rules files: 2")


class Facts(unittest.TestCase):
    def test_facts_check_passes(self):
        r = run(["python3", "evals/facts_check.py"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_both_cases_pin_each_reference_and_the_skill(self):
        for cid in CASES:
            files = {f["file"] for f in cases()[cid]["facts"]}
            for rel in (*REFS.values(), SKILL):
                with self.subTest(case=cid, file=rel):
                    self.assertIn(rel, files)

    def test_pinned_facts_hold_in_the_files(self):
        for cid in CASES:
            for f in cases()[cid]["facts"]:
                text = (REPO / f["file"]).read_text(encoding="utf-8")
                for pat in f.get("contains", []):
                    with self.subTest(case=cid, file=f["file"], pattern=pat[:70]):
                        self.assertRegex(text, re.compile(pat, re.M))

    def test_each_required_fact_is_pinned(self):
        joined = {k: " ".join(p for c in CASES for f in cases()[c]["facts"] if f["file"] == v
                              for p in f.get("contains", [])) for k, v in REFS.items()}
        for needle in ("skills-profile", "profile_check", r"CLAUDE_SKILL_DIR", "half-appl", "gate_tests",
                       "dev_root", "hosting", "passwordless", "Gate tests: \\*\\*only when"):
            self.assertIn(needle, joined["detection"], needle)
        for needle in ("gate_tests", "setup", "review", "last"):
            self.assertIn(needle, joined["generation"], needle)
        for needle in ("per-file", "hand-edited", "re-?run"):
            self.assertIn(needle, joined["attribution"], needle)

    def test_the_profile_step_is_in_step_1_not_step_2(self):
        text = (REPO / REFS["detection"]).read_text()
        step1 = text.split("## Step 2", 1)[0]
        self.assertIn(".ai/skills-profile.json", step1)
        self.assertIn("bin/profile_check.py", step1)

    def test_profile_check_runs_from_the_skill_folder_like_craft_gated_build(self):
        text = (REPO / REFS["detection"]).read_text()
        self.assertIn("${CLAUDE_SKILL_DIR}/../../bin/", text)
        self.assertTrue((REPO / "skills/craft-project-setup/../../bin/profile_check.py").is_file())

    def test_existing_setup_facts_stay_pinned(self):
        # R7: the 1.31.0 gate-tests facts are kept on both cases, unchanged.
        for cid in CASES:
            joined = " ".join(p for f in cases()[cid]["facts"] for p in f.get("contains", []))
            for needle in ("Gate tests: \\*\\*only when the project has an isolated Pest suite\\*\\*",
                           "with no suite, don't ask and write nothing",
                           "exactly one `Gate tests: locked` or `Gate tests: builder-written` line"):
                self.assertIn(needle, joined)


class Listing(unittest.TestCase):
    def test_description_and_when_to_use_match_v1_31_0(self):
        tag = run(["git", "rev-parse", "--verify", "-q", "v1.31.0^{commit}"])
        if tag.returncode != 0:
            self.skipTest("tag v1.31.0 not available")
        old = run(["git", "show", f"v1.31.0:{SKILL}"]).stdout
        new = (REPO / SKILL).read_text(encoding="utf-8")
        a, b = listing_fields(old), listing_fields(new)
        self.assertIsNotNone(a["description"])
        self.assertIsNotNone(a["when_to_use"])
        self.assertEqual(b["description"], a["description"])
        self.assertEqual(b["when_to_use"], a["when_to_use"])

    def test_skill_name_unchanged(self):
        self.assertRegex((REPO / SKILL).read_text(), r"(?m)^name: craft-project-setup$")


class ReleaseCases(unittest.TestCase):
    def common(self, c):
        self.assertTrue(c["copy_cwd"])
        self.assertEqual(c["runs"], 1)
        self.assertTrue((REPO / c["cwd"]).is_dir())
        self.assertIn("Skill", c["tools"])
        self.assertIn("Bash", c["tools"])
        self.assertIn("craft-project-setup", c["prompt"])
        self.assertTrue(c["max_turns"] >= 20 and c["timeout"] >= 900)
        self.assertEqual(c["max_agents"], 0)
        self.assertNotIn("expect_agents", c)

    def test_with_profile(self):
        c = cases()["setup-with-profile"]
        self.common(c)
        self.assertEqual(c["cwd"], "evals/fixtures/setup-profile")
        for needle in ("ASKED|", "GATELINES|", "GATE|", "MARKER|", "STATUS|", "team-step"):
            self.assertIn(needle, c["prompt"])
        self.assertIn("non-interactively", c["prompt"])
        pats = " ".join(p for g in c["must_match"] for p in g)
        for needle in ("GATELINES", "Gate tests: builder-written", "team-step ran", "CLAUDE", r"\.team-step-ran", "review"):
            self.assertIn(needle, pats)
        forbid = " ".join(c["must_not_match"])
        for needle in ("ASKED", "gate", "Gate tests: locked", "CLAUDE\\.md present: no"):
            self.assertIn(needle, forbid)

    def test_with_profile_assertions_bite(self):
        c = cases()["setup-with-profile"]
        good = ("Review: CLAUDE.md, rules, then extra step team-step.\n"
                "GATELINES|1\nGATE|- Gate tests: builder-written\nDEVROOT|- devRootPath: ~/dev\n"
                "MARKER|team-step ran; CLAUDE.md present: yes; rules files: 3\nSTATUS|?? .team-step-ran\n")
        def fails(text):
            ok = all(any(re.search(p, text, re.I | re.S) for p in g) for g in c["must_match"])
            bad = any(re.search(p, text, re.I | re.S) for p in c["must_not_match"])
            return (not ok) or bad
        self.assertFalse(fails(good))
        self.assertTrue(fails(good + "ASKED|Should builds lock their gate tests?\n"))
        self.assertTrue(fails(good.replace("builder-written", "locked")))
        self.assertTrue(fails(good.replace("present: yes", "present: no")))
        self.assertTrue(fails(good.replace("GATELINES|1", "GATELINES|2")))
        self.assertTrue(fails(good.replace("STATUS|?? .team-step-ran\n", "")))

    def test_rerun(self):
        c = cases()["setup-rerun-update"]
        self.common(c)
        self.assertEqual(c["cwd"], "evals/fixtures/setup-rerun")
        for needle in ("SHOWN|", "DIFFSTAT|", "git diff --stat", "HAND-EDITED", "rerun"):
            self.assertIn(needle, c["prompt"])

    def test_rerun_assertions_bite(self):
        c = cases()["setup-rerun-update"]
        good = ("SHOWN|CLAUDE.md|Gate tests: builder-written -> locked\n"
                "DIFFSTAT| CLAUDE.md | 2 +-\nDIFFSTAT| 1 file changed, 1 insertion(+), 1 deletion(-)\n"
                "CHANGES|2\nCHANGE|-- Gate tests: builder-written\nCHANGE|+- Gate tests: locked\n"
                "HANDEDIT|1\nSTATUS| M CLAUDE.md\n")
        def fails(text):
            ok = all(any(re.search(p, text, re.I | re.S) for p in g) for g in c["must_match"])
            bad = any(re.search(p, text, re.I | re.S) for p in c["must_not_match"])
            return (not ok) or bad
        self.assertFalse(fails(good), [p for g in c["must_match"] for p in g])
        self.assertTrue(fails(good + "SHOWN|.claude/rules/testing.md|rewrite\n"))
        self.assertTrue(fails(good.replace("1 file changed", "2 files changed")))
        self.assertTrue(fails(good.replace("CHANGES|2", "CHANGES|4")))
        self.assertTrue(fails(good.replace("HANDEDIT|1", "HANDEDIT|0")))
        self.assertTrue(fails(good + "CHANGE|-HAND-EDITED: releases\n"))
        self.assertTrue(fails(good + "STATUS|?? stray.md\n"))

    def test_at_most_two_new_cases_and_release_evals_selects_them(self):
        r = run(["python3", "evals/release_evals.py", "--dry-run", "--no-cache", "--only", ",".join(CASES)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for cid in CASES:
            self.assertIn(cid, r.stdout)

    def test_existing_scenarios_untouched(self):
        s = {x["id"]: x for x in json.loads((REPO / "evals/scenarios.json").read_text())}
        self.assertEqual(s["setup-with-profile-builders"]["expect_any"], ["craft-project-setup"])
        self.assertEqual(s["onboard-dev-claude"]["expect_any"], ["craft-project-setup"])


if __name__ == "__main__":
    unittest.main()
