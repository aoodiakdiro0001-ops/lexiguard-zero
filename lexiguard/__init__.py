"""Lexi-Guard Zero — an autonomous contract & document red-flag reviewer.

Reads contracts / NDAs / ToS / invoices YOU own or are authorized to review,
extracts their text locally, flags risky or one-sided clause patterns
(bilingual: Arabic + English), scores them into honest risk bands, and
proposes fair counter-clause language — with an optional free-AI (Gemini
free tier) rephrasing and a deterministic offline fallback.

Bright lines (enforced in code, pinned by tests — see SECURITY.md):
  * NOT LEGAL ADVICE. Every report says so. This tool is a first-pass
    signal generator for a HUMAN; a licensed attorney reviews real deals.
  * Local-first privacy: documents never leave the machine unless YOU
    explicitly configure the optional AI layer or Telegram delivery —
    contracts are confidential and there is no telemetry.
  * No "100% accurate" / "replaces your lawyer" claim anywhere. Findings
    are heuristic clause-pattern signals and may miss or over-flag.
  * The AI layer only rephrases counter-clause suggestions; it is never
    asked to guarantee an outcome, and the offline engine works without it.

MIT (c) 2026 Baran Avisat — Aodı Akdıro Suite
Support: baranavisat@gmail.com · WhatsApp +90 531 326 37 22
"""
__version__ = "1.0.0"

DISCLAIMER_EN = (
    "Not legal advice. Lexi-Guard Zero is a heuristic first-pass review of "
    "clause patterns, not a licensed attorney's opinion; findings may miss "
    "or over-flag terms. Have a qualified lawyer review any real agreement."
)
DISCLAIMER_AR = (
    "ليست استشارة قانونية. يراجع Lexi-Guard Zero أنماط البنود بطريقة "
    "استدلالية ولا يُغني عن رأي محامٍ مرخَّص؛ قد تفوّت نتائجه بنوداً أو "
    "يضخّم بنوداً. راجع محامياً مؤهلاً قبل أي اتفاق حقيقي."
)
