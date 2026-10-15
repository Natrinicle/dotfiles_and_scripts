#!/usr/bin/env python3
"""Tests for Meld-style side-by-side diffs (not GitHub unified output)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import meld_style_diff as msd


class AlignTests(unittest.TestCase):
    def test_equal_files_are_side_by_side_with_line_numbers(self) -> None:
        rows = msd.align_rows(["a", "b"], ["a", "b"])
        self.assertEqual([row.kind for row in rows], ["equal", "equal"])
        self.assertEqual(rows[0].left_no, 1)
        self.assertEqual(rows[0].right_no, 1)
        self.assertEqual(rows[1].left, "b")
        self.assertEqual(rows[1].right, "b")

    def test_insert_leaves_blank_on_left(self) -> None:
        rows = msd.align_rows(["keep"], ["keep", "new"])
        self.assertEqual([row.kind for row in rows], ["equal", "insert"])
        self.assertIsNone(rows[1].left_no)
        self.assertEqual(rows[1].left, "")
        self.assertEqual(rows[1].right_no, 2)
        self.assertEqual(rows[1].right, "new")

    def test_delete_leaves_blank_on_right(self) -> None:
        rows = msd.align_rows(["keep", "gone"], ["keep"])
        self.assertEqual([row.kind for row in rows], ["equal", "delete"])
        self.assertEqual(rows[1].left_no, 2)
        self.assertIsNone(rows[1].right_no)
        self.assertEqual(rows[1].right, "")

    def test_replace_same_length_is_blue_chunk_not_delete_plus_insert(self) -> None:
        rows = msd.align_rows(["return 1"], ["return 2"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].kind, "replace")
        self.assertEqual(rows[0].left, "return 1")
        self.assertEqual(rows[0].right, "return 2")

    def test_replace_unequal_length_stays_one_replace_chunk(self) -> None:
        rows = msd.align_rows(["one", "two"], ["ONE"])
        kinds = [row.kind for row in rows]
        self.assertTrue(kinds)
        self.assertTrue(all(kind == "replace" for kind in kinds))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].left, "one")
        self.assertEqual(rows[0].right, "ONE")
        self.assertEqual(rows[1].left, "two")
        self.assertEqual(rows[1].right, "")
        self.assertIsNone(rows[1].right_no)


class IntraLineTests(unittest.TestCase):
    def test_intra_line_marks_changed_token_only(self) -> None:
        left, right = msd.intra_spans("foo BAR baz", "foo qux baz")
        left_kinds = [span.kind for span in left if span.text]
        right_kinds = [span.kind for span in right if span.text]
        self.assertIn("delete", left_kinds)
        self.assertIn("insert", right_kinds)
        self.assertEqual("".join(span.text for span in left), "foo BAR baz")
        self.assertEqual("".join(span.text for span in right), "foo qux baz")
        deleted = "".join(span.text for span in left if span.kind == "delete")
        inserted = "".join(span.text for span in right if span.kind == "insert")
        self.assertEqual(deleted, "BAR")
        self.assertEqual(inserted, "qux")


class RenderTests(unittest.TestCase):
    def _compare(self) -> msd.FileCompare:
        rows = msd.align_rows(
            ["def foo():", "    return 1", "def bar():"],
            ["def foo():", "    return 2", "def bar():"],
        )
        return msd.FileCompare(
            left_label="old.py",
            right_label="new.py",
            rows=rows,
        )

    def test_html_uses_meld_chunk_classes_not_github_prefixes(self) -> None:
        html = msd.render_html([self._compare()])
        self.assertIn("chunk replace", html)
        self.assertIn("old.py", html)
        self.assertIn("new.py", html)
        self.assertIn("map-tick", html)
        self.assertIn("link chunk", html)
        self.assertNotIn("@@ -", html)
        self.assertNotRegex(html, r"(?m)^[+-]{3} ")
        self.assertIn("return", html)
        self.assertIn('inline delete">1', html)
        self.assertIn('inline insert">2', html)

    def test_text_is_two_column_not_unified(self) -> None:
        text = msd.render_text([self._compare()], width=88)
        self.assertIn("old.py", text)
        self.assertIn("new.py", text)
        self.assertIn("|", text)
        self.assertNotIn("@@", text)
        self.assertNotRegex(text, r"(?m)^--- ")
        self.assertNotRegex(text, r"(?m)^\+\+\+ ")
        self.assertIn("return 1", text)
        self.assertIn("return 2", text)

    def test_ansi_colors_insert_delete_replace(self) -> None:
        rows = msd.align_rows(["keep", "AAAAAA"], ["keep", "BBBBBB", "CCCCCC"])
        compare = msd.FileCompare("a", "b", tuple(rows))
        ansi = msd.render_ansi([compare], width=80)
        self.assertIn("\x1b[", ansi)
        self.assertIn("AAAAAA", ansi)
        self.assertIn("BBBBBB", ansi)
        self.assertIn("CCCCCC", ansi)


class UnifiedInputTests(unittest.TestCase):
    SAMPLE = """\
--- a/sample.py
+++ b/sample.py
@@ -1,3 +1,3 @@
 def foo():
-    return 1
+    return 2
 def bar():
"""

    def test_from_unified_rebuilds_both_sides(self) -> None:
        compares = msd.parse_unified_diff(self.SAMPLE)
        self.assertEqual(len(compares), 1)
        self.assertEqual(compares[0].left_label, "a/sample.py")
        self.assertEqual(compares[0].right_label, "b/sample.py")
        left = [row.left for row in compares[0].rows if row.left_no is not None]
        right = [row.right for row in compares[0].rows if row.right_no is not None]
        self.assertEqual(left, ["def foo():", "    return 1", "def bar():"])
        self.assertEqual(right, ["def foo():", "    return 2", "def bar():"])
        kinds = {row.kind for row in compares[0].rows}
        self.assertIn("replace", kinds)
        self.assertNotIn("@@", msd.render_text(compares, width=88))


class PathCompareTests(unittest.TestCase):
    def test_compare_paths_reads_files(self) -> None:
        tmp = Path("/tmp/meld-style-diff-test")
        tmp.mkdir(parents=True, exist_ok=True)
        left = tmp / "left.txt"
        right = tmp / "right.txt"
        left.write_text("alpha\n", encoding="utf-8")
        right.write_text("alpha\nbeta\n", encoding="utf-8")
        compare = msd.compare_paths(left, right, dyff="never")
        self.assertEqual(compare.left_label, str(left))
        self.assertEqual([row.kind for row in compare.rows], ["equal", "insert"])
        self.assertEqual(compare.rows[1].right, "beta")


class StructuredDetectTests(unittest.TestCase):
    def test_labels_by_extension(self) -> None:
        self.assertTrue(msd.is_structured_label("values.yaml"))
        self.assertTrue(msd.is_structured_label("chart.yml"))
        self.assertTrue(msd.is_structured_label("a/config.json"))
        self.assertTrue(msd.is_structured_label("HEAD:deploy/app.jsonc"))
        self.assertFalse(msd.is_structured_label("main.py"))
        self.assertFalse(msd.is_structured_label("README.md"))
        self.assertFalse(msd.is_structured_label("Cargo.toml"))

    def test_text_sniff(self) -> None:
        self.assertTrue(msd.is_structured_text('{"replicas": 1}\n'))
        self.assertTrue(msd.is_structured_text("[1, 2]\n"))
        self.assertTrue(
            msd.is_structured_text("---\napiVersion: v1\nkind: ConfigMap\n")
        )
        self.assertTrue(msd.is_structured_text("foo: bar\n"))
        self.assertFalse(msd.is_structured_text("def foo():\n    return 1\n"))
        self.assertFalse(msd.is_structured_text(""))
        self.assertFalse(msd.is_structured_text("# just a comment\n"))
        self.assertFalse(
            msd.is_structured_text("[See the docs](https://example.com)\n")
        )


class DyffTests(unittest.TestCase):
    def _fake_dyff(self, tmp: Path) -> Path:
        script = tmp / "dyff"
        script.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "Path(sys.argv[0]).with_suffix('.args').write_text(\n"
            "    ' '.join(sys.argv[1:]), encoding='utf-8'\n"
            ")\n"
            "print('spec.replicas')\n"
            "print('  ± value change')\n"
            "print('    - 1')\n"
            "print('    + 3')\n"
            "sys.exit(0)\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return script

    def test_dyff_between_texts_invokes_human_not_github(self) -> None:
        tmp = Path("/tmp/meld-style-diff-dyff-test")
        tmp.mkdir(parents=True, exist_ok=True)
        fake = self._fake_dyff(tmp)
        report = msd.dyff_between_texts(
            "replicas: 1\n",
            "replicas: 3\n",
            "old.yaml",
            "new.yaml",
            dyff_bin=str(fake),
        )
        self.assertIsNotNone(report)
        assert report is not None
        self.assertIn("spec.replicas", report)
        args = fake.with_suffix(".args").read_text(encoding="utf-8")
        self.assertIn("between", args)
        self.assertIn("--omit-header", args)
        self.assertIn("--color", args)
        self.assertNotIn("github", args)
        self.assertNotIn("gitlab", args)
        self.assertNotIn("-o ", args)

    def test_missing_binary_returns_none(self) -> None:
        self.assertIsNone(
            msd.dyff_between_texts(
                "a: 1\n",
                "a: 2\n",
                "a.yaml",
                "b.yaml",
                dyff_bin="/nonexistent/dyff",
            )
        )

    def test_compare_texts_attaches_dyff_for_yaml(self) -> None:
        tmp = Path("/tmp/meld-style-diff-dyff-test")
        tmp.mkdir(parents=True, exist_ok=True)
        fake = self._fake_dyff(tmp)
        compare = msd.compare_texts(
            "foo: 1\n",
            "foo: 2\n",
            "left.yaml",
            "right.yaml",
            dyff_bin=str(fake),
        )
        self.assertIsNotNone(compare.dyff_report)
        assert compare.dyff_report is not None
        self.assertIn("spec.replicas", compare.dyff_report)

    def test_compare_texts_skips_dyff_for_python(self) -> None:
        tmp = Path("/tmp/meld-style-diff-dyff-test")
        tmp.mkdir(parents=True, exist_ok=True)
        fake = self._fake_dyff(tmp)
        args_file = fake.with_suffix(".args")
        if args_file.exists():
            args_file.unlink()
        compare = msd.compare_texts(
            "def foo():\n    return 1\n",
            "def foo():\n    return 2\n",
            "old.py",
            "new.py",
            dyff_bin=str(fake),
        )
        self.assertIsNone(compare.dyff_report)
        self.assertFalse(args_file.exists())

    def test_never_mode_skips_even_yaml(self) -> None:
        tmp = Path("/tmp/meld-style-diff-dyff-test")
        tmp.mkdir(parents=True, exist_ok=True)
        fake = self._fake_dyff(tmp)
        args_file = fake.with_suffix(".args")
        if args_file.exists():
            args_file.unlink()
        compare = msd.compare_texts(
            "foo: 1\n",
            "foo: 2\n",
            "left.yaml",
            "right.yaml",
            dyff="never",
            dyff_bin=str(fake),
        )
        self.assertIsNone(compare.dyff_report)
        self.assertFalse(args_file.exists())

    def test_auto_runs_when_text_is_yaml_without_extension(self) -> None:
        tmp = Path("/tmp/meld-style-diff-dyff-test")
        tmp.mkdir(parents=True, exist_ok=True)
        fake = self._fake_dyff(tmp)
        compare = msd.compare_texts(
            "foo: 1\n",
            "foo: 2\n",
            "left",
            "right",
            dyff_bin=str(fake),
        )
        self.assertIsNotNone(compare.dyff_report)

    def test_html_includes_dyff_section(self) -> None:
        compare = msd.FileCompare(
            left_label="old.yaml",
            right_label="new.yaml",
            rows=tuple(msd.align_rows(["foo: 1"], ["foo: 2"])),
            dyff_report="spec.replicas\n  ± value change\n",
        )
        html = msd.render_html([compare])
        self.assertIn('class="dyff"', html)
        self.assertIn("spec.replicas", html)
        self.assertIn("Structured diff (dyff)", html)
        self.assertIn("chunk replace", html)

    def test_empty_dyff_report_omits_section(self) -> None:
        compare = msd.FileCompare(
            left_label="old.yaml",
            right_label="new.yaml",
            rows=tuple(msd.align_rows(["foo: 1"], ["foo: 1"])),
            dyff_report="",
        )
        html = msd.render_html([compare])
        self.assertNotIn('class="dyff"', html)

    def test_text_puts_dyff_above_panes(self) -> None:
        compare = msd.FileCompare(
            left_label="old.yaml",
            right_label="new.yaml",
            rows=tuple(msd.align_rows(["foo: 1"], ["foo: 2"])),
            dyff_report="spec.replicas\n  ± 1 -> 3\n",
        )
        text = msd.render_text([compare], width=88)
        dyff_at = text.find("spec.replicas")
        pane_at = text.find("old.yaml")
        self.assertGreaterEqual(dyff_at, 0)
        self.assertGreater(pane_at, dyff_at)

    def test_from_unified_yaml_attaches_dyff(self) -> None:
        tmp = Path("/tmp/meld-style-diff-dyff-test")
        tmp.mkdir(parents=True, exist_ok=True)
        fake = self._fake_dyff(tmp)
        sample = """\
--- a/values.yaml
+++ b/values.yaml
@@ -1,2 +1,2 @@
 replicaCount: 1
-image: old
+image: new
"""
        compares = msd.parse_unified_diff(sample, dyff_bin=str(fake))
        self.assertEqual(len(compares), 1)
        self.assertIsNotNone(compares[0].dyff_report)


class BinarySkipTests(unittest.TestCase):
    def test_nul_bytes_are_binary(self) -> None:
        self.assertTrue(msd.looks_binary(b"\x00\x01\x02"))
        self.assertFalse(msd.looks_binary(b"plain text\n"))

    def test_compare_paths_skips_binary(self) -> None:
        tmp = Path("/tmp/meld-style-diff-test")
        tmp.mkdir(parents=True, exist_ok=True)
        left = tmp / "left.bin"
        right = tmp / "right.bin"
        left.write_bytes(b"\x7fELF\x00")
        right.write_bytes(b"\x7fELF\x00more")
        compare = msd.compare_paths(left, right)
        self.assertEqual(compare.skipped, "binary")
        self.assertEqual(compare.rows, ())
        html = msd.render_html([compare])
        self.assertIn("Skipped binary", html)
        self.assertNotIn('class="dyff"', html)


if __name__ == "__main__":
    unittest.main()
