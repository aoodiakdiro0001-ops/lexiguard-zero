# Security

> ⚠️ **NOT LEGAL ADVICE** — Lexi-Guard Zero is a heuristic first-pass signal
> generator; a licensed attorney reviews real agreements.

## Threat model: hostile document files

The primary threat is a **malicious or malformed contract file** — you are
reviewing a document an opposing party gave you, so treat it as hostile
input. The engine is built so that a worst-case file can at worst produce a
weird report, never code execution, unbounded resource use, or exfiltration.

| Guard | Implementation (`lexiguard/extract.py` and friends) |
|---|---|
| **No execution** | Nothing from the document is ever executed, imported, evaluated, or rendered as a program. Formats are parsed as plain text only; there is no macro/script support in any backend. |
| **No HTML interpretation** | `.html` files go through a stdlib `HTMLParser` that extracts text nodes; `<script>`, `<style>`, `<noscript>`, `<template>`, `<svg>`, `<head>` subtrees are dropped as text (pinned by `tests/test_extract.py::test_script_stripped_not_executed`). Tags are never "run" — a `<script>` in a contract page is just text we discard. |
| **Size caps** | Every file read is capped at **5 MiB** (`MAX_BYTES`); larger files are truncated *with a visible warning*, so a hostile file cannot exhaust memory. |
| **Page caps** | PDFs are processed at most **200 pages**; beyond that extraction stops with a warning (guard against decompression/page bombs). |
| **Bounded regexes** | All rule patterns use bounded quantifiers (`{0,90}` etc.), never nested unbounded repetition. `tests/test_rules.py::test_no_catastrophic_backtracking` pins a time bound on adversarial inputs (ReDoS guard). Clause segmentation is linear over lines. |
| **Safe decoding** | Byte input is decoded through a fixed fallback chain (utf-8 → utf-8-sig → utf-16 → cp1256 → latin-1 → utf-8/replace); decode errors never crash or execute. |
| **Honest failure** | Unreadable or empty input raises `ExtractError` with a truthful message. Scanned/image-only PDFs are reported as such ("run `ocrmypdf` or Tesseract first") — the tool never fabricates content it did not extract. |
| **Output escaping** | HTML reports escape all interpolated content (`html.escape`); snippets are short and bounded. Reports embed snippets, never the full document. |
| **Temporary files** | PyMuPDF extraction writes an anonymous temp copy that is deleted in a `finally` block; the original file is only ever opened for reading. |

## Network bright lines

By default the tool opens **zero** network connections. The only two
network-capable paths are explicitly documented, opt-in per run, and
payload-constrained:

1. **Gemini rephrasing** (`--ai gemini` + `GEMINI_API_KEY`) — sends only a
   fixed system prompt, your optional one-line deal hint, and one rule's
   generic counter-clause template (hard cap 1,200 chars). Never the
   document, snippets, findings, or filenames. Single POST, 20 s timeout,
   no retries; any failure falls back offline (fail-closed). Reports label
   AI-rephrased text. Exact payload: [docs/PRIVACY.md](docs/PRIVACY.md).
2. **Telegram summary** (`--notify` + bot env vars) — sends only rule ids,
   counts, band, score and the disclaimer (≤ 1,500 chars); `document` is the
   literal word `document`, never a path. **HTTP redirects are refused**, so
   the payload cannot be bounced to an attacker-controlled hop. 15 s
   timeout; errors return a status instead of raising.

There is **no telemetry** of any kind: no analytics, no crash uploads, no
phone-home updates.

## Product bright lines (pinned by tests where noted)

- **NOT LEGAL ADVICE.** Every textual output path embeds the disclaimer
  (console, Markdown, HTML, JSON). The tool is a first-pass signal generator
  for a human; a licensed attorney reviews real deals.
- **No accuracy claims.** No "100% accurate", no "replaces your lawyer"
  anywhere in code or docs. Severities are negotiation signals, not proof of
  enforceability.
- **Never "safe".** The zero-score band is named `none` and rendered as
  "no known patterns detected — NOT a claim the contract is safe".
- **Local-first privacy.** Contracts are confidential, read on-device; the AI
  layer is off by default and sends only counter-clause templates; Telegram
  sends summary-only.
- **Counter-clause text is a TEMPLATE**, not a legal guarantee: bracketed
  values (`[30]`, `[X]%`) must be filled in by a human, who should have a
  lawyer adapt it.

## Reporting a vulnerability

Email **baranavisat@gmail.com** with:

- the affected file/feature (e.g. extraction, a specific rule id, notify)
- a minimal reproduction (a small sample file or command line — please
  redact any real contract you cannot share)
- impact you observed (crash, hang, unexpected output, unwanted network)

You will get an acknowledgment as soon as possible; fixes ship as a normal
release with the bright lines re-pinned by the test suite.

---

**Not legal advice** — Lexi-Guard Zero is a heuristic first-pass signal
generator for clause patterns; a licensed attorney reviews real agreements.
Support: baranavisat@gmail.com · WhatsApp +90 531 326 37 22
