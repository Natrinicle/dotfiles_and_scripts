#!/usr/bin/env python3
"""CLI tests for identity-subagent-scan.py. Fake tokens only."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "identity-subagent-scan.py"


def _load_cli():
    scripts = str(SCRIPT.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("identity_subagent_scan", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class IdentitySubagentScanTests(unittest.TestCase):
    def _run(
        self, args: list[str], *, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("CI", None)
        env.pop("GITHUB_ACTIONS", None)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def test_fixture_keeps_aws_flags_employer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "When accessing AWS, use IAM roles.\n"
                "Push images with Docker and GitHub Actions.\n",
                encoding="utf-8",
            )
            (root / "notes.md").write_text(
                "ExampleEmployerName payroll for ExampleSubjectName.\n",
                encoding="utf-8",
            )
            proc = self._run(["--root", str(root)], cwd=root)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertNotIn("AWS", proc.stdout)
            self.assertNotIn("GitHub", proc.stdout)
            self.assertIn("ExampleEmployerName", proc.stdout)
            self.assertIn("ExampleSubjectName", proc.stdout)
            self.assertIn("notes.md", proc.stdout)

    def test_skips_python_identifiers_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "When accessing AWS, use IAM roles.\n", encoding="utf-8"
            )
            (root / "hook.py").write_text(
                "class ParsedHit:\n    raise TypeError\n", encoding="utf-8"
            )
            proc = self._run(["--root", str(root)], cwd=root)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertNotIn("ParsedHit", proc.stdout)
            self.assertNotIn("hook.py", proc.stdout)

    def test_print_prompt(self) -> None:
        proc = self._run(["--print-prompt"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("identity-subagent-prompt.md", proc.stdout)

    def test_ci_skips_ollama(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.md").write_text(
                "ExampleEmployerName payroll for ExampleSubjectName.\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["CI"] = "true"
            env.pop("GITHUB_ACTIONS", None)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--ollama"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("skip --ollama in CI", proc.stderr)
            self.assertIn("ExampleEmployerName", proc.stdout)
            self.assertNotIn('"hits"', proc.stdout)

    def test_extract_json_from_fence(self) -> None:
        mod = _load_cli()
        raw = 'Sure.\n```json\n{"hits": [], "kept_vendor": []}\n```\n'
        out = mod.extract_json_object(raw)
        self.assertEqual(json.loads(out)["hits"], [])
        self.assertEqual(json.loads(out)["kept_vendor"], [])


if __name__ == "__main__":
    unittest.main()
