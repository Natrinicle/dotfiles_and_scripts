"""Shared predicates for interpreting decoded hub tool results."""

import re

# A hub that refuses ``kg_supersede`` / ``kg_invalidate`` because the old
# triple is not open says so with one of these phrasings (case-insensitive).
_STALE = re.compile(r"not (?:a )?current|no current fact", re.IGNORECASE)


def result_failed(result: object) -> bool:
    """True for a non-dict reply or one carrying ``success: false`` / ``error``."""
    return not isinstance(result, dict) or result.get("success") is False or "error" in result


def result_error(result: object) -> str:
    """Human-readable error text for a failed result."""
    if not isinstance(result, dict):
        return "bad reply"
    return str(result.get("error", "unknown error"))


def is_stale_error(text: str) -> bool:
    """True when an error says the referenced fact is not currently open."""
    return bool(_STALE.search(text or ""))
