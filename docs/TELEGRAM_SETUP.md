# Telegram Setup — summary-only notifications (free)

> ⚠️ **NOT LEGAL ADVICE** — Lexi-Guard Zero is a heuristic first-pass signal
> generator; a licensed attorney reviews real agreements.

Telegram delivery is **opt-in and summary-only**: band, score, counts, rule
ids and the disclaimer. **No contract text, no snippets, no file names ever
leave via this path** — see the payload section below and
[PRIVACY.md](PRIVACY.md). If you skip this entirely, nothing changes about
scanning; notifications are simply never sent.

## Step 1 — create a bot (token) with BotFather

1. In Telegram, open a chat with **@BotFather**.
2. Send `/newbot`.
3. Choose a display name (e.g. `Lexi Guard Notifier`) and a username ending
   in `bot` (e.g. `my_lexiguard_bot`).
4. BotFather replies with an **HTTP API token** like
   `123456789:AAE-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
   Treat this token like a password — anyone with it can post as your bot.

## Step 2 — get your chat id

1. Send any message to your new bot (e.g. `/start`) — a bot cannot message
   you before you message it.
2. In a browser, open:

   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```

3. In the JSON, find `"chat":{"id": 123456789, ...}` — that number is your
   **chat id**. (For a group, add the bot to the group, send a message
   mentioning it, and read the group chat id.)

## Step 3 — export the environment variables

In your shell (or CI secrets):

```bash
export TELEGRAM_BOT_TOKEN="123456789:AAE-xxxx…"
export TELEGRAM_CHAT_ID="123456789"
```

To persist, add both lines to `~/.bashrc` / `~/.zshrc`. Never commit them to
git.

## Step 4 — send a test ping

```bash
python -m lexiguard doctor                 # shows: telegram: configured
python -m lexiguard scan examples/sample-risky-en.txt --notify
```

Console output ends with `notify: sent` (or `skipped`/`error` — the scan
result itself is unaffected either way; notifications are fail-closed).

Sample message your chat receives:

```
Lexi-Guard Zero summary
{"tool": "lexiguard-zero", "band": "urgent", "score": 23,
 "counts": {"high": 4, "medium": 3, "low": 1, "info": 0},
 "rule_ids": ["LG-AUTORENEW", "LG-IP-PREPAY", "LG-UNILATERAL-TERM", "..."],
 "disclaimer": "automated pattern signals — not legal advice",
 "document": "document"}
```

## The summary-only guarantee (enforced in code)

The payload is built by `build_summary()` in `lexiguard/notify.py` and
contains **only**:

| Field | Content |
|---|---|
| `tool` | the literal string `lexiguard-zero` |
| `band` / `score` | risk band name and point total |
| `counts` | findings per severity (numbers only) |
| `rule_ids` | sorted rule identifiers, e.g. `LG-LATE-PENALTY` (≤ 40) |
| `disclaimer` | fixed one-liner |
| `document` | the literal generic word `document` — never your file name |

Never included: contract text, extracted text, snippets, findings wording,
file names, paths. Additional hardening:

- HTTP **redirects are refused** — the payload cannot be bounced to a
  different host.
- 15-second timeout; oversized summaries shrink to ids-only automatically.
- Errors are caught and returned as a status; they never break a scan.

## Security hygiene

- Keep the token secret; rotate it with BotFather (`/revoke` token or
  `/token`) if it leaks.
- Prefer a chat you alone control; the payload is harmless, but your band
  history is still your business.
- Chat ids and tokens belong in environment variables, not in
  `.lexiguard.json` (that file holds only rule filters).

---

**Not legal advice** — Lexi-Guard Zero is a heuristic first-pass signal
generator for clause patterns; a licensed attorney reviews real agreements.
Support: baranavisat@gmail.com · WhatsApp +90 531 326 37 22
