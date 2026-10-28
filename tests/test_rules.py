# -*- coding: utf-8 -*-
"""Rule registry tests: integrity, selection, ReDoS guard."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexiguard import rules


class RegistryTests(unittest.TestCase):
    def test_ids_unique(self):
        ids = [r.id for r in rules.RULES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_rule_is_bilingual_and_complete(self):
        for r in rules.RULES:
            self.assertTrue(r.title_en and r.title_ar, r.id)
            self.assertTrue(r.why_en and r.why_ar, r.id)
            self.assertTrue(r.fix_en and r.fix_ar, r.id)
            self.assertIn(r.side, ("provider", "client", "both"), r.id)
            self.assertTrue(r.patterns, r.id)

    def test_severity_domain(self):
        for r in rules.RULES:
            self.assertIn(r.severity, rules.SEVERITIES)

    def test_all_regexes_compile(self):
        for r in rules.RULES:
            for pat in r._compiled:
                self.assertTrue(pat.pattern, r.id)


class RedosGuardTests(unittest.TestCase):
    """Bounded-regex sanity: hostile inputs must resolve fast."""

    def test_no_catastrophic_backtracking(self):
        hostile = ["a" * 300 + "!", " " * 300, "1" * 300,
                   "كلمة " * 150, "a " * 200 + "!"]
        start = time.time()
        for r in rules.RULES:
            for s in hostile:
                for pat in r._compiled:
                    pat.search(s)
        self.assertLess(time.time() - start, 5.0)


class SelectionTests(unittest.TestCase):
    def test_ignore(self):
        ids = [r.id for r in rules.select_rules(
            ignore={"LG-IP-PREPAY"})]
        self.assertNotIn("LG-IP-PREPAY", ids)

    def test_min_severity_floor(self):
        out = rules.select_rules(min_severity="high")
        self.assertTrue(out)
        for r in out:
            self.assertEqual(r.severity, "high")

    def test_side_filter(self):
        out = rules.select_rules(side="client")
        for r in out:
            self.assertIn(r.side, ("client", "both"))

    def test_get_rule(self):
        self.assertEqual(rules.get_rule("LG-IP-PREPAY").severity, "high")
        self.assertIsNone(rules.get_rule("LG-NOPE"))


class PatternBehaviorTests(unittest.TestCase):
    """Spot-check that each flagship rule fires on its canonical text."""

    CASES = {
        "LG-IP-PREPAY": "Provider assigns all rights in the work product "
                        "to Client prior to payment.",
        "LG-NO-OWNERSHIP": "Client shall not acquire any right or title "
                           "in the work.",
        "LG-LATE-PENALTY": "A late penalty of 2% per day applies.",
        "LG-COMPOUND-INTEREST": "Overdue sums bear compound interest.",
        "LG-PAY-NET90": "Invoices are payable at Net 90 days.",
        "LG-NONREFUNDABLE": "All fees are non-refundable.",
        "LG-FINAL-PAY-SUBJECTIVE": "The final payment is released upon "
                                   "Client's sole satisfaction.",
        "LG-AUTORENEW": "This agreement will automatically renew for "
                        "successive terms.",
        "LG-UNILATERAL-AMEND": "Client may modify this agreement at any "
                               "time without consent.",
        "LG-UNILATERAL-TERM": "Client may terminate for convenience at "
                              "any time.",
        "LG-UNLIMITED-REVISIONS": "Unlimited revisions are included.",
        "LG-NONCOMPETE": "Contractor agrees to a non-compete for two "
                         "years.",
        "LG-EXCLUSIVE": "Services are provided on an exclusive basis.",
        "LG-PERSONAL-GUARANTEE": "The owner personally guarantees all "
                                 "obligations.",
        "LG-UNLIMITED-LIABILITY": "Provider is liable for any and all "
                                  "losses without limit.",
        "LG-ONEWAY-INDEMNITY": "Provider shall indemnify Client against "
                               "all claims.",
        "LG-MORAL-RIGHTS": "All moral rights are waived by Artist.",
        "LG-DEPOSIT-FULL": "100% of the fee is payable in advance.",
        "LG-SETTLE-DISTANT-FORUM": "Governed by the laws of Country X "
                                   "with exclusive jurisdiction in its "
                                   "courts.",
        "LG-CONF-INDEFINITE": "Confidentiality obligations are perpetual "
                              "and survive forever.",
    }

    def test_all_rules_have_canonical_cases(self):
        self.assertEqual(sorted(self.CASES.keys()),
                         sorted(r.id for r in rules.RULES))

    def test_each_rule_fires_on_its_case(self):
        for rid, text in self.CASES.items():
            rule = rules.get_rule(rid)
            hits = [p for p in rule._compiled if p.search(text)]
            if rule.mode == "all":
                self.assertEqual(len(hits), len(rule._compiled),
                                 "%s mode=all missed: %r" % (rid, text))
            else:
                self.assertTrue(hits, "%s did not fire on %r" % (rid, text))


if __name__ == "__main__":
    unittest.main()
