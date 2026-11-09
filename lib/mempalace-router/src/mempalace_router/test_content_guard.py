"""Tests for content_guard module — secret pattern detection."""

import unittest
from mempalace_router.content_guard import find_secret


class TestContentGuard(unittest.TestCase):
    """Test suite for find_secret() pattern detection."""

    def test_aws_access_key(self):
        """Detect AWS access key pattern: AKIA[A-Z2-7]{16}."""
        # Build canary at runtime
        aws_key = "AKIA" + "A" * 16
        result = find_secret(aws_key)
        self.assertEqual(result, "aws_access_key")

    def test_github_token(self):
        """Detect GitHub token pattern: gh[pousr]_[A-Za-z0-9]{36,}."""
        # Build canary at runtime
        gh_token = "gh" + "p_" + "a" * 36
        result = find_secret(gh_token)
        self.assertEqual(result, "github_token")

    def test_slack_token(self):
        """Detect Slack token pattern: xox[abprs]-[A-Za-z0-9-]{10,}."""
        # Build canary at runtime
        slack_token = "xox" + "b-" + "1" * 12
        result = find_secret(slack_token)
        self.assertEqual(result, "slack_token")

    def test_twilio_account_sid(self):
        """Detect Twilio Account SID pattern: \\bAC[0-9a-f]{32}\\b."""
        # Build canary at runtime
        twilio_sid = "AC" + "0" * 32
        result = find_secret(twilio_sid)
        self.assertEqual(result, "twilio_account_sid")

    def test_google_api_key(self):
        """Detect Google API key pattern: AIza[0-9A-Za-z\\-_]{35}."""
        # Build canary at runtime
        google_key = "AIza" + "A" * 35
        result = find_secret(google_key)
        self.assertEqual(result, "google_api_key")

    def test_private_key_block(self):
        """Detect private key block pattern: -----BEGIN [A-Z ]*PRIVATE KEY-----."""
        # Build canary at runtime
        pkey = "-----BEGIN " + "RSA PRIVATE KEY-----"
        result = find_secret(pkey)
        self.assertEqual(result, "private_key_block")

    def test_bearer_header(self):
        """Detect Bearer auth header pattern: (?i)authorization:\\s*bearer\\s+[A-Za-z0-9._\\-]{20,}."""
        # Build canary at runtime
        bearer = "authorization: " + "bearer " + "x" * 24
        result = find_secret(bearer)
        self.assertEqual(result, "bearer_header")

    def test_jwt(self):
        """Detect JWT pattern: eyJ[A-Za-z0-9_-]{10,}\\.eyJ[A-Za-z0-9_-]{10,}."""
        # Build canary at runtime
        jwt_token = "eyJ" + "a" * 12 + "." + "eyJ" + "b" * 12
        result = find_secret(jwt_token)
        self.assertEqual(result, "jwt")

    def test_clean_text_is_none(self):
        """Clean text with no secrets returns None."""
        result = find_secret("This is just a normal string with no secrets.")
        self.assertIsNone(result)

    def test_env_var_names_are_not_secrets(self):
        """Environment variable names with placeholder values are clean."""
        # Text like "TOKEN=<redacted>" or "MEMPALACE_MCP_HTTP_TOKEN=…" is clean
        text = "MEMPALACE_MCP_HTTP_TOKEN=<redacted>"
        result = find_secret(text)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
