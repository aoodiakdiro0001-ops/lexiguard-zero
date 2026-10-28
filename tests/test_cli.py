# -*- coding: utf-8 -*-
"""CLI end-to-end tests (subprocess)."""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXAMPLES = os.path.join(ROOT, "examples")


def run(*argv):
    env = dict(os.environ)
    env.pop("GEMINI_API_KEY", None)
    env.pop("TELEGRAM_BOT_TOKEN", None)
    env.pop("TELEGRAM_CHAT_ID", None)
    return subprocess.run([sys.executable, "-m", "lexiguard"] + list(argv),
                          cwd=ROOT, env=env, capture_output=True,
                          text=True, timeout=60)


class CliScanTests(unittest.TestCase):
    def test_scan_risky(self):
        p = run("scan", "examples/sample-risky-en.txt")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("URGENT", p.stdout)
        self.assertIn("LG-IP-PREPAY", p.stdout)
        self.assertIn("Not legal advice", p.stdout)

    def test_scan_arabic(self):
        p = run("scan", "examples/sample-risky-ar.txt")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("LG-IP-PREPAY", p.stdout)
        self.assertIn("البند 2", p.stdout)

    def test_fail_on_gate(self):
        p = run("scan", "examples/sample-risky-en.txt", "--fail-on", "high")
        self.assertEqual(p.returncode, 2)
        p2 = run("scan", "examples/sample-fair-en.txt", "--fail-on", "high")
        self.assertEqual(p2.returncode, 0)

    def test_missing_file_fails_clean(self):
        p = run("scan", "no-such-file.txt")
        self.assertEqual(p.returncode, 1)
        self.assertIn("error", p.stderr.lower())

    def test_ignore_flag(self):
        p = run("scan", "examples/sample-fair-en.txt",
                "--ignore", "LG-SETTLE-DISTANT-FORUM")
        self.assertEqual(p.returncode, 0)
        self.assertIn("(no known patterns", p.stdout)


class CliReportTests(unittest.TestCase):
    def test_report_writes_file_with_disclaimer(self):
        fd, out = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        try:
            p = run("report", "examples/sample-risky-ar.txt",
                    "-f", "markdown", "-o", out)
            self.assertEqual(p.returncode, 0, p.stderr)
            with open(out, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("Not legal advice", text)
            self.assertIn("ليست استشارة قانونية", text)
            self.assertIn("counter-clause", text.lower())
        finally:
            os.unlink(out)

    def test_report_json_stdout(self):
        p = run("report", "examples/sample-fair-en.txt", "-f", "json")
        self.assertEqual(p.returncode, 0, p.stderr)
        import json
        data = json.loads(p.stdout)
        self.assertIn("disclaimer_en", data)
        self.assertEqual(data["band"], "watch")


class CliDoctorTests(unittest.TestCase):
    def test_doctor_runs(self):
        p = run("doctor")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("privacy", p.stdout)
        self.assertIn("Not legal advice", p.stdout)


if __name__ == "__main__":
    unittest.main()
