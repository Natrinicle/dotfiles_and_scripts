#!/usr/bin/env python3
"""Tests for residual-identity-scan.py. Uses fake tokens only."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "residual-identity-scan.py"


class ResidualIdentityScanTests(unittest.TestCase):
    def _run(
        self, args: list[str], *, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_self_test(self) -> None:
        proc = self._run(["--self-test"])
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_denylist_hit_and_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            denylist = root / "denylist.yaml"
            denylist.write_text(
                "forbidden:\n  - AcmeCorpXYZ\n  - ExampleSubjectName\n",
                encoding="utf-8",
            )
            dirty = root / "SKILL.md"
            dirty.write_text(
                "See `references/example.md` for the ExampleSubjectName account claim.\n",
                encoding="utf-8",
            )
            proc = self._run(
                ["--root", str(root), "--denylist", str(denylist), str(dirty)],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("denylist", proc.stderr)
            self.assertIn("[redacted]", proc.stderr)
            self.assertNotIn("ExampleSubjectName", proc.stderr)

            dirty.write_text(
                "See `references/example.md` for a sample password-protection claim.\n",
                encoding="utf-8",
            )
            proc = self._run(
                ["--root", str(root), "--denylist", str(denylist), str(dirty)],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_allows_example_and_container_homes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            denylist = root / "denylist.yaml"
            denylist.write_text("forbidden:\n  - AcmeCorpXYZ\n", encoding="utf-8")
            sample = root / "aliases.sh"
            sample.write_text(
                "docker run --mount target=/home/worker/.config\n"
                "# docs: /home/alice/.bashrc vs ${HOME}\n",
                encoding="utf-8",
            )
            proc = self._run(
                ["--root", str(root), "--denylist", str(denylist), str(sample)],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_skips_example_denylist_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "config"
            cfg.mkdir()
            example = cfg / "identity-denylist.example.yaml"
            example.write_text(
                "forbidden:\n  - ExampleSubjectName\n",
                encoding="utf-8",
            )
            denylist = root / "denylist.yaml"
            denylist.write_text(
                "forbidden:\n  - ExampleSubjectName\n", encoding="utf-8"
            )
            proc = self._run(
                ["--root", str(root), "--denylist", str(denylist), str(example)],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
