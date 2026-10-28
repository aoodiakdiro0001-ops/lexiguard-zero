# -*- coding: utf-8 -*-
"""Optional notifications — SUMMARY ONLY, never contract content.

A scan summary (band + counts + rule ids) can be pushed to a Telegram
chat you own. The bright line, enforced below: NO document text, NO
snippets, NO file names ever leave via this path — only rule ids and
counts, so even a compromised chat leaks nothing confidential.

Fail-closed behavior (same pattern as Code-Shield's notifier):
  * no token/chat id configured -> skip, return skipped status
  * HTTP redirects are NOT followed (no accidental exfiltration hop)
  * response read is capped; errors never raise into the CLI
"""
import json
import os

try:
    from urllib.request import Request, build_opener, HTTPRedirectHandler
    from urllib.error import URLError, HTTPError
except ImportError:                     # pragma: no cover
    raise

API = "https://api.telegram.org/bot%s/sendMessage"
TIMEOUT = 15
MAX_CHARS = 1500


class _NoRedirect(HTTPRedirectHandler):
    """Refuse every redirect (301/302/303/307/308) — a summary ping must
    never be bounced to an attacker-controlled hop."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code,
                        "redirects are not followed by lexiguard notify",
                        headers, fp)


class NotifyResult(object):
    __slots__ = ("status", "detail")

    def __init__(self, status, detail=""):
        self.status = status            # sent|skipped|error
        self.detail = detail

    def as_dict(self):
        return {"status": self.status, "detail": self.detail}


def build_summary(result, doc_label="document"):
    """Compliant payload: counts + rule ids only. `doc_label` defaults to
    a generic word and callers must not pass a path — see send()."""
    counts = result.counts()
    ids = sorted(set(f.rule.id for f in result.findings))
    return {
        "tool": "lexiguard-zero",
        "band": result.band,
        "score": result.score,
        "counts": counts,
        "rule_ids": ids[:40],
        "disclaimer": "automated pattern signals — not legal advice",
        "document": doc_label,
    }


def send(result, chat_id=None, token=None, doc_label="document"):
    """Push a summary to your own Telegram chat. Opt-in: requires
    TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID (or explicit args)."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return NotifyResult("skipped", "no TELEGRAM_BOT_TOKEN/"
                            "TELEGRAM_CHAT_ID configured")
    summary = build_summary(result, doc_label)
    payload = json.dumps(summary, ensure_ascii=False)
    if len(payload) > MAX_CHARS:
        payload = json.dumps({"tool": "lexiguard-zero",
                              "band": summary["band"],
                              "score": summary["score"],
                              "counts": summary["counts"],
                              "rule_ids": summary["rule_ids"][:10],
                              "disclaimer": summary["disclaimer"]},
                             ensure_ascii=False)
    body = json.dumps({"chat_id": str(chat_id),
                       "text": "Lexi-Guard Zero summary\n" + payload,
                       "disable_web_page_preview": True}).encode("utf-8")
    req = Request(API % token, data=body,
                  headers={"Content-Type": "application/json"},
                  method="POST")
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            resp.read(MAX_CHARS)
        return NotifyResult("sent")
    except (HTTPError, URLError, OSError, ValueError) as e:
        return NotifyResult("error", str(e)[:200])
