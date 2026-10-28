# Privacy — what leaves your device, and what never does

> ⚠️ **NOT LEGAL ADVICE** — Lexi-Guard Zero is a heuristic first-pass signal
> generator; a licensed attorney reviews real agreements.

**Default posture: nothing leaves your device.** The full pipeline —
extraction, clause splitting, rule matching, scoring, and report rendering —
runs locally with the Python standard library. There is **no telemetry, no
analytics, no crash reporting, no update phoning home**. The only code in the
project that can open a network socket is the two opt-in features below, and
both are **off unless you configure them yourself**.

## Never leaves the device (always)

| Data | Why |
|---|---|
| The contract/document itself | read from your disk, stays on your disk |
| Extracted text and clause splits | in-memory only |
| Match snippets (≤ ~250 chars) | rendered into *your* report files |
| File names and paths | used locally only |
| Config `.lexiguard.json` | read from your working directory only |
| Reports (md/html/json) | written where *you* direct, via `-o` |

Reports are designed to be shareable *instead of* the contract: snippets are
short and the document body is never embedded in full.

## Opt-in #1 — Gemini rephrasing (`--ai gemini`)

Enabled only when **both** are true: you pass `--ai gemini` on the command
line **and** `GEMINI_API_KEY` is set in your environment. Per finding, one
HTTPS POST is made to Google's `generativelanguage.googleapis.com`
(`gemini-2.0-flash`), with a 20-second timeout and no retries.

**Exactly what is sent** (`lexiguard/remedy.py`, `_gemini()`):

1. A **fixed system prompt** (identical for every user, shipped in the code):
   *"You assist with contract negotiation drafts. Rephrase the given
   counter-clause template to fit the deal description, keeping it fair to
   BOTH parties, concise, and marked as a draft that a licensed attorney must
   review. Do not add guarantees, citations to real cases, or claims that it
   is legally sufficient."*
2. A user message of the literal form:

   ```
   Deal context (short): <your one-line --deal-hint, or "general service agreement">

   Counter-clause template to rephrase:
   EN: <template>        } capped together at MAX_TEMPLATE_CHARS = 1200
   AR: <template>        }
   ```

3. Generation config: `maxOutputTokens: 400`, `temperature: 0.2`.

**What is sent is only the rule's counter-clause TEMPLATE** — generic
boiler-plate text that is identical for every document the rule fires on.
The template is hard-capped at **1,200 characters**. Replies over 3,000 chars
or empty are discarded.

**What is never sent:** the contract, extracted text, clause bodies,
snippets, findings, severity counts, file names, paths — none of it is part
of the request. The only document-derived fact that can reach Google is
*your own* optional `--deal-hint` string, which you type and can omit
(the default placeholder is the generic phrase `"general service agreement"`).

Any network failure falls back silently to the offline template — the AI
layer can fail, the review cannot be blocked or degraded by it.

## Opt-in #2 — Telegram summary (`--notify`)

Enabled only when **both** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are
set (or passed explicitly in code). One HTTPS POST to
`api.telegram.org`, 15-second timeout, **HTTP redirects are refused**
(so a redirect response can never bounce the payload to another host), and
any error is returned as a status — it never breaks the scan.

**Exactly what is sent** — the entire summary object from
`lexiguard/notify.py`, `build_summary()`:

```json
{
  "tool": "lexiguard-zero",
  "band": "urgent",
  "score": 23,
  "counts": {"high": 4, "medium": 3, "low": 1, "info": 0},
  "rule_ids": ["LG-AUTORENEW", "LG-IP-PREPAY", "..."],
  "disclaimer": "automated pattern signals — not legal advice",
  "document": "document"
}
```

- `rule_ids` = the sorted, de-duplicated **rule identifiers only** (capped at
  40; if the message exceeds 1,500 chars a reduced payload keeps just the
  first 10 ids plus band/score/counts/disclaimer).
- `document` is the literal generic word **`"document"`** — the CLI never
  passes your file name or path (`build_summary`'s contract: callers must not
  pass a path).
- The message is prefixed with `Lexi-Guard Zero summary` and sent with web
  previews disabled.

**What is never sent:** no contract text, no snippets, no findings text, no
file names, no paths. Even if your chat were compromised, an eavesdropper
learns only that *some* document produced *these* rule ids and counts.

## Third parties, summarized

| Feature | Destination | Payload | Default |
|---|---|---|---|
| Core scan + report | — (nowhere) | — | local, always |
| `--ai gemini` | Google AI (Gemini free tier) | fixed prompt + your one-line deal hint + one rule's counter-clause template (≤1,200 chars) | **off** |
| `--notify` | your Telegram chat via api.telegram.org | rule ids + counts + band + score + disclaimer (≤1,500 chars) | **off** |

PDF text extraction (PyMuPDF/pdfplumber) also runs entirely locally.

## Verify it yourself

- Read `lexiguard/remedy.py` and `lexiguard/notify.py` — the payloads are
  short and quoted above.
- Run with networking observation tools (e.g. `lsof -i`, a firewall log):
  a plain `scan`/`report` run opens **zero** connections.
- `python -m lexiguard doctor` reports whether either opt-in layer is even
  configured.

---

**Not legal advice** — Lexi-Guard Zero is a heuristic first-pass signal
generator for clause patterns; a licensed attorney reviews real agreements.
Support: baranavisat@gmail.com · WhatsApp +90 531 326 37 22
