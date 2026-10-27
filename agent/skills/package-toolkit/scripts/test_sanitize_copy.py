#!/usr/bin/env python3
"""Tests for sanitize-copy.py denylist replace. Uses fake tokens only."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SCRIPT = SCRIPTS / "sanitize-copy.py"
sys.path.insert(0, str(SCRIPTS))
from identity_denylist import (
    compile_token_re,
    replace_denylist_tokens,
)


class IdentityDenylistHelperTests(unittest.TestCase):
    def test_longest_token_first(self) -> None:
        token_re = compile_token_re(["ExampleSubjectName", "ExampleSubjectNameSuffix"])
        self.assertIsNotNone(token_re)
        out, n = replace_denylist_tokens(
            "See ExampleSubjectNameSuffix in the notes.\n", token_re
        )
        self.assertEqual(n, 1)
        self.assertEqual(out, "See {subject} in the notes.\n")
        self.assertNotIn("ExampleSubjectName", out)
        self.assertNotIn("Suffix", out)


class SanitizeCopyTests(unittest.TestCase):
    def _run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("CI", None)
        env.pop("GITHUB_ACTIONS", None)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def test_replaces_denylist_token_with_subject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            denylist = root / "denylist.yaml"
            denylist.write_text(
                "forbidden:\n  - ExampleSubjectName\n",
                encoding="utf-8",
            )
            src = root / "notes.md"
            src.write_text(
                "The ExampleSubjectName account is a sample.\n",
                encoding="utf-8",
            )
            dest = root / "out"
            proc = self._run(
                [
                    "--dest",
                    str(dest),
                    "--denylist",
                    str(denylist),
                    "--no-host-denylist",
                    str(src),
                ],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            written = dest / "notes.md"
            body = written.read_text(encoding="utf-8")
            self.assertIn("{subject}", body)
            self.assertNotIn("ExampleSubjectName", body)

    def test_fails_without_denylist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "notes.md"
            src.write_text("no identity here\n", encoding="utf-8")
            dest = root / "out"
            proc = self._run(
                ["--dest", str(dest), "--no-host-denylist", str(src)],
                cwd=root,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("no denylist", proc.stderr)
            self.assertFalse((dest / "notes.md").is_file())

    def test_allow_missing_denylist_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "notes.md"
            src.write_text("portable text\n", encoding="utf-8")
            dest = root / "out"
            proc = self._run(
                [
                    "--dest",
                    str(dest),
                    "--no-host-denylist",
                    "--allow-missing-denylist",
                    str(src),
                ],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(
                (dest / "notes.md").read_text(encoding="utf-8"),
                "portable text\n",
            )

    def test_skips_example_denylist_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            denylist = root / "denylist.yaml"
            denylist.write_text(
                "forbidden:\n  - ExampleSubjectName\n",
                encoding="utf-8",
            )
            src = root / "identity-denylist.example.yaml"
            original = "forbidden:\n  - ExampleSubjectName\n"
            src.write_text(original, encoding="utf-8")
            dest = root / "out"
            proc = self._run(
                [
                    "--dest",
                    str(dest),
                    "--denylist",
                    str(denylist),
                    "--no-host-denylist",
                    str(src),
                ],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(
                (dest / "identity-denylist.example.yaml").read_text(encoding="utf-8"),
                original,
            )


if __name__ == "__main__":
    unittest.main()
