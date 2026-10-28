# -*- coding: utf-8 -*-
"""Scan engine: clause x rule matching + transparent risk scoring.

Scoring is deliberately simple and auditable (printed in every report):
    high=5 points, medium=2, low=1, info=0
    0        -> band "none"    (NOT a claim the contract is safe)
    1..4     -> band "watch"
    5..11    -> band "review"
    12+      -> band "urgent"

Bright line: the band is a PRIORITIZATION signal for human review — a
"none" band never renders as "safe/approved/legally clean". Snippets are
kept short and stay on this machine; reports carry the disclaimer.
"""
from . import clauses as _clauses
from . import rules as _rules

SCORE = {"high": 5, "medium": 2, "low": 1, "info": 0}

BANDS = [
    (12, "urgent", "عاجل — راجع بنوداً عالية الخطورة قبل التوقيع",
     "high-signal clauses need review before signing"),
    (5, "review", "يحتاج مراجعة — بنود تستحق التفاوض",
     "clauses worth negotiating"),
    (1, "watch", "مراقبة — إشارات منخفضة الأثر",
     "lower-impact signals"),
    (0, "none", "لم تُكتشف أنماط معروفة (لا يعني ذلك خلو العقد)",
     "no known patterns detected (NOT a claim the contract is safe)"),
]

_SNIPPET = 170


class Finding(object):
    __slots__ = ("rule", "clause", "snippet", "severity")

    def __init__(self, rule, clause, snippet, severity):
        self.rule = rule
        self.clause = clause          # clauses.Clause or None
        self.snippet = snippet
        self.severity = severity

    @property
    def location(self):
        return self.clause.label if self.clause else "?"

    @property
    def location_ar(self):
        return self.clause.label_ar if self.clause else "؟"

    def as_dict(self):
        return {"rule": self.rule.id, "severity": self.severity,
                "category": self.rule.category, "side": self.rule.side,
                "title_en": self.rule.title_en, "title_ar": self.rule.title_ar,
                "location": self.location, "location_ar": self.location_ar,
                "snippet": self.snippet}


def _snippet(text, start, end):
    s_from = max(0, start - 60)
    s_to = min(len(text), end + _SNIPPET)
    s = text[s_from:s_to].replace("\n", " ").strip()
    if len(s) > _SNIPPET + 80:
        s = s[:_SNIPPET + 80]
    return ("…" if s_from > 0 else "") + s + ("…" if s_to < len(text) else "")


def _clause_text(clause):
    """The haystack for matching: heading + body, so terms sitting on the
    header line (common when a wrapped line is detected as a title) are
    still reviewed."""
    if clause.heading:
        return clause.heading + "\n" + clause.text
    return clause.text


def _clause_hits(clause, rule):
    """Return (pattern_index, raw_start, raw_end) of the first hit or
    None. mode any: first pattern that matches wins.
    mode all: every pattern must match somewhere in the clause."""
    hay_full = _clause_text(clause)
    matched_on = None
    first = None
    for idx, pat in enumerate(rule._compiled):
        span = _clauses.find_span(pat, hay_full)
        if span:
            if first is None:
                first = (idx, span[0], span[1], span[2])
            matched_on = matched_on or []
            matched_on.append(idx)
            if rule.mode == "any":
                return first
    if rule.mode == "all" and matched_on is not None \
            and len(matched_on) == len(rule._compiled):
        return first
    return None


def scan(document, cfg=None):
    """Scan a Document against the selected rules. Returns ScanResult."""
    ignore = set(getattr(cfg, "ignore_rules", ()) or ())
    min_sev = getattr(cfg, "min_severity", "info") or "info"
    side = getattr(cfg, "side", None)
    selected = _rules.select_rules(ignore=ignore, min_severity=min_sev,
                                   side=side)

    clause_objs = _clauses.split_clauses(document.text)
    findings = []
    seen = set()                       # (rule_id, clause_line) dedupe
    for clause in clause_objs:
        for rule in selected:
            hit = _clause_hits(clause, rule)
            if hit is None:
                continue
            key = (rule.id, clause.start_line)
            if key in seen:
                continue
            seen.add(key)
            _, s, e, hay = hit
            findings.append(Finding(rule, clause, _snippet(hay, s, e),
                                    rule.severity))
    return ScanResult(document, findings, clause_objs, min_sev)


class ScanResult(object):
    __slots__ = ("document", "findings", "clauses", "min_severity")

    def __init__(self, document, findings, clauses, min_severity):
        self.document = document
        self.findings = findings
        self.clauses = clauses
        self.min_severity = min_severity

    @property
    def score(self):
        return sum(SCORE.get(f.severity, 0) for f in self.findings)

    @property
    def band(self):
        for threshold, name, _ar, _en in BANDS:
            if self.score >= threshold:
                return name
        return "none"

    @property
    def band_ar(self):
        b = self.band
        for _t, name, ar, _en in BANDS:
            if name == b:
                return ar
        return ""

    @property
    def band_en(self):
        b = self.band
        for _t, name, _ar, en in BANDS:
            if name == b:
                return en
        return ""

    def counts(self):
        out = {"high": 0, "medium": 0, "low": 0, "info": 0}
        for f in self.findings:
            out[f.severity] = out.get(f.severity, 0) + 1
        return out

    def sorted_findings(self):
        rank = _rules.SEVERITY_RANK
        return sorted(self.findings,
                      key=lambda f: (-rank[f.severity], f.rule.id,
                                     f.clause.start_line if f.clause else 0))

    def as_dict(self):
        return {
            "document": self.document.as_dict(),
            "score": self.score,
            "band": self.band,
            "band_note_en": self.band_en,
            "counts": self.counts(),
            "findings": [f.as_dict() for f in self.sorted_findings()],
            "scoring": "high=5 medium=2 low=1 info=0; "
                       "bands: 12+ urgent, 5-11 review, 1-4 watch, "
                       "0 none (never 'safe')",
        }
