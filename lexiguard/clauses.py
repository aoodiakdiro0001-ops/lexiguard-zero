"""Clause segmentation — split a contract into numbered clauses/articles.

Findings cite a human-usable location: «البند 5» / "Clause 5 · Article 3".
Bilingual header detection (Arabic + English + roman + Arabic-Indic digits).

Fallback: if no headers are found (an unnumbered agreement), the text is
split into paragraph blocks so every finding still has a stable location.

Bright line: pure text segmentation — the document is never executed or
interpreted as anything but text.
"""
import re

# Arabic-Indic digits -> ASCII (so ٥. matches 5.)
_AR_DIGITS = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_AR_DIGITS.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})

# Header patterns. Each yields (label_kind, label_text).
# Keep them ordered: more specific first.
_HEADER_PATTERNS = [
    # Arabic: المادة الأولى / المادة 5 / البند (5) / الفصل الثاني / القسم 3
    (re.compile(r"^[ \t]*(?:المادة|البند|الفصل|القسم|المرجع)\s+"
                r"(?P<n>[٠-٩0-9]+|[أ-ي]{1,12})\b"),
     "ar"),
    # English: Clause 5 / Article 3 / Section 2.1 / Paragraph 4
    (re.compile(r"^[ \t]*(?:Clause|Article|Section|Paragraph|Part|Annex"
                r"|Appendix)\s+(?P<n>[0-9]+(?:\.[0-9]+)?)\b", re.I),
     "en"),
    # Numbered top-level: "5." or "5)" or "٥)" at line start (max 2 digits
    # so prices/dates mid-sentence never start a clause)
    (re.compile(r"^[ \t]*(?P<n>[0-9٠-٩]{1,2})[.)][ \t]+(?P<t>\S)"),
     "num"),
    # ALL-CAPS section titles: "PAYMENT TERMS" as standalone
    (re.compile(r"^[ \t]*(?P<n>[A-Z][A-Z0-9 &/()-]{3,40})[ \t]*$"),
     "title"),
    # Arabic standalone titles: "شروط الدفع" / "الملكية الفكرية" alone on a
    # line (letters only, >=10 chars, not sentence-ending punctuation).
    # kind "title-ar": further screened against sentence particles below.
    (re.compile(r"^[ \t]*(?P<n>[ء-ي][ء-ي \t0-9()\-–—]{9,})[ \t]*"
                r"(?<![.,،؛:])$"),
     "title-ar"),
]

_ROMAN = {"ا": "1", "اب": "2", "اثر": "3", "اربعة": "4", "خمسة": "5",
          "ستة": "6", "سبعة": "7", "ثمانية": "8", "تسعة": "9",
          "عشرة": "10"}
# Arabic ordinals as written in headers (الأولى / الأولى / الثاني / ...) —
# keys are FOLDED forms (normalize_ar already applied: tashkeel gone,
# أ→ا, ة→ه, ى→ي); both masculine and feminine spellings accepted.
_AR_ORD = {"الاول": "1", "الاولي": "1",
           "الثاني": "2", "الثانيه": "2",
           "الثالث": "3", "الثالثه": "3",
           "الرابع": "4", "الرابعه": "4",
           "الخامس": "5", "الخامسه": "5",
           "السادس": "6", "السادسه": "6",
           "السابع": "7", "السابعه": "7",
           "الثامن": "8", "الثامنه": "8",
           "التاسع": "9", "التاسعه": "9",
           "العاشر": "10", "العاشره": "10"}
_EN_ROMAN = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5",
             "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10"}


def _canon_number(raw, kind):
    """Normalize a captured header number to a short display string."""
    if kind in ("title", "title-ar"):
        return None                    # title headers carry no number
    s = str(raw).translate(_AR_DIGITS).strip()
    if kind == "en" and s.upper() in _EN_ROMAN:
        return _EN_ROMAN[s.upper()]
    if kind == "ar":
        folded = normalize_ar(s)
        if folded in _AR_ORD:
            return _AR_ORD[folded]
        if s in _ROMAN:
            return _ROMAN[s]
    return s[:8]


class Clause(object):
    __slots__ = ("number", "heading", "text", "start_line")

    def __init__(self, number, heading, text, start_line):
        self.number = number          # display string, e.g. "5" or "A"
        self.heading = heading        # raw heading line
        self.text = text              # body (heading stripped)
        self.start_line = start_line  # 1-based line of the heading

    @property
    def label(self):
        if self.number:
            return "Clause %s" % self.number
        if self.heading:
            return "§ %s" % self.heading[:40]
        return "¶%d" % self.start_line

    @property
    def label_ar(self):
        if self.number:
            return "البند %s" % self.number
        if self.heading:
            return "§ %s" % self.heading[:40]
        return "فقرة (سطر %d)" % self.start_line

    def as_dict(self):
        return {"number": self.number, "heading": self.heading,
                "text": self.text, "start_line": self.start_line,
                "label": self.label}


# Sentence particles: an Arabic line containing these is a wrapped body
# sentence, not a title (prevents "ينقل المقدم ملكية ... قبل الدفعة" from
# being split off as a heading).
_AR_PARTICLE = re.compile(
    r"(?:^|\s)(?:من|في|عن|مع|قبل|بعد|على|الذي|التي|بين|الى|حتى|كانت?"
    r"|هذا|هذه|ذلك|تلك|الاول|الثاني)(?:\s|$)")


def _match_header(line):
    for pat, kind in _HEADER_PATTERNS:
        m = pat.match(line)
        if m:
            if kind == "title-ar" and _AR_PARTICLE.search(line):
                return None, None, 0   # body line, not a title
            raw = m.groupdict().get("n")
            if raw is None:
                raw = m.group(1) if m.groups() else ""
            return kind, _canon_number(raw, kind), m.end()
    return None, None, 0


def split_clauses(text):
    """Segment `text` into Clause objects. Never raises on odd input."""
    lines = text.splitlines()
    headers = []                       # (line_idx, kind, number, heading)
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        kind, num, end = _match_header(line)
        if kind:
            headers.append((i, kind, num, line.strip()[:120]))

    if len(headers) >= 3:
        clauses = []
        for idx, (li, kind, num, heading) in enumerate(headers):
            stop = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
            body = "\n".join(lines[li + 1:stop]).strip()
            clauses.append(Clause(num, heading, body, li + 1))
        return clauses

    # Fallback: paragraph blocks (blank-line separated), unnumbered.
    blocks, cur, start = [], [], 1
    for i, line in enumerate(lines, 1):
        if line.strip():
            if not cur:
                start = i
            cur.append(line)
        elif cur:
            blocks.append((start, "\n".join(cur).strip()))
            cur = []
    if cur:
        blocks.append((start, "\n".join(cur).strip()))
    return [Clause(None, "", body, ln)
            for ln, body in blocks if body and len(body) >= 20]


_FOLD_MAP = {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي",
             "ة": "ه"}
_TASHKEEL = set("ً-ْٰـ")          # removed during folding


def normalize_ar(s):
    """Fold Arabic orthography for matching: strip tashkeel, unify
    alef/ya/ta-marbuta forms. (Matching only — display keeps originals.)"""
    s = re.sub(r"[ً-ْٰـ]", "", str(s))
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    s = s.replace("ة", "ه")
    return s


def normalize_ar_map(s):
    """Like normalize_ar but also returns the index map from folded
    positions back to RAW positions, so a folded match can be shown to
    the user with the original wording."""
    out, idx = [], []
    for i, ch in enumerate(str(s)):
        if ch in _TASHKEEL:
            continue
        out.append(_FOLD_MAP.get(ch, ch))
        idx.append(i)
    return "".join(out), idx


def find_span(pattern, text):
    """Return (raw_start, raw_end, raw_text) of the first match: raw
    text first; else folded text with the span mapped back to raw so
    snippets keep the original (voweled) wording. None if no match."""
    m = pattern.search(text)
    if m:
        return m.start(), m.end(), text
    folded, idx = normalize_ar_map(text)
    m = pattern.search(folded)
    if not m:
        return None
    n = len(text)
    start = idx[m.start()] if m.start() < len(idx) else n
    if m.end() > 0 and (m.end() - 1) < len(idx):
        end = idx[m.end() - 1] + 1
    else:
        end = n
    return start, end, text
