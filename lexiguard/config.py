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
    file -> defaults. Malformed file -> ValueError with a clear message
    (never silently ignored: a typo'd rule id should be visible)."""
    candidates = [path] if path else [
        os.path.join(os.getcwd(), n) for n in CONFIG_NAMES]
    for cand in candidates:
        if cand and os.path.isfile(cand):
            try:
                with open(cand, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError) as e:
                raise ValueError("bad config %s: %s" % (cand, e))
            if not isinstance(data, dict):
                raise ValueError("config %s must be a JSON object" % cand)
            return Config(
                ignore_rules=tuple(data.get("ignore_rules") or ()),
                min_severity=data.get("min_severity") or "info",
                side=data.get("side") or None,
                path=cand)
    return Config()


def default():
    return Config()
