#!/usr/bin/env python3
"""Tests for identity candidate heuristics. Fake tokens only."""

from __future__ import annotations

import unittest

from identity_candidates import (
    extract_line_candidates,
    extract_text_candidates,
    load_vendor_names,
    span_is_generic,
)


class IdentityCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vendor = load_vendor_names()
        self.assertIn("aws", self.vendor)
        self.assertIn("github", self.vendor)

    def test_keeps_accessing_aws(self) -> None:
        line = "When accessing AWS, use IAM roles and a named profile."
        self.assertEqual(extract_line_candidates(line, self.vendor), [])

    def test_keeps_github_docker_traefik(self) -> None:
        text = (
            "Push with GitHub Actions.\n"
            "The compose file uses Docker and Traefik labels.\n"
            "Flipper Zero stores Infrared/*.ir files.\n"
        )
        self.assertEqual(extract_text_candidates(text, self.vendor), [])

    def test_flags_fake_employer_and_person(self) -> None:
        line = "ExampleEmployerName payroll for ExampleSubjectName."
        spans = extract_line_candidates(line, self.vendor)
        joined = " ".join(spans)
        self.assertIn("ExampleEmployerName", joined)
        self.assertIn("ExampleSubjectName", joined)

    def test_documented_fakes_are_generic(self) -> None:
        self.assertTrue(span_is_generic("Alice Example", self.vendor))
        self.assertTrue(span_is_generic("Acme Corp", self.vendor))
        self.assertTrue(span_is_generic("Globex", self.vendor))

    def test_placeholder_not_a_hit(self) -> None:
        line = "Use {company}'s API and ${HOME}/.config."
        self.assertEqual(extract_line_candidates(line, self.vendor), [])

    def test_skips_exceptions_and_hook_names(self) -> None:
        text = (
            "raise TypeError\n"
            "except ValueError:\n"
            "hookEventName PreToolUse\n"
            "NEC and HVAC stay as protocol names.\n"
        )
        self.assertEqual(extract_text_candidates(text, self.vendor), [])

    def test_allcaps_acronyms_not_hits(self) -> None:
        line = "Set HOME and USER, then SMART, IPMI, OCR, and APK notes."
        self.assertEqual(extract_line_candidates(line, self.vendor), [])

    def test_english_leader_proper_seq_not_hit(self) -> None:
        self.assertEqual(
            extract_line_candidates(
                "If Cool 90 and Dry 90 share the byte.", self.vendor
            ),
            [],
        )
        self.assertEqual(
            extract_line_candidates(
                "Use Globex's API (hard-coded employer).", self.vendor
            ),
            [],
        )

    def test_markdown_headings_not_hits(self) -> None:
        text = (
            "# Writing Style Auto-Update\n"
            "## Plan Summary\n"
            "ExampleEmployerName payroll for ExampleSubjectName.\n"
        )
        spans = [
            span for _ln, span, _line in extract_text_candidates(text, self.vendor)
        ]
        self.assertNotIn("Writing Style", spans)
        self.assertNotIn("Plan Summary", spans)
        self.assertIn("ExampleEmployerName", spans)
        self.assertIn("ExampleSubjectName", spans)


if __name__ == "__main__":
    unittest.main()
