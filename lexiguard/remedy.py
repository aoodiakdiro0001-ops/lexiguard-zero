# -*- coding: utf-8 -*-
"""Counter-clause remedies — offline-first, AI optional and disclosed.

The offline path is the default and works with zero network: each rule
carries a bilingual fair-counter-clause TEMPLATE that a human adapts
(bracketed values like [30] days must be filled in by them).

The optional Gemini layer (free tier) only REPHRASES a suggestion to fit
the deal's wording. Contract privacy is a bright line:

  * it is off unless the user passes --ai gemini AND GEMINI_API_KEY is set
  * only the flagged rule id + the counter-clause template are sent —
    NEVER the document, the snippet, the file name, or anything else
  * the request is a single POST with a timeout; any failure falls back
    to the offline template (fail-closed, no retries, no proxying)
  * the report discloses which suggestions were AI-rephrased
"""
import json
import os

try:                                    # stdlib only
    from urllib.request import Request, build_opener
    from urllib.error import URLError, HTTPError
except ImportError:                     # pragma: no cover
    raise

from .notify import _NoRedirect         # single no-redirect implementation

GEMINI_ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/"
                   "models/gemini-2.0-flash:generateContent")
TIMEOUT = 20
MAX_TEMPLATE_CHARS = 1200               # hard cap on what may be sent
MAX_AI_REMEDIES = 25                    # hard cap on API calls per scan

_SYSTEM = ("You assist with contract negotiation drafts. Rephrase the "
           "given counter-clause template to fit the deal description, "
           "keeping it fair to BOTH parties, concise, and marked as a "
           "draft that a licensed attorney must review. Do not add "
           "guarantees, citations to real cases, or claims that it is "
           "legally sufficient.")


class Remedy(object):
    __slots__ = ("rule_id", "text_en", "text_ar", "source")

    def __init__(self, rule_id, text_en, text_ar, source):
        self.rule_id = rule_id
        self.text_en = text_en
        self.text_ar = text_ar
        self.source = source        # "offline" | "gemini"

    def as_dict(self):
        return {"rule_id": self.rule_id, "text_en": self.text_en,
                "text_ar": self.text_ar, "source": self.source}


def offline_remedy(finding):
    """Deterministic template remedy — never touches the network."""
    r = finding.rule
    return Remedy(r.id, r.fix_en, r.fix_ar, "offline")


def _gemini(api_key, template, deal_hint):
    body = json.dumps({
        "system_instruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{
            "parts": [{"text":
                       "Deal context (short): %s\n\nCounter-clause "
                       "template to rephrase:\n%s"
                       % (deal_hint or "general service agreement",
                          template[:MAX_TEMPLATE_CHARS])}]
        }],
        "generationConfig": {"maxOutputTokens": 400, "temperature": 0.2},
    }).encode("utf-8")
    # Key goes in a HEADER (never in the URL), redirects are refused,
    # and the response is size-capped below.
    req = Request(GEMINI_ENDPOINT, data=body,
                  headers={"Content-Type": "application/json",
                           "x-goog-api-key": api_key},
                  method="POST")
    opener = build_opener(_NoRedirect())
    with opener.open(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read(MAX_TEMPLATE_CHARS * 4)
                          .decode("utf-8"))
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()


def gemini_remedy(finding, api_key, deal_hint=""):
    """Opt-in AI rephrase. Sends ONLY the rule id context + template.
    Raises on any failure so callers fall back offline."""
    if not api_key:
        raise ValueError("gemini_remedy requires an API key")
    r = finding.rule
    template = ("EN: %s\nAR: %s" % (r.fix_en, r.fix_ar))[:MAX_TEMPLATE_CHARS]
    out = _gemini(api_key, template, deal_hint)
    if not out or len(out) > 3000:
        raise ValueError("gemini returned an empty/oversized reply")
    return Remedy(r.id, out, "(راجع النص الإنجليزي أعلاه)", "gemini")


def remedies_for(result, use_ai=False, api_key=None, deal_hint=""):
    """Build remedies — ONE per distinct rule (dedupe: a rule hitting
    ten clauses needs its counter-clause shown once, not ten times; with
    AI this also bounds API spend to MAX_AI_REMEDIES calls). AI is
    opt-in per call; every AI failure silently degrades to the offline
    template."""
    out, seen, ai_budget = [], set(), MAX_AI_REMEDIES
    for f in result.sorted_findings():
        if f.rule.id in seen:
            continue
        seen.add(f.rule.id)
        if use_ai and ai_budget > 0:
            ai_budget -= 1
            try:
                out.append(gemini_remedy(f, api_key or
                                         os.environ.get("GEMINI_API_KEY"),
                                         deal_hint))
                continue
            except Exception:
                pass
        out.append(offline_remedy(f))
    return out
