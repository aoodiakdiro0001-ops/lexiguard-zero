# -*- coding: utf-8 -*-
"""Engine tests: detection, scoring math, bands, honesty of 'none'."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexiguard import config, engine, extract

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def _scan_file(name):
    doc = extract.extract(os.path.join(EXAMPLES, name))
    return engine.scan(doc, config.default())


class RiskyEnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _scan_file("sample-risky-en.txt")

    def test_band_urgent(self):
        self.assertEqual(self.result.band, "urgent")

    def test_ip_prepay_flagged_high(self):
        hits = [f for f in self.result.findings
                if f.rule.id == "LG-IP-PREPAY"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].severity, "high")
        self.assertIn("Clause 2", hits[0].location)

    def test_core_flags_present(self):
        ids = set(f.rule.id for f in self.result.findings)
        for rid in ("LG-IP-PREPAY", "LG-DEPOSIT-FULL", "LG-NONREFUNDABLE",
                    "LG-UNILATERAL-TERM", "LG-PERSONAL-GUARANTEE",
                    "LG-UNLIMITED-LIABILITY", "LG-UNLIMITED-REVISIONS",
                    "LG-MORAL-RIGHTS"):
            self.assertIn(rid, ids)

    def test_scoring_math(self):
        expected = sum(engine.SCORE[f.severity]
                       for f in self.result.findings)
        self.assertEqual(self.result.score, expected)
        self.assertGreaterEqual(self.result.score, 12)


class RiskyArTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _scan_file("sample-risky-ar.txt")

    def test_arabic_patterns_fire(self):
        ids = set(f.rule.id for f in self.result.findings)
        for rid in ("LG-IP-PREPAY", "LG-DEPOSIT-FULL", "LG-NONREFUNDABLE",
                    "LG-UNILATERAL-TERM", "LG-PERSONAL-GUARANTEE",
                    "LG-UNLIMITED-LIABILITY", "LG-CONF-INDEFINITE",
                    "LG-SETTLE-DISTANT-FORUM"):
            self.assertIn(rid, ids)

    def test_arabic_location_label(self):
        f = [f for f in self.result.findings
             if f.rule.id == "LG-IP-PREPAY"][0]
        self.assertEqual(f.location_ar, "البند 2")

    def test_snippet_keeps_raw_arabic(self):
        f = [f for f in self.result.findings
             if f.rule.id == "LG-IP-PREPAY"][0]
        # The snippet must show the original (voweled) wording, not the
        # folded haystack.
        self.assertIn("ملكية", f.snippet)


class FairContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _scan_file("sample-fair-en.txt")

    def test_no_high_or_medium(self):
        for f in self.result.findings:
            self.assertIn(f.severity, ("low", "info"),
                          "fair sample must not trigger %s" % f.rule.id)

    def test_band_not_urgent(self):
        self.assertIn(self.result.band, ("watch", "none"))


class BandHonestyTests(unittest.TestCase):
    def _result_with(self, sev_count_pairs):
        doc = extract.extract_text("Agreement text long enough to scan. "
                                   "More words here to pass the minimum.")
        res = engine.scan(doc, config.default())
        fake = []
        from lexiguard import rules as _rules
        rule = _rules.RULES[0]
        for sev, n in sev_count_pairs:
            for _ in range(n):
                fake.append(engine.Finding(rule, None, "x", sev))
        res.findings = fake
        return res

    def test_score_bands(self):
        self.assertEqual(self._result_with([]).band, "none")
        self.assertEqual(self._result_with([("low", 1)]).band, "watch")
        self.assertEqual(self._result_with([("medium", 3)]).band, "review")
        self.assertEqual(self._result_with([("high", 3)]).band, "urgent")

    def test_none_band_never_claims_safety(self):
        res = self._result_with([])
        for phrase in ("clean", "approved", "secure", "legally safe"):
            self.assertNotIn(phrase, res.band_en.lower())
        self.assertIn("NOT a claim", res.band_en)
        self.assertIn("لا يعني ذلك خلو العقد", res.band_ar)

    def test_dedupe_same_rule_same_clause(self):
        doc = extract.extract_text(
            "1. Payment\nAll fees are non-refundable under any "
            "circumstances whatsoever indeed.\n\n"
            "2. Term\nA second clause body with enough text here now.\n\n"
            "3. Scope\nA third clause body with enough text here now.\n")
        res = engine.scan(doc, config.default())
        hits = [f for f in res.findings if f.rule.id == "LG-NONREFUNDABLE"]
        self.assertLessEqual(len(hits), 1)

    def test_config_side_filter_applies(self):
        cfg = config.Config(side="client")
        res = engine.scan(extract.extract(
            os.path.join(EXAMPLES, "sample-risky-en.txt")), cfg)
        for f in res.findings:
            self.assertIn(f.rule.side, ("client", "both"))

    def test_config_ignore_applies(self):
        cfg = config.Config(ignore_rules=("LG-SETTLE-DISTANT-FORUM",))
        res = engine.scan(extract.extract(
            os.path.join(EXAMPLES, "sample-fair-en.txt")), cfg)
        ids = [f.rule.id for f in res.findings]
        self.assertNotIn("LG-SETTLE-DISTANT-FORUM", ids)
        self.assertEqual(res.band, "none")


if __name__ == "__main__":
    unittest.main()
