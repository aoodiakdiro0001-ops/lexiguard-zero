# -*- coding: utf-8 -*-
"""User configuration — .lexiguard.json in the working directory.

Everything is optional; defaults are the widest safe review:

    {
      "ignore_rules": ["LG-SETTLE-DISTANT-FORUM"],
      "min_severity": "low",          // info|low|medium|high
      "side": "provider"              // provider|client|both(null)
    }

`side` filters findings to the party whose perspective you sign from:
a freelancer picks "provider", the business buying the work picks
"client". Documents are still never uploaded anywhere.
"""
import json
import os

from .rules import SEVERITIES

CONFIG_NAMES = (".lexiguard.json", "lexiguard.json")
VALID_SIDES = ("provider", "client", "both")


class Config(object):
    __slots__ = ("ignore_rules", "min_severity", "side", "path")

    def __init__(self, ignore_rules=(), min_severity="info", side=None,
                 path=None):
        self.ignore_rules = tuple(ignore_rules)
        if min_severity not in SEVERITIES:
            raise ValueError("min_severity must be one of %s"
                             % (SEVERITIES,))
        self.min_severity = min_severity
        if side not in (None,) + VALID_SIDES:
            raise ValueError("side must be one of %s or null"
                             % (VALID_SIDES,))
        self.side = None if side == "both" else side
        self.path = path

    def as_dict(self):
        return {"ignore_rules": list(self.ignore_rules),
                "min_severity": self.min_severity,
                "side": self.side or "both", "path": self.path}


def load(path=None):
    """Load config from `path` or the first CONFIG_NAMES found. Missing
    file -> defaults ONLY when no explicit path was requested; a
    malformed or oversized file, or a typo'd/unknown rule id, raises
    ValueError (never silently ignored: narrowing a review must be
    visible)."""
    if path:
        candidates = [path]
    else:
        candidates = [os.path.join(os.getcwd(), n) for n in CONFIG_NAMES]
    for cand in candidates:
        if cand and os.path.isfile(cand):
            if os.path.getsize(cand) > 1024 * 1024:
                raise ValueError("config too large (1 MiB max): %s" % cand)
            try:
                with open(cand, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError) as e:
                raise ValueError("bad config %s: %s" % (cand, e))
            if not isinstance(data, dict):
                raise ValueError("config %s must be a JSON object" % cand)
            ignore = data.get("ignore_rules") or ()
            if not isinstance(ignore, (list, tuple)):
                raise ValueError("ignore_rules must be a list of rule ids "
                                 "in %s" % cand)
            from .rules import RULES_BY_ID
            unknown = [r for r in ignore if r not in RULES_BY_ID]
            if unknown:
                raise ValueError("unknown rule id(s) in %s: %s"
                                 % (cand, ", ".join(str(u) for u in
                                                    unknown)))
            return Config(
                ignore_rules=tuple(ignore),
                min_severity=data.get("min_severity") or "info",
                side=data.get("side") or None,
                path=cand)
    if path:
        # An explicit --config that does not exist is an error, not
        # silent defaults (a missing narrowing file must be visible).
        raise ValueError("config file not found: %s" % path)
    return Config()


def default():
    return Config()
