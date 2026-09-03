"""Small security helpers shared by logs, scripts and graph error states."""

import re


_SENSITIVE_QUERY_VALUE = re.compile(
    r"(?i)([?&](?:key|api[_-]?key|access[_-]?token)=)[^&\s\"']+"
)


def redact_sensitive_text(value: object) -> str:
    """Mask credential values embedded in URLs or exception messages."""
    return _SENSITIVE_QUERY_VALUE.sub(r"\1<redacted>", str(value))

