# -*- coding: utf-8 -*-
"""Report rendering + remedy + notify: compliance paths."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexiguard import config, engine, extract, notify, remedy, report
from lexiguard import DISCLAIMER_AR, DISCLAIMER_EN

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def _risky_result():
    doc = extract.extract(os.path.join(EXAMPLES, "sample-risky-en.txt"))
    return engine.scan(doc, config.default())


class DisclaimerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _risky_result()
        cls.rems = remedy.remedies_for(cls.result)

    def test_markdown_has_disclaimer_both_ends(self):
        md = report.to_markdown(self.result, self.rems)
        self.assertIn(DISCLAIMER_EN, md)
        self.assertIn(DISCLAIMER_AR, md)
        self.assertLess(md.index(DISCLAIMER_AR), len(md) // 3)
        self.assertGreater(md.rindex(DISCLAIMER_AR), len(md) // 2)

    def test_html_has_disclaimer(self):
        import html as _html
        h = report.to_html(self.result, self.rems)
        # HTML escapes quotes — assert the escaped form is present.
        self.assertIn(_html.escape(DISCLAIMER_EN), h)
        self.assertIn(_html.escape(DISCLAIMER_AR), h)

    def test_json_has_disclaimer(self):
        data = json.loads(report.to_json(self.result, self.rems))
        self.assertEqual(data["disclaimer_en"], DISCLAIMER_EN)
        self.assertEqual(data["disclaimer_ar"], DISCLAIMER_AR)


class HtmlSafetyTests(unittest.TestCase):
    def test_hostile_snippet_is_escaped(self):
        doc = extract.extract_text(
            "1. Payment\nAll fees are non-refundable. "
            "<script>alert('pwn')</script> more text here.\n\n"
            "2. Term\nEnough body text in this clause to be kept here.\n\n"
            "3. Scope\nEnough body text in this clause to be kept here.\n")
        res = engine.scan(doc, config.default())
        self.assertTrue(res.findings)
        h = report.to_html(res)
        self.assertNotIn("<script>alert", h)
        self.assertIn("&lt;script&gt;", h)

    def test_render_unknown_format_raises(self):
        with self.assertRaises(ValueError):
            report.render(_risky_result(), "pdf")


class RemedyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _risky_result()

    def test_offline_remedy_is_template(self):
        f = self.result.sorted_findings()[0]
        rem = remedy.offline_remedy(f)
        self.assertEqual(rem.source, "offline")
        self.assertEqual(rem.text_en, f.rule.fix_en)

    def test_ai_off_by_default_no_network(self):
        # urlopen must never be reached: patch it to prove it.
        calls = []
        orig = remedy.urlopen
        remedy.urlopen = lambda *a, **k: calls.append(a) or \
            (_ for _ in ()).throw(AssertionError("network touched"))
        try:
            rems = remedy.remedies_for(self.result, use_ai=False)
        finally:
            remedy.urlopen = orig
        self.assertEqual(len(rems), len(self.result.findings))
        self.assertEqual(calls, [])
        self.assertTrue(all(r.source == "offline" for r in rems))

    def test_ai_without_key_falls_back(self):
        rems = remedy.remedies_for(self.result, use_ai=True, api_key=None)
        self.assertTrue(all(r.source == "offline" for r in rems))

    def test_gemini_requires_key(self):
        f = self.result.sorted_findings()[0]
        with self.assertRaises(ValueError):
            remedy.gemini_remedy(f, None)


class NotifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _risky_result()

    def test_skipped_without_credentials(self):
        n = notify.send(self.result)
        self.assertEqual(n.status, "skipped")

    def test_summary_leaks_no_content(self):
        summary = notify.build_summary(self.result)
        blob = json.dumps(summary, ensure_ascii=False)
        self.assertNotIn("sample-risky-en.txt", blob)
        self.assertNotIn("assigns all rights", blob)   # snippet text
        self.assertIn("LG-IP-PREPAY", blob)
        self.assertIn("not legal advice", blob)

    def test_send_fails_closed_on_network_error(self):
        class _Boom(object):
            def open(self, *a, **k):
                raise OSError("no network here")

        orig = notify.build_opener
        notify.build_opener = lambda *a, **k: _Boom()
        try:
            n = notify.send(self.result, chat_id="1", token="t0ken")
        finally:
            notify.build_opener = orig
        self.assertEqual(n.status, "error")
        self.assertNotIn("t0ken", n.detail)

    def test_payload_cap(self):
        res = self.result
        res.findings = res.findings * 40        # inflate
        summary = notify.build_summary(res)
        blob = json.dumps(summary, ensure_ascii=False)
        self.assertLessEqual(len(blob), notify.MAX_CHARS)
        self.assertLessEqual(len(summary["rule_ids"]), 40)


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        cfg = config.default()
        self.assertEqual(cfg.min_severity, "info")
        self.assertIsNone(cfg.side)

    def test_both_side_normalizes_to_none(self):
        cfg = config.Config(side="both")
        self.assertIsNone(cfg.side)

    def test_invalid_values_raise(self):
        with self.assertRaises(ValueError):
            config.Config(min_severity="critical")
        with self.assertRaises(ValueError):
            config.Config(side="third-party")

    def test_load_file(self):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"ignore_rules": ["LG-AUTORENEW"],
                       "min_severity": "low", "side": "provider"}, fh)
        try:
            cfg = config.load(path)
            self.assertEqual(cfg.ignore_rules, ("LG-AUTORENEW",))
            self.assertEqual(cfg.min_severity, "low")
            self.assertEqual(cfg.side, "provider")
        finally:
            os.unlink(path)

    def test_bad_json_raises(self):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            fh.write("{not json")
        try:
            with self.assertRaises(ValueError):
                config.load(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
