# How Lexi-Guard Zero Works

> ⚠️ **NOT LEGAL ADVICE** — this document describes a heuristic signal
> generator, not a legal analysis engine. A licensed attorney reviews real
> agreements.

The engine is a pure-function pipeline. Same input → same output, no network,
no state beyond the optional `.lexiguard.json`.

```
FILE ──► extract ──► clauses ──► rules ──► score ──► report
          │            │           │         │         │
          │            │           │         │         └─ md / html / json
          │            │           │         │            + counter-clause
          │            │           │         │            templates
          │            │           │         └─ high=5 med=2 low=1 info=0
          │            │           │            → urgent/review/watch/none
          │            │           └─ ~20 bilingual pattern rules
          │            └─ numbered headers or paragraph fallback
          └─ local text only (PDF via optional backend; no OCR)
```

## 1. Extract — local text only

`lexiguard/extract.py`

- `.txt`/`.md`/`.csv`/`.json`/`.rtf`/`.html` are handled by the Python
  standard library; `.pdf` needs the optional PyMuPDF (or pdfplumber) backend.
- Reads are **capped at 5 MiB** and PDFs at **200 pages**; a truncated read is
  surfaced as a warning, never hidden.
- Encoding is auto-detected (utf-8, utf-8-sig, utf-16, cp1256 for Arabic
  Windows, latin-1, then utf-8-with-replacement), so Arabic documents from any
  source decode correctly.
- **HTML is text, not code.** A stdlib parser strips `<script>`/`<style>`
  and all tags; nothing in the document is ever executed.
- **No fake OCR.** If a PDF yields under ~40 characters of text it is treated
  as scanned/image-only and extraction fails with an honest message:
  *"run it through an OCR tool first (e.g. `ocrmypdf` or Tesseract)"*. The
  tool never invents or guesses content.

Output: a `Document` (text, source, method, page count, warnings).

## 2. Clauses — a human-usable location for every finding

`lexiguard/clauses.py`

Findings must cite a location a human can find in the paper contract. The
segmenter recognizes, in order:

- Arabic headers: `المادة 5`, `المادة الأولى`, `البند (5)`, `الفصل`, `القسم`
- English headers: `Clause 5`, `Article 3`, `Section 2.1`, `Paragraph`, `Annex`
- Numbered lines: `5.` / `5)` at line start (max 2 digits, so mid-sentence
  prices and dates never start a clause)
- ALL-CAPS titles (`PAYMENT TERMS`) and standalone Arabic titles
  (`شروط الدفع`), with a particle screen so wrapped body sentences
  (`… من …`, `… قبل …`, `… الذي …`) are not mistaken for headings

Arabic-Indic digits (٥) and Arabic/Roman ordinals
(الأولى → 1, II → 2) are normalized to the same numbers, so
`المادة ٥` and `Clause 5` cite identically.

If fewer than 3 headers are found (an unnumbered agreement), the text falls
back to blank-line-separated paragraph blocks — every finding still gets a
stable label (`¶7`, `فقرة (سطر 12)`). Segmentation is pure text handling; the
document is never executed or interpreted as anything but text.

## 3. Rules — ~20 bilingual heuristic patterns

`lexiguard/rules.py`

Each rule declares: an id, severity, category (`ip|money|exit|liability|scope|data`),
the side it usually harms (`provider|client|both`), bilingual titles and
explanations, regex patterns, and a bilingual **counter-clause template**.

Matching mode per rule:

- `any` — the first pattern that matches fires the rule.
- `all` — every pattern must match somewhere in the same clause (used for
  compound traps like "IP assigns *and* before payment *and* advance").

Selection honors your config (`select_rules`): the ignore list, the
`min_severity` floor, and your `side`. Arabic patterns are written in folded
orthography (see below). All regexes are bounded (no nested unbounded
quantifiers) and pinned by `tests/test_rules.py` against catastrophic
backtracking.

## 4. Bilingual matching — Arabic orthography folding

`clauses.normalize_ar()` + `clauses.find_span()`

Arabic is written with enormous orthographic freedom: the same word appears
with or without tashkeel (حركات), with أ/إ/آ or bare ا, with ى or ي, with ة or
ه. If patterns matched raw bytes only, a rule written as `الملكية الفكرية`
would miss `المَلكِيَّة الفِكرِيَّة` or `ملكية الفكريه`.

**Folding (matching only — display keeps the original):**

| Change | Examples |
|---|---|
| strip tashkeel (harakat) + tatweel | `المَلكِيَّة` → `الملكية`, `الـملكية` → `الملكية` |
| أ إ آ → ا | `إقرار` → `اقرار`, `آجل` → `اجل` |
| ى → ي, ئ → ي | `المستثنى` → `المستثني`, `مسؤول` → `مسوول` |
| ؤ → و | `موصول` variants unified |
| ة → ه | `الملكية` → `الملكيه` |

**How it is applied:** each pattern is searched in the **raw** clause text
first; only if that fails is the Arabic-folded text searched
(`find_span()` uses `normalize_ar_map()`, a length-preserving fold that
records each folded character's raw offset). A folded match is therefore
mapped back to the exact span in the ORIGINAL text — snippets always show
the document's real (voweled) wording, never the folded haystack.

**What this means for recall/precision:** recall goes up — one rule catches
the many legitimate spellings of a term, which matters because contract
authors, OCR, and keyboard habits vary. The cost is precision: folded texts
collide more (e.g. `ة`≈`ه`), so a folded match may occasionally over-flag.
That is the intended trade-off: a first-pass reviewer that shouts a little
too often is safer than one that silently misses a one-sided clause — and
every signal still needs human eyes.

## 5. Score — transparent bands, never "safe"

`lexiguard/engine.py`

Points per finding: **high = 5, medium = 2, low = 1, info = 0**. The total is
printed in every report along with the arithmetic.

| Score | Band | Note |
|---|---|---|
| 12+ | `urgent` | high-signal clauses need review before signing |
| 5–11 | `review` | clauses worth negotiating |
| 1–4 | `watch` | lower-impact signals |
| 0 | `none` | "no known patterns detected — **NOT** a claim the contract is safe" |

The band is a **prioritization signal for a human**, not a legal conclusion.
The `none` band is deliberately never rendered as "safe/approved/clean", and
the report text says so explicitly.

## 6. Report — with counter-clause templates

`lexiguard/report.py` + `lexiguard/remedy.py`

Markdown, HTML (fully escaped), or JSON. Every format embeds the
not-legal-advice disclaimer (bilingual in md/html) at the top and bottom.
Snippets are shortened; the document body is never embedded in full — you
share *reports*, not contracts.

For each finding, a **counter-clause template** is attached from the rule
(fix_en/fix_ar). These are drafts for a human to adapt: bracketed values
like `[30]` days or `[X]%` **must be filled in**, and a lawyer must check the
result. Templates work fully offline.

### Optional layers (off by default)

- **AI rephrase** (`--ai gemini` + `GEMINI_API_KEY`): rephrases one template
  to fit your one-line deal hint. Sends **only** the template (+ hint +
  fixed system prompt) — never the document, snippet, or filename. Failure
  falls back silently to the offline template; reports label AI text.
  Details: [PRIVACY.md](PRIVACY.md).
- **Telegram ping** (`--notify` + bot env vars): sends **only** rule ids,
  counts, band and score. Never contract content. Setup:
  [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md).

## Running the tests

```bash
python -m unittest discover tests
```

The tests pin the bright lines: size caps, script stripping, honest scanned-PDF
errors, regex backtracking bounds, bilingual rule completeness, and clause
segmentation.

---

**Not legal advice** — Lexi-Guard Zero is a heuristic first-pass signal
generator for clause patterns; a licensed attorney reviews real agreements.
Support: baranavisat@gmail.com · WhatsApp +90 531 326 37 22
