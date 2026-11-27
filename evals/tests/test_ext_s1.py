"""Gate tests for extension-points slice S1 (R1, R8; AC1, AC8).

Contract: evals/fixtures/profile/CONTRACT.md. Standard library only.
Run: python3 -m unittest discover -s evals/tests -p 'test_ext_s1.py' -v
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROFILE = REPO / "evals/fixtures/profile"
NEUTRAL = REPO / "evals/fixtures/neutral"

INVALID = {
    "invalid-missing-version.json": "version",
    "invalid-gate-tests-enum.json": "gate_tests",
    "invalid-builder-no-command.json": "command",
    "invalid-negative-timeout.json": "timeout_minutes",
    "invalid-setup-steps-not-list.json": "setup.steps",
    "invalid-timeout-nan.json": "timeout_minutes",
}

PACK_PATHS = ("skills agents docs schema README.md CHANGELOG.md .claude-plugin "
              "project-template reference hooks")

DOC_KEYS = [
    "version", "managed_by", "gate_tests", "locked", "builder-written",
    "builders", "name", "command", "timeout_minutes", "setup.steps",
    "verdicts", "craft.answers", "hosting", "passwordless", "dev_root",
    "craft.choices", "chrome_devtools_mcp", "craft_mcp",
]

DENY_MIN = ["qwen", "mistral", "glm", "ollama", "llama", "deepseek", "gpt",
            "gemini", "vllm", "chatgpt", "openai", "codex", "copilot", "codestral",
            "devstral"]


def run(*args):
    return subprocess.run(
        ["python3", *args], cwd=REPO, capture_output=True, text=True, timeout=300
    )


class ProfileChecker(unittest.TestCase):
    def test_valid_exits_0(self):
        r = run("bin/profile_check.py", "evals/fixtures/profile/valid.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_valid_uses_every_ad2_key(self):
        v = json.loads((PROFILE / "valid.json").read_text())
        for k in ("version", "managed_by", "gate_tests", "builders", "setup",
                  "verdicts", "craft", "laravel"):
            self.assertIn(k, v)
        self.assertEqual(set(v["builders"][0]),
                         {"name", "command", "timeout_minutes"})
        self.assertIn("steps", v["setup"])
        self.assertIn("answers", v["craft"])
        self.assertIn("choices", v["craft"])

    def test_each_invalid_exits_1_and_names_key(self):
        for name, needle in INVALID.items():
            with self.subTest(fixture=name):
                r = run("bin/profile_check.py", f"evals/fixtures/profile/{name}")
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn(needle, r.stdout + r.stderr)

    def test_unsupported_schema_keyword_exits_2(self):
        r = run("bin/profile_check.py", "--schema",
                "evals/fixtures/profile/schema-unknown-keyword.json",
                "evals/fixtures/profile/valid.json")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("minimum", r.stdout + r.stderr)

    def test_real_schema_uses_only_supported_keywords(self):
        r = run("bin/profile_check.py", "evals/fixtures/profile/valid.json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_unknown_keys_kept(self):
        v = json.loads((PROFILE / "valid.json").read_text())
        self.assertIn("future_key", v)
        self.assertIn("laravel", v)


class Schema(unittest.TestCase):
    def test_schema_is_json_with_dollar_schema(self):
        p = REPO / "schema/skills-profile.schema.json"
        self.assertTrue(p.is_file(), "schema file missing")
        self.assertIn("$schema", json.loads(p.read_text()))


class Docs(unittest.TestCase):
    def test_location_and_every_key_documented(self):
        p = REPO / "docs/profile.md"
        self.assertTrue(p.is_file(), "docs/profile.md missing")
        text = p.read_text()
        self.assertIn(".ai/skills-profile.json", text)
        for key in DOC_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, text)


class NeutralChecker(unittest.TestCase):
    def test_names_a_model_fails(self):
        r = run("bin/neutral_check.py", "evals/fixtures/neutral/names-a-model.md")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("names-a-model.md", r.stdout + r.stderr)
        self.assertIn("qwen", (r.stdout + r.stderr).lower())

    def test_allowed_mention_passes(self):
        r = run("bin/neutral_check.py", "evals/fixtures/neutral/allowed-mention.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_pack_is_neutral(self):
        r = run("bin/neutral_check.py", *[p for p in PACK_PATHS.split()
                                          if (REPO / p).exists()])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_names_with_version_fails(self):
        r = run("bin/neutral_check.py", "evals/fixtures/neutral/names-with-version.md")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("qwen", (r.stdout + r.stderr).lower())

    def test_allowed_phrase_exempts_only_itself(self):
        r = run("bin/neutral_check.py", "evals/fixtures/neutral/allowed-plus-builder.md")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("qwen", (r.stdout + r.stderr).lower())

    def test_empty_allow_phrase_is_usage_error(self):
        r = run("bin/neutral_check.py", "--allow",
                "evals/fixtures/neutral/allow-empty-phrase.tsv",
                "evals/fixtures/neutral/allowed-mention.md")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_directory_scans_any_extension(self):
        r = run("bin/neutral_check.py", "evals/fixtures/neutral/dir-with-sh")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("script.sh", r.stdout + r.stderr)

    def test_letter_only_boundaries(self):
        for line in ("Qwen3", "GPT4", "gpt_4", "Llama3", "qwen-2", "ChatGPT", "Codex"):
            with self.subTest(line=line), tempfile.TemporaryDirectory() as d:
                f = Path(d) / "a.md"
                f.write_text(f"use {line} here\n")
                r = run("bin/neutral_check.py", str(f))
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.md"
            f.write_text("a word like Ruglmore is not a model\n")
            r = run("bin/neutral_check.py", str(f))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_directory_skips_binary_and_undecodable(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "nul.bin").write_bytes(b"qwen\x00\x01")
            (Path(d) / "bad.txt").write_bytes(b"\xff\xfe qwen \xff")
            r = run("bin/neutral_check.py", d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_deny_list_minimum(self):
        p = REPO / "bin/data/builder-names.txt"
        self.assertTrue(p.is_file(), "deny list missing")
        terms = {l.strip().lower() for l in p.read_text().splitlines()
                 if l.strip() and not l.lstrip().startswith("#")}
        for t in DENY_MIN:
            self.assertIn(t, terms)

    def test_allowlist_has_reasons(self):
        p = REPO / "bin/data/builder-names-allow.tsv"
        self.assertTrue(p.is_file(), "allowlist missing")
        rows = [l for l in p.read_text().splitlines()
                if l.strip() and not l.lstrip().startswith("#")]
        self.assertTrue(any(r.split("\t")[0].lower() == "gemini cli" for r in rows))
        for r in rows:
            parts = r.split("\t")
            self.assertEqual(len(parts), 2, r)
            self.assertTrue(parts[1].strip(), f"no reason: {r}")


class CheckSh(unittest.TestCase):
    def setUp(self):
        self.text = (REPO / "bin/check.sh").read_text()

    def test_must_fail_lines_present(self):
        for name in INVALID:
            with self.subTest(fixture=name):
                self.assertRegex(
                    self.text,
                    r"must_fail[^\n]*profile_check\.py[^\n]*" + name.replace(".", r"\."))
        for n in ("names-a-model\\.md", "names-with-version\\.md",
                  "allowed-plus-builder\\.md", "dir-with-sh"):
            with self.subTest(neutral=n):
                self.assertRegex(self.text, r"must_fail[^\n]*neutral_check\.py[^\n]*" + n)

    def test_gate_lines_present(self):
        self.assertRegex(self.text, r"\bgate\b[^\n]*profile_check\.py[^\n]*profile/valid\.json")
        self.assertRegex(self.text, r"\bgate\b[^\n]*neutral_check\.py[^\n]*allowed-mention\.md")
        paths = PACK_PATHS.replace(".", r"\.").replace(" ", " +")
        self.assertRegex(self.text, r"\bgate\b[^\n]*neutral_check\.py +" + paths + r"\s*($|\n)")
        for line in self.text.splitlines():
            if "neutral_check.py" in line and line.lstrip().startswith("gate"):
                self.assertNotIn("bin/data", line)
                self.assertNotIn("evals/fixtures/profile", line)

    def test_check_sh_green(self):
        r = subprocess.run(["sh", "bin/check.sh"], cwd=REPO, capture_output=True,
                           text=True, timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-1000:])


if __name__ == "__main__":
    unittest.main()
