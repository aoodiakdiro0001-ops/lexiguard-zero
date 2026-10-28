"""Document text extraction — local, stdlib-first, honest about limits.

Contracts are CONFIDENTIAL: extraction runs entirely on this machine.
Nothing is uploaded here; the optional AI layer (remedy.py) is a separate,
explicit step.

Backends:
  * .txt / .md / .csv / .json / .rtf / .html  — stdlib only, always works
  * .pdf                                      — OPTIONAL: PyMuPDF (fitz) if
    installed, else pdfplumber, else an honest error telling you how to
    convert. There is NO bundled OCR: an image-only (scanned) PDF is
    detected and reported as such instead of pretending to read it.

Contracts (pinned by tests):
  * extraction never executes anything from the document
  * size-capped reads (no unbounded memory on a hostile file)
  * HTML/script content is stripped — a <script> in a contract page is text,
    not code
"""
import io
import os
import re

MAX_BYTES = 5 * 1024 * 1024          # 5 MiB per document
TEXT_EXTS = {".txt", ".md", ".markdown", ".csv", ".json", ".rtf", ".text",
             ".html", ".htm"}
PDF_EXTS = {".pdf"}


class ExtractError(Exception):
    pass


class Document(object):
    __slots__ = ("text", "source", "method", "warnings", "pages")

    def __init__(self, text, source, method, warnings=None, pages=None):
        self.text = text
        self.source = source
        self.method = method            # e.g. "utf-8", "pymupdf", "html"
        self.warnings = list(warnings or [])
        self.pages = pages              # int or None

    @property
    def chars(self):
        return len(self.text)

    @property
    def words(self):
        return len(self.text.split())

    def as_dict(self):
        return {"source": self.source, "method": self.method,
                "chars": self.chars, "words": self.words,
                "pages": self.pages, "warnings": self.warnings}


def _read_capped(path):
    """Read at most MAX_BYTES; return (bytes, truncated)."""
    try:
        size = os.path.getsize(path)
    except OSError as e:
        raise ExtractError("cannot read %s: %s" % (path, e))
    if size > MAX_BYTES:
        with open(path, "rb") as fh:
            return fh.read(MAX_BYTES), True
    with open(path, "rb") as fh:
        return fh.read(), False


def _decode(raw):
    for enc in ("utf-8", "utf-8-sig", "utf-16", "cp1256", "latin-1"):
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace"), "utf-8/replace"


# --------------------------------------------------------------------- HTML
class _HTMLText(object):
    """Strip scripts/styles/tags with the stdlib parser (no execution)."""
    _SKIP = {"script", "style", "noscript", "template", "svg", "head"}
    _BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5",
              "h6", "section", "article", "table", "ul", "ol", "hr"}

    def __init__(self):
        from html.parser import HTMLParser
        self._parts = []
        self._skip_depth = 0
        outer = self

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag in outer._SKIP:
                    outer._skip_depth += 1
                elif tag in outer._BLOCK:
                    outer._parts.append("\n")

            def handle_endtag(self, tag):
                if tag in outer._SKIP and outer._skip_depth:
                    outer._skip_depth -= 1
                elif tag in outer._BLOCK:
                    outer._parts.append("\n")

            def handle_data(self, data):
                if not outer._skip_depth:
                    outer._parts.append(data)

        self._p = P(convert_charrefs=True)

    def feed(self, text):
        try:
            self._p.feed(text)
            self._p.close()
        except Exception:
            self._parts.append(re.sub(r"<[^>]+>", " ", text))
        return self


def strip_html(text):
    h = _HTMLText()
    h.feed(text)
    out = "".join(h._parts)
    return re.sub(r"[ \t]+", " ", out)


def strip_rtf(text):
    """Very small RTF-to-text (control words + groups). Good enough for
    clause review; not a full RTF engine."""
    text = re.sub(r"\\'([0-9a-fA-F]{2})", " ", text)     # hex escapes -> drop
    text = re.sub(r"\\par[d]?\b", "\n", text)
    text = re.sub(r"\\tab\b", " ", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)      # control words
    text = re.sub(r"[{}]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text)


# --------------------------------------------------------------------- PDF
def _pdf_backend():
    try:
        import fitz                      # PyMuPDF
        return "pymupdf", fitz
    except Exception:
        pass
    try:
        import pdfplumber
        return "pdfplumber", pdfplumber
    except Exception:
        pass
    return None, None


def _extract_pdf(path, raw):
    backend, mod = _pdf_backend()
    if backend is None:
        raise ExtractError(
            "PDF support needs an optional free library: `pip install "
            "PyMuPDF` (or pdfplumber), or convert the file to .txt/.md "
            "first (e.g. `pdftotext file.pdf out.txt`). Scanned/image-"
            "only PDFs additionally need OCR (ocrmypdf/Tesseract) — "
            "Lexi-Guard Zero never fakes a reading. The engine itself "
            "stays dependency-free.")
    warnings = []
    pages = None
    if backend == "pymupdf":
        try:
            import tempfile
            fd, tmp = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            with open(tmp, "wb") as fh:
                fh.write(raw)
            try:
                doc = mod.open(tmp)
                pages = doc.page_count
                parts = []
                for i, page in enumerate(doc):
                    if i >= 200:                     # hostile-PDF guard
                        warnings.append("PDF capped at 200 pages")
                        break
                    parts.append(page.get_text())
                doc.close()
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        except Exception as e:
            raise ExtractError("PyMuPDF failed: %s" % e)
        text = "\n".join(parts)
    else:                                            # pdfplumber
        try:
            with mod.open(path) as pdf:
                pages = len(pdf.pages)
                if pages > 200:
                    warnings.append("PDF capped at 200 pages")
                text = "\n".join((p.extract_text() or "")
                                 for p in pdf.pages[:200])
        except Exception as e:
            raise ExtractError("pdfplumber failed: %s" % e)
    if len(text.strip()) < 40:
        raise ExtractError(
            "no extractable text in this PDF — it looks like a SCANNED/"
            "image-only document. Lexi-Guard Zero does not bundle OCR "
            "(no fake readings): run it through an OCR tool first "
            "(e.g. `ocrmypdf` or Tesseract) and upload the text layer.")
    return text, pages, warnings


# ------------------------------------------------------------------ public
def extract(path):
    """Extract reviewable text from a local document. Returns Document.

    Raises ExtractError with an honest message when it genuinely cannot
    read the file (never fabricates content).
    """
    ext = os.path.splitext(path)[1].lower()
    raw, truncated = _read_capped(path)
    warnings = ["file truncated at 5 MiB"] if truncated else []
    if not raw:
        raise ExtractError("empty file: %s" % path)

    if ext in PDF_EXTS:
        text, pages, w2 = _extract_pdf(path, raw)
        warnings.extend(w2)
        return Document(text, path, "pdf", warnings, pages)

    text, enc = _decode(raw)
    if ext in (".html", ".htm"):
        text = strip_html(text)
        method = "html"
    elif ext == ".rtf":
        text = strip_rtf(text)
        method = "rtf"
    else:
        method = enc
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text.strip()) < 20:
        raise ExtractError("no usable text found in %s" % path)
    return Document(text, path, method, warnings)


def extract_text(text, source="<memory>"):
    """Wrap already-extracted text (pasted contract) as a Document."""
    if text is None or len(str(text).strip()) < 20:
        raise ExtractError("text too short to review")
    return Document(str(text), source, "memory")
