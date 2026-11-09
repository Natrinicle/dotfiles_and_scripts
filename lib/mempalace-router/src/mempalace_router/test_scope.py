"""Tests for scope normalization."""

import unittest
from pathlib import Path

from mempalace_router.config import Target, Targets
from mempalace_router.scope import ScopeError, normalize_scope


class ScopeNormalizationTest(unittest.TestCase):
    """Test scope normalization."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a local target
        self.local_target = Target(
            name="local",
            kind="local",
            company=None,
            url="http://127.0.0.1:9999",
            token_file=None,
            palace_path=Path("/tmp/palace"),
            hints={},
        )

        # Create company targets
        self.acme_target = Target(
            name="acme",
            kind="company",
            company="acme",
            url="http://acme.example.com",
            token_file=Path("/tmp/acme_token"),
            palace_path=None,
            hints={},
        )

        self.globex_target = Target(
            name="globex",
            kind="company",
            company="globex",
            url="http://globex.example.com",
            token_file=Path("/tmp/globex_token"),
            palace_path=None,
            hints={},
        )

        # Create targets object
        self.targets = Targets(
            by_name={
                "local": self.local_target,
                "acme": self.acme_target,
                "globex": self.globex_target,
            },
            local=self.local_target,
            companies={
                "acme": self.acme_target,
                "globex": self.globex_target,
            },
        )

    def test_default_is_local(self):
        """None or empty list should return ([local], [])."""
        # Test with None
        targets, notes = normalize_scope(None, self.targets)
        self.assertEqual(targets, ["local"])
        self.assertEqual(notes, [])

        # Test with empty list
        targets, notes = normalize_scope([], self.targets)
        self.assertEqual(targets, ["local"])
        self.assertEqual(notes, [])

    def test_company_only_gets_local_prepended_with_note(self):
        """Company only in scope should prepend local with note."""
        targets, notes = normalize_scope(["acme"], self.targets)
        self.assertEqual(targets, ["local", "acme"])
        self.assertIn("local added to scope", notes)

    def test_local_plus_company_keeps_order_local_first(self):
        """Local + company should keep order with local first."""
        # When local is first
        targets, notes = normalize_scope(["local", "acme"], self.targets)
        self.assertEqual(targets, ["local", "acme"])
        self.assertEqual(notes, [])

        # When company is first (should still put local first)
        targets, notes = normalize_scope(["acme", "local"], self.targets)
        self.assertEqual(targets, ["local", "acme"])
        self.assertEqual(notes, [])

    def test_two_companies_rejected(self):
        """Two distinct companies should raise ScopeError with code cross_company_scope."""
        with self.assertRaises(ScopeError) as cm:
            normalize_scope(["acme", "globex"], self.targets)
        self.assertEqual(cm.exception.code, "cross_company_scope")

    def test_unknown_target_rejected(self):
        """Unknown target name should raise ScopeError with code unknown_target."""
        with self.assertRaises(ScopeError) as cm:
            normalize_scope(["unknown"], self.targets)
        self.assertEqual(cm.exception.code, "unknown_target")

    def test_duplicates_collapsed(self):
        """Duplicate targets should be collapsed."""
        targets, notes = normalize_scope(["local", "acme", "local"], self.targets)
        self.assertEqual(targets, ["local", "acme"])
        self.assertEqual(notes, [])
