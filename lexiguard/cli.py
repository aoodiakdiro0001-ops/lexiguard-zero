# -*- coding: utf-8 -*-
"""Lexi-Guard Zero CLI.

    lexiguard scan  contract.pdf [--side provider] [--ai gemini]
    lexiguard report contract.pdf -f html -o review.html
    lexiguard doctor

Every textual output path embeds the not-legal-advice disclaimer.
Documents are read locally; nothing is uploaded unless you explicitly
enable the optional AI rephrasing or Telegram summary (both off by
default, both documented in README.md).
"""
import argparse
import os
import sys

from . import __version__, DISCLAIMER_EN
from . import config as _config
from . import engine, extract, notify, remedy, report


def _load_cfg(args):
    cfg = _config.load(getattr(args, "config", None))
    # CLI flags override file config, they never widen it silently.
    if getattr(args, "side", None):
        cfg = _config.Config(cfg.ignore_rules, cfg.min_severity,
                             args.side, cfg.path)
    if getattr(args, "ignore", None):
        cfg = _config.Config(tuple(cfg.ignore_rules) + tuple(args.ignore),
                             cfg.min_severity, cfg.side, cfg.path)
    if getattr(args, "min_severity", None):
        cfg = _config.Config(cfg.ignore_rules, args.min_severity,
                             cfg.side, cfg.path)
    return cfg


def _scan_file(path, args):
    cfg = _load_cfg(args)
    doc = extract.extract(path)
    return engine.scan(doc, cfg), cfg


def _print_summary(result, remedies=None):
    d = result.document
    counts = result.counts()
    by_rule = {}
    for rem in (remedies or []):
        by_rule.setdefault(rem.rule_id, []).append(rem)
    print("Lexi-Guard Zero %s — local review" % __version__)
    print("document: %s (via %s, %d chars%s)" % (
        d.source, d.method, d.chars,
        ", %d pages" % d.pages if d.pages else ""))
    for w in d.warnings:
        print("  warning: %s" % w)
    print("band: %s — %s" % (result.band.upper(), result.band_en))
    print("score: %d (high=5 medium=2 low=1)" % result.score)
    print("findings: %d high · %d medium · %d low · %d info" % (
        counts["high"], counts["medium"], counts["low"], counts["info"]))
    if not result.findings:
        print("(no known patterns — NOT a clearance)")
    for f in result.sorted_findings():
        loc = f.location
        if f.location_ar != loc:
            loc = "%s / %s" % (f.location_ar, loc)
        print("  [%s] %s %s — %s" % (
            f.severity.upper(), f.rule.id, loc, f.rule.title_en))
        print("      %s" % f.snippet[:160])
        for rem in by_rule.get(f.rule.id, []):
            tag = " (AI draft)" if rem.source == "gemini" else ""
            print("      ⟶ counter%s: %s" % (tag, rem.text_en[:160]))
            print("      ⟶ البديل: %s" % rem.text_ar[:120])
    print("DISCLAIMER: %s" % DISCLAIMER_EN)


def cmd_scan(args):
    result, cfg = _scan_file(args.file, args)
    if cfg.path:
        print("config: %s (ignored %d rule(s), min_severity=%s, side=%s)"
              % (cfg.path, len(cfg.ignore_rules), cfg.min_severity,
                 cfg.side or "both"), file=sys.stderr)
    use_ai = args.ai == "gemini"
    if use_ai and not os.environ.get("GEMINI_API_KEY"):
        print("note: --ai gemini needs GEMINI_API_KEY in the environment; "
              "using offline templates", file=sys.stderr)
        use_ai = False
    rems = None
    if use_ai or getattr(args, "remedies", False):
        rems = remedy.remedies_for(result, use_ai=use_ai,
                                   deal_hint=getattr(args, "deal_hint", ""))
        if use_ai and any(r.source == "offline" for r in rems):
            print("note: AI unavailable for some suggestions — offline "
                  "templates used instead", file=sys.stderr)
    _print_summary(result, rems)
    if args.notify:
        n = notify.send(result)
        print("notify: %s %s" % (n.status, n.detail))
    if args.fail_on:
        from .rules import SEVERITY_RANK
        floor = SEVERITY_RANK.get(args.fail_on, 99)
        if any(SEVERITY_RANK.get(f.severity, 0) >= floor
               for f in result.findings):
            return 2
    return 0


def cmd_report(args):
    result, cfg = _scan_file(args.file, args)
    if cfg.path:
        print("config: %s (ignored %d rule(s), min_severity=%s, side=%s)"
              % (cfg.path, len(cfg.ignore_rules), cfg.min_severity,
                 cfg.side or "both"), file=sys.stderr)
    use_ai = args.ai == "gemini"
    if use_ai and not os.environ.get("GEMINI_API_KEY"):
        print("note: --ai gemini needs GEMINI_API_KEY in the environment; "
              "using offline templates", file=sys.stderr)
        use_ai = False
    rems = remedy.remedies_for(result, use_ai=use_ai,
                               deal_hint=getattr(args, "deal_hint", ""))
    if use_ai and any(r.source == "offline" for r in rems):
        print("note: AI unavailable for some suggestions — offline "
              "templates used instead", file=sys.stderr)
    text = report.render(result, args.format, rems)
    if args.output:
        if os.path.exists(args.output):
            print("note: overwriting existing file %s" % args.output,
                  file=sys.stderr)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s (%d bytes) — band %s, %d findings" % (
            args.output, len(text.encode("utf-8")), result.band.upper(),
            len(result.findings)))
        print("DISCLAIMER: %s" % DISCLAIMER_EN)
    else:
        print(text)
    return 0


def cmd_doctor(args):
    print("Lexi-Guard Zero %s doctor" % __version__)
    print("python: %s" % sys.version.split()[0])
    for mod, purpose in (("fitz", "PyMuPDF (PDF text extraction)"),
                         ("pdfplumber", "alternative PDF backend")):
        try:
            __import__(mod)
            print("  [ok] %s available" % purpose)
        except Exception:
            print("  [--] %s not installed (optional)" % purpose)
    print("  [--] OCR: never bundled (scanned PDFs are reported honestly)")
    try:
        cfg = _config.load(getattr(args, "config", None))
        print("config: %s (min_severity=%s side=%s ignored=%d)" % (
            cfg.path or "<defaults>", cfg.min_severity,
            cfg.side or "both", len(cfg.ignore_rules)))
    except ValueError as e:
        print("config: ERROR %s" % e)
        return 1
    print("gemini key: %s" % ("set" if os.environ.get("GEMINI_API_KEY")
                              else "not set (offline mode)"))
    print("telegram: %s" % ("configured" if os.environ.get(
        "TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")
        else "not configured (notifications skipped)"))
    print("privacy: documents are read locally; no telemetry; the AI "
          "layer sends only counter-clause templates when enabled")
    print("DISCLAIMER: %s" % DISCLAIMER_EN)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="lexiguard",
        description="Local contract red-flag reviewer — not legal advice.")
    p.add_argument("--version", action="version",
                   version="lexiguard %s" % __version__)
    sub = p.add_subparsers(dest="cmd")

    def common(sp):
        sp.add_argument("file", help="document to review (.pdf/.txt/.md/"
                        ".markdown/.csv/.json/.text/.html/.rtf)")
        sp.add_argument("--config", help="path to .lexiguard.json")
        sp.add_argument("--side", choices=("provider", "client", "both"),
                        help="whose perspective you sign from")

    sp = sub.add_parser("scan", help="quick console review")
    common(sp)
    sp.add_argument("--ignore", action="append", metavar="RULE_ID",
                    help="skip a rule (repeatable)")
    sp.add_argument("--min-severity", dest="min_severity",
                    choices=("info", "low", "medium", "high"))
    sp.add_argument("--remedies", action="store_true",
                    help="print counter-clause templates in the console")
    sp.add_argument("--ai", choices=("gemini",),
                    help="opt-in AI rephrasing of suggestions "
                    "(implies --remedies)")
    sp.add_argument("--deal-hint", dest="deal_hint", default="",
                    help="one-line deal context (sent to AI only if --ai)")
    sp.add_argument("--notify", action="store_true",
                    help="send a summary-only Telegram ping (opt-in)")
    sp.add_argument("--fail-on", dest="fail_on",
                    choices=("low", "medium", "high"),
                    help="exit 2 if any finding reaches this severity")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("report", help="write a full report file")
    common(sp)
    sp.add_argument("-f", "--format", default="markdown",
                    choices=("markdown", "md", "html", "json"))
    sp.add_argument("-o", "--output", help="output file (default: stdout)")
    sp.add_argument("--ai", choices=("gemini",))
    sp.add_argument("--deal-hint", dest="deal_hint", default="")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("doctor", help="environment + config check")
    sp.add_argument("--config", help="path to .lexiguard.json")
    sp.set_defaults(func=cmd_doctor)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 1
    try:
        return args.func(args) or 0
    except extract.ExtractError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
