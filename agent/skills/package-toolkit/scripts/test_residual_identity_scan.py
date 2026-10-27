#!/usr/bin/env python3
"""Tests for residual-identity-scan.py. Uses fake tokens only."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "residual-identity-scan.py"


class ResidualIdentityScanTests(unittest.TestCase):
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
                [
                    "--root",
                    str(root),
                    "--denylist",
                    str(denylist),
                    "--no-host-denylist",
                    str(dirty),
                ],
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
                [
                    "--root",
                    str(root),
                    "--denylist",
                    str(denylist),
                    "--no-host-denylist",
                    str(dirty),
                ],
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
                "HOME=/home/node\n"
                "# docs: /home/alice/.bashrc vs ${HOME}\n",
                encoding="utf-8",
            )
            proc = self._run(
                [
                    "--root",
                    str(root),
                    "--denylist",
                    str(denylist),
                    "--no-host-denylist",
                    str(sample),
                ],
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
                [
                    "--root",
                    str(root),
                    "--denylist",
                    str(denylist),
                    "--no-host-denylist",
                    str(example),
                ],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_require_denylist_fails_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "README.md"
            sample.write_text("portable pack notes\n", encoding="utf-8")
            proc = self._run(
                [
                    "--root",
                    str(root),
                    "--no-host-denylist",
                    str(sample),
                ],
                cwd=root,
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("no denylist", proc.stderr)

    def test_ci_allows_missing_denylist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "README.md"
            sample.write_text("portable pack notes\n", encoding="utf-8")
            proc = self._run(
                ["--root", str(root), "--no-host-denylist", str(sample)],
                cwd=root,
                extra_env={"CI": "true"},
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_whole_tree_finds_unlisted_leftover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            denylist = base / "denylist.yaml"
            denylist.write_text(
                "forbidden:\n  - ExampleSubjectName\n",
                encoding="utf-8",
            )
            pack = base / "pack"
            hidden = pack / "examples"
            hidden.mkdir(parents=True)
            (pack / "README.md").write_text("clean\n", encoding="utf-8")
            leftover = hidden / "notes.md"
            leftover.write_text("leftover ExampleSubjectName token\n", encoding="utf-8")
            proc = self._run(
                [
                    "--root",
                    str(pack),
                    "--denylist",
                    str(denylist),
                    "--no-host-denylist",
                ],
                cwd=pack,
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("denylist", proc.stderr)
            self.assertIn("notes.md", proc.stderr)

    def test_gitignored_leftover_skipped_on_whole_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            denylist = base / "denylist.yaml"
            denylist.write_text(
                "forbidden:\n  - ExampleSubjectName\n",
                encoding="utf-8",
            )
            pack = base / "pack"
            pack.mkdir()
            git_env = os.environ.copy()
            git_env["GIT_CONFIG_GLOBAL"] = "/dev/null"
            git_env["GIT_CONFIG_NOSYSTEM"] = "1"
            init = subprocess.run(
                ["git", "init", "-q"],
                cwd=pack,
                capture_output=True,
                text=True,
                check=False,
                env=git_env,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            (pack / ".gitignore").write_text("scratch-leftover.md\n", encoding="utf-8")
            (pack / "README.md").write_text("clean\n", encoding="utf-8")
            (pack / "scratch-leftover.md").write_text(
                "leftover ExampleSubjectName token\n", encoding="utf-8"
            )
            proc = self._run(
                [
                    "--root",
                    str(pack),
                    "--denylist",
                    str(denylist),
                    "--no-host-denylist",
                ],
                cwd=pack,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
