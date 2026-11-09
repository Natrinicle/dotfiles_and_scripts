"""Secret pattern detection for company content writes.

Detects common secret patterns (AWS keys, tokens, API keys, etc.) to prevent
accidental exposure when routing content to company targets.
"""

import re
from typing import Optional

# Patterns compiled once at module level as ordered list of (name, compiled_regex)
_PATTERNS = [
    ("aws_access_key", re.compile(r"AKIA[A-Z2-7]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("slack_token", re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}")),
    ("twilio_account_sid", re.compile(r"\bAC[0-9a-f]{32}\b")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer_header", re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{20,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}")),
]


def find_secret(text: str) -> Optional[str]:
    """Find the first matching secret pattern in text.

    Args:
        text: The text to search for secret patterns.

    Returns:
        The name of the first matching pattern (e.g., "aws_access_key", "github_token"),
        or None if no patterns match.
    """
    for pattern_name, regex in _PATTERNS:
        if regex.search(text):
            return pattern_name
    return None
