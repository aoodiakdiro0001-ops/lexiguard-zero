# -*- coding: utf-8 -*-
"""Extraction tests: honest limits, caps, no execution of content."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexiguard import extract


def _tmp(content, suffix=".txt"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(content if isinstance(content, bytes)
                 else content.encode("utf-8"))
    return path


class ExtractTextTests(unittest.TestCase):
    def test_plain_text_ok(self):
        p = _tmp("Service Agreement. " * 5)
        try:
            doc = extract.extract(p)
            self.assertGreater(doc.chars, 50)
            self.assertEqual(doc.pages, None)
        finally:
            os.unlink(p)

    def test_empty_file_raises(self):
        p = _tmp("")
        try:
            with self.assertRaises(extract.ExtractError):
                extract.extract(p)
        finally:
            os.unlink(p)

    def test_too_short_raises(self):
        p = _tmp("tiny")
        try:
            with self.assertRaises(extract.ExtractError):
                extract.extract(p)
        finally:
            os.unlink(p)

    def test_size_cap_truncates_and_warns(self):
        big = ("word " * 1200 + "\n") * 60        # ~360KB? no: ensure >5MiB
        big = ("x" * 1000 + "\n") * (6 * 1024)    # ~6 MiB
        p = _tmp(big)
        try:
            doc = extract.extract(p)
            self.assertLessEqual(doc.chars, extract.MAX_BYTES + 16)
            self.assertTrue(any("truncat" in w for w in doc.warnings))
        finally:
            os.unlink(p)

    def test_arabic_cp1256_decodes(self):
        raw = "عقد تقديم خدمات تصميم".encode("cp1256")
        p = _tmp(raw)
        try:
            doc = extract.extract(p)
            self.assertIn("خدمات", doc.text)
        finally:
            os.unlink(p)

    def test_non_regular_file_rejected(self):
        # /dev/zero is a character device with st_size 0 — must be
        # rejected, never read unbounded (security review #10).
        with self.assertRaises(extract.ExtractError):
            extract.extract("/dev/zero")


class ExtractHtmlTests(unittest.TestCase):
    def test_script_stripped_not_executed(self):
        p = _tmp("<html><head><script>alert('x')</script></head>"
                 "<body><p>Confidentiality clause text here.</p>"
                 "<script>steal()</script></body></html>",
                 suffix=".html")
        try:
            doc = extract.extract(p)
            self.assertIn("Confidentiality", doc.text)
            self.assertNotIn("alert", doc.text)
            self.assertNotIn("steal", doc.text)
        finally:
            os.unlink(p)

    def test_entities_and_blocks(self):
        self.assertIn("A", extract.strip_html("&lt;A&gt;"))
        self.assertIn("\n", extract.strip_html("<p>a</p><p>b</p>"))

    def test_malformed_html_fallback_no_duplication(self):
        # Security review #3: the fallback must REPLACE partial output,
        # never append a second copy of the document.
        out = extract.strip_html("Visible text<!--" + "-" * 8)
        self.assertEqual(out.count("Visible text"), 1)


class ExtractRtfTests(unittest.TestCase):
    def test_rtf_control_words_stripped(self):
        rtf = r"{\rtf1\ansi Payment terms: Net 30 days.\par}"
        out = extract.strip_rtf(rtf)
        self.assertIn("Payment terms", out)
        self.assertNotIn("\\par", out)
        self.assertNotIn("{\\rtf1", out)


class ExtractPdfHonestyTests(unittest.TestCase):
    def test_pdf_without_backend_is_honest(self):
        orig = extract._pdf_backend
        extract._pdf_backend = lambda: (None, None)
        p = _tmp(b"%PDF-1.4 fake bytes for test", suffix=".pdf")
        try:
            with self.assertRaises(extract.ExtractError) as ctx:
                extract.extract(p)
            msg = str(ctx.exception)
            self.assertIn("PyMuPDF", msg)
            self.assertIn("OCR", msg)
        finally:
            os.unlink(p)
            extract._pdf_backend = orig

    def test_scanned_pdf_reported_not_faked(self):
        # Simulate a backend returning (almost) nothing: the engine must
        # report honestly instead of fabricating text.
        class _FakePage(object):
            def get_text(self):
                return ""

        class _FakeDoc(object):
            page_count = 3

            def __iter__(self):
                return iter([_FakePage()] * 3)

            def close(self):
                pass

        class _FakeMod(object):
            @staticmethod
            def open(path):
                return _FakeDoc()

        orig = extract._pdf_backend
        extract._pdf_backend = lambda: ("pymupdf", _FakeMod)
        p = _tmp(b"%PDF-1.4 fake", suffix=".pdf")
        try:
            with self.assertRaises(extract.ExtractError) as ctx:
                extract.extract(p)
            self.assertIn("SCANNED", str(ctx.exception))
            self.assertIn("OCR", str(ctx.exception))
        finally:
            os.unlink(p)
            extract._pdf_backend = orig


class ExtractMemoryTests(unittest.TestCase):
    def test_extract_text_wrapper(self):
        doc = extract.extract_text("Agreement text " * 10)
        self.assertEqual(doc.method, "memory")
        with self.assertRaises(extract.ExtractError):
            extract.extract_text("short")


if __name__ == "__main__":
    unittest.main()
