# -*- coding: utf-8 -*-
"""Clause segmentation + Arabic folding tests."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexiguard import clauses


class SplitEnTests(unittest.TestCase):
    def test_numbered_headers(self):
        text = ("1. Scope\nProvider shall deliver.\n\n"
                "2. Payment\nNet 30 days.\n\n"
                "3. Term\nOne year.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual([c.number for c in cs], ["1", "2", "3"])
        self.assertIn("deliver", cs[0].text)
        self.assertIn("Net 30", cs[1].text)

    def test_clause_keywords(self):
        text = ("Clause 1. Services\nBody one here now.\n\n"
                "Article 2. Fees\nBody two here now.\n\n"
                "Section 3. Term\nBody three here now.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual([c.number for c in cs], ["1", "2", "3"])

    def test_all_caps_title(self):
        text = ("PAYMENT TERMS\nNet 15 days apply here.\n\n"
                "TERMINATION\nEither party may exit now.\n\n"
                "LIABILITY\nCapped at fees paid.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual(len(cs), 3)
        self.assertIsNone(cs[0].number)
        self.assertIn("PAYMENT", cs[0].heading)

    def test_fallback_paragraphs(self):
        text = ("First paragraph with enough characters to be a block.\n\n"
                "Second paragraph with enough characters as well.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual(len(cs), 2)
        self.assertIsNone(cs[0].number)
        self.assertTrue(cs[0].label.startswith("¶"))


class SplitArTests(unittest.TestCase):
    def test_arabic_numbered(self):
        text = ("1. المدفوعات\nيُدفع المبلغ خلال 15 يوماً من التوقيع.\n\n"
                "2. المسؤولية\nتُحدّ المسؤولية بأجور العقد فقط.\n\n"
                "3. السرية\nيلتزم الطرفان بالسرية 3 سنوات.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual([c.number for c in cs], ["1", "2", "3"])
        self.assertEqual(cs[0].label_ar, "البند 1")

    def test_arabic_indic_digits(self):
        text = ("٥. المدفوعات\nنص يشرح شروط الدفع هنا.\n\n"
                "٦. الإنهاء\nنص يشرح الإنهاء هنا.\n\n"
                "٧. السرية\nنص يشرح السرية هنا.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual([c.number for c in cs], ["5", "6", "7"])

    def test_arabic_ordinal(self):
        text = ("المادة الأولى Scope\nنص أول.\n\n"
                "المادة الثانية Fees\nنص ثانٍ.\n\n"
                "المادة الثالثة Term\nنص ثالث.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual([c.number for c in cs], ["1", "2", "3"])

    def test_arabic_body_line_not_title(self):
        # A wrapped sentence with particles must NOT be split as a title.
        text = ("2. الملكية الفكرية\n"
                "ينقل مقدم الخدمة ملكية الفكرية للعميل قبل سداد الدفعة.\n\n"
                "3. المدفوعات\nنص المدفوعات يشرح كل التفاصيل.\n\n"
                "4. السرية\nنص السرية يشرح كل التفاصيل.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual([c.number for c in cs], ["2", "3", "4"])
        self.assertIn("ينقل", cs[0].text)

    def test_arabic_standalone_title(self):
        text = ("شروط الدفع\nيُدفع المبلغ خلال 15 يوماً كاملاً.\n\n"
                "الملكية الفكرية\nتنتقل الملكية بعد الدفع الكامل.\n\n"
                "السرية والتزام الطرفين\nيلتزم الطرفان بالسرية التامة.\n")
        cs = clauses.split_clauses(text)
        self.assertEqual(len(cs), 3)
        self.assertIsNone(cs[0].number)
        self.assertIn("شروط الدفع", cs[0].heading)


class FoldingTests(unittest.TestCase):
    def test_tashkeel_stripped(self):
        self.assertEqual(clauses.normalize_ar("مُبَلَّغ"), "مبلغ")

    def test_alef_unified(self):
        self.assertEqual(clauses.normalize_ar("أإآ"), "ااا")

    def test_ta_marbuta_and_alif_maqsurah(self):
        self.assertEqual(clauses.normalize_ar("ملةى"), "ملهي")

    def test_hamza_waw_unified(self):
        self.assertEqual(clauses.normalize_ar("مسؤولية"), "مسووليه")

    def test_find_span_raw_first(self):
        import re
        span = clauses.find_span(re.compile("net 30", re.I), "Net 30 days")
        self.assertIsNotNone(span)
        self.assertEqual(span[2][span[0]:span[1]].lower(), "net 30")

    def test_find_span_folded_maps_to_raw(self):
        import re
        # Raw has tashkeel so the plain pattern misses raw but hits
        # folded; the returned span must point into the ORIGINAL text.
        span = clauses.find_span(re.compile("غرامه"), "غرامة تأخير")
        self.assertIsNotNone(span)
        s, e, hay = span
        self.assertEqual(hay, "غرامة تأخير")
        self.assertEqual(hay[s:e], "غرامة")


class LabelTests(unittest.TestCase):
    def test_labels_bilingual(self):
        c = clauses.Clause("5", "5. Payment", "body", 10)
        self.assertEqual(c.label, "Clause 5")
        self.assertEqual(c.label_ar, "البند 5")

    def test_heading_fallback(self):
        c = clauses.Clause(None, "PAYMENT TERMS", "body", 4)
        self.assertIn("PAYMENT", c.label)

    def test_paragraph_fallback(self):
        c = clauses.Clause(None, "", "body", 7)
        self.assertEqual(c.label, "¶7")


if __name__ == "__main__":
    unittest.main()
