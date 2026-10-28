# Lexi-Guard Zero

A **local, offline-first contract & document red-flag reviewer** for freelancers
and small businesses. It reads PDF/txt/md/html/rtf files **on your machine**,
splits them into clauses, matches ~20 bilingual (Arabic + English) heuristic
risk patterns, scores them with a transparent, auditable rubric, and writes
Markdown/HTML/JSON reports with fair counter-clause **templates**.

> ⚠️ **NOT LEGAL ADVICE.** Lexi-Guard Zero is a heuristic first-pass signal
> generator. It does not replace a licensed attorney; every report repeats
> this disclaimer. Have a qualified lawyer review any real agreement before
> you sign.

## Honest limits — read this first

- **It is a signal generator, not an oracle.** The engine only knows the
  patterns in its rule set (`lexiguard/rules.py`, 20 rules). Unusual wording
  can hide the same risk; ordinary wording can look risky. Findings may miss
  or over-flag.
- **Zero findings ≠ "safe".** The bottom band is literally named `none` —
  "no known patterns detected". It is never presented as clearance, approval,
  or a claim that the contract is legally clean.
- **No fake OCR.** Scanned/image-only PDFs are detected and reported honestly
  ("run `ocrmypdf` or Tesseract first"). The tool never pretends to read text
  it could not extract.
- **Counter-clause text is a TEMPLATE** for a human to adapt — bracketed
  values like `[30]` days or `[5]%` **must be filled in**. It is not a legal
  guarantee and may not fit your jurisdiction.
- **No accuracy claims.** Severities are negotiation signals, not proof of
  enforceability.
- **Contracts are confidential.** Everything runs locally; there is no
  telemetry. The optional AI/Telegram layers are off by default and send
  strictly limited payloads (see [docs/PRIVACY.md](docs/PRIVACY.md)).

## What it does

```
extract  →  clauses  →  rules  →  score  →  report
(PDF/txt/  (numbered   (20 bilingual  (transparent   (md/html/json +
 md/html/   headers or   heuristic      bands,         counter-clause
 rtf,       paragraphs)   patterns)      no "safe")     templates)
local)
```

Details: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

### Supported inputs

| Format | Backend | Notes |
|---|---|---|
| `.txt` `.md` `.markdown` `.csv` `.json` `.text` | stdlib | always works, zero deps |
| `.html` `.htm` | stdlib parser | `<script>`/`<style>` are **stripped as text**, never executed |
| `.rtf` | stdlib | lightweight control-word strip |
| `.pdf` | optional PyMuPDF **or** pdfplumber | if neither is installed, you get an honest error suggesting `pip install PyMuPDF` or `pdftotext`; scanned PDFs → honest "run OCR first" error |

Reads are capped at **5 MiB** per file and PDFs at **200 pages** (hostile-file
guards, see [SECURITY.md](SECURITY.md)).

## Install

Python 3.8+. The engine has **zero required dependencies**.

```bash
# Option A — no install at all, from the repo root:
python -m lexiguard --help

# Option B — editable install (exposes a `lexiguard` command):
pip install -e .
lexiguard --help
```

For PDF input, install one optional free backend (not required for
txt/md/html/rtf):

```bash
pip install PyMuPDF        # or: pip install pdfplumber
```

Run the environment check at any time:

```bash
python -m lexiguard doctor
```

## Quickstart

Using the bundled examples (`examples/`):

```bash
# Deliberately risky English contract — expect a high band
python -m lexiguard scan examples/sample-risky-en.txt

# Deliberately risky Arabic contract — same engine, Arabic patterns
python -m lexiguard scan examples/sample-risky-ar.txt

# Balanced sample viewed from the freelancer's side
python -m lexiguard scan examples/sample-fair-en.txt --side provider

# Full HTML report with counter-clause templates
python -m lexiguard report examples/sample-risky-en.txt -f html -o review-en.html

# Machine-readable JSON
python -m lexiguard report examples/sample-risky-ar.txt -f json -o review.json

# CI-style gate: exit code 2 if anything reaches "high"
python -m lexiguard scan examples/sample-risky-en.txt --fail-on high
```

### Commands

| Command | Purpose | Extra flags |
|---|---|---|
| `scan FILE` | quick console review | `--side`, `--ignore RULE_ID` (repeatable), `--min-severity`, `--fail-on low\|medium\|high`, `--notify` (Telegram, opt-in), `--ai gemini`, `--deal-hint "…"`, `--config` |
| `report FILE` | write a full report | `-f/--format markdown\|html\|json`, `-o/--output`, `--side`, `--config`, `--ai gemini`, `--deal-hint "…"` |
| `doctor` | check Python, optional PDF backends, config, AI/Telegram env vars | `--config` |

Common flags: `--config PATH` (alternate `.lexiguard.json`),
`--side provider|client|both` (whose perspective you sign from).
Exit codes: `0` ok · `1` error · `2` (`--fail-on` threshold reached) ·
`130` interrupted.

## Configuration — `.lexiguard.json`

Optional. Looked up in the working directory as `.lexiguard.json` (or
`lexiguard.json`), or point at a file with `--config`. All keys optional;
CLI flags override the file, and `--ignore` appends to the file's list.

```json
{
  "ignore_rules": ["LG-SETTLE-DISTANT-FORUM"],
  "min_severity": "low",
  "side": "provider"
}
```

| Key | Values | Effect |
|---|---|---|
| `ignore_rules` | array of rule ids | skip those rules entirely |
| `min_severity` | `info` \| `low` \| `medium` \| `high` | severity floor — hide findings below it |
| `side` | `provider` \| `client` \| `both` | keep only rules relevant to your side of the deal (`provider` = freelancer/vendor, `client` = buyer) |

A malformed config is an **error with a message**, never silently ignored.
The file is in `.gitignore` so local tweaks don't get committed.

## Scoring — transparent and auditable

Every finding contributes a fixed number of points; the arithmetic is printed
in every report:

| Severity | Points |
|---|---|
| high | 5 |
| medium | 2 |
| low | 1 |
| info | 0 (reserved) |

| Total score | Band | Meaning |
|---|---|---|
| 12+ | **urgent** | high-signal clauses need review before signing |
| 5–11 | **review** | clauses worth negotiating |
| 1–4 | **watch** | lower-impact signals |
| 0 | **none** | no known patterns detected — **NOT** a claim the contract is safe |

The band is a *prioritization* signal for a human, nothing more.

## Rule catalog (20 rules, bilingual)

`Side` = who the term usually harms: `provider` (you sell the work),
`client` (you buy it), `both`.

| ID | Severity | Category | Side | What it flags |
|---|---|---|---|---|
| LG-IP-PREPAY | high | ip | provider | Work-product IP transfers before (or without) payment |
| LG-NO-OWNERSHIP | high | ip | client | Client pays but acquires no rights in the work |
| LG-UNILATERAL-TERM | high | exit | provider | Client may terminate at will; provider has no equivalent right |
| LG-PERSONAL-GUARANTEE | high | liability | both | Personal guarantee / joint-and-several liability of the owner |
| LG-UNLIMITED-LIABILITY | high | liability | both | Unlimited liability for one or both parties |
| LG-ONEWAY-INDEMNITY | high | liability | provider | One-way indemnity running only against the provider |
| LG-LATE-PENALTY | medium | money | both | Daily or un-capped late-payment penalty |
| LG-COMPOUND-INTEREST | medium | money | both | Compounding interest on overdue amounts |
| LG-PAY-NET90 | medium | money | provider | Very long payment window (Net 60/90/120+) |
| LG-NONREFUNDABLE | medium | money | client | All payments non-refundable regardless of delivery |
| LG-FINAL-PAY-SUBJECTIVE | medium | money | provider | Final payment hinges on the client's subjective satisfaction |
| LG-UNILATERAL-AMEND | medium | exit | both | Contract can be amended unilaterally |
| LG-UNLIMITED-REVISIONS | medium | scope | provider | Unlimited revisions with no defined scope |
| LG-NONCOMPETE | medium | scope | provider | Broad non-compete restricting your other work |
| LG-MORAL-RIGHTS | medium | ip | provider | Blanket waiver of moral rights |
| LG-DEPOSIT-FULL | medium | money | client | 100% of the fee demanded in advance |
| LG-AUTORENEW | low | money | both | Automatic renewal without a notice window |
| LG-EXCLUSIVE | low | scope | provider | Exclusive engagement without a minimum guarantee |
| LG-SETTLE-DISTANT-FORUM | low | exit | both | Distant forum / foreign governing law |
| LG-CONF-INDEFINITE | low | data | both | Confidentiality obligations that never end |

Every rule ships with a plain-language explanation and a bilingual
**counter-clause template** in both reports. Templates contain bracketed
placeholders (`[30]`, `[X]%`, `[country]`) that you must fill in and adapt —
with your lawyer.

## Optional AI rephrasing (off by default)

Gemini free tier can rephrase a counter-clause template to fit your deal's
wording. The offline templates are always available and the default.

```bash
export GEMINI_API_KEY="your-key"       # from Google AI Studio (free tier)
python -m lexiguard report contract.pdf --ai gemini --deal-hint "logo design, fixed fee"
```

**What it sends: only the flagged rule's counter-clause template** (capped at
1,200 chars) plus your optional one-line deal hint and a fixed system prompt.
**Never** the document, snippets, findings, or file name. Any failure falls
back silently to the offline template; reports label AI-rephrased text.
Details and the exact payload: [docs/PRIVACY.md](docs/PRIVACY.md).

## Optional Telegram summary (off by default)

Push a **summary-only** ping to a Telegram chat you own — rule ids and counts,
never contract text:

```bash
export TELEGRAM_BOT_TOKEN="123:abc…"
export TELEGRAM_CHAT_ID="123456789"
python -m lexiguard scan contract.pdf --notify
```

Setup walkthrough: [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md).
Guarantee: the payload contains band, score, counts, rule ids and the
disclaimer — no document text, no snippets, no file names. If anything goes
wrong the scan still succeeds; the notify line simply reports `skipped`/`error`.

## More documentation

- [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) — pipeline & bilingual matching
- [docs/PRIVACY.md](docs/PRIVACY.md) — what never leaves your device
- [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md) — free Telegram setup
- [SECURITY.md](SECURITY.md) — threat model for hostile documents
- [README_AR.md](README_AR.md) — النسخة العربية

## Support & contact

Questions, issues, feature requests:

- **Email:** baranavisat@gmail.com
- **WhatsApp:** +90 531 326 37 22
- **GitHub:** [aoodiakdiro0001-ops](https://github.com/aoodiakdiro0001-ops)

## License

MIT (c) 2026 Baran Avisat — Aodı Akdıro Suite. See [LICENSE](LICENSE).

---

**Not legal advice** — Lexi-Guard Zero is a heuristic first-pass signal
generator for clause patterns; a licensed attorney reviews real agreements.
Support: baranavisat@gmail.com · WhatsApp +90 531 326 37 22
