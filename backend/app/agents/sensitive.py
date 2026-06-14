"""Shared sensitive data patterns for agent traces and replays."""

import re

SENSITIVE_KEY_RE = re.compile(
    r"(^authorization$|^cookie$|password|secret|private[_-]?key|api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?token|id[_-]?token)",
    re.IGNORECASE,
)
