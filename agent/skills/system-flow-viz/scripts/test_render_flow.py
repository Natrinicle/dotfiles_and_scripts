#!/usr/bin/env python3
"""Application-scenario tests for system-flow-viz (graph JSON → labeled HTML)."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RENDER = HERE / "render_flow.py"
EXAMPLE = HERE.parent / "examples" / "compose-stack.json"


def load_mod():
    spec = importlib.util.spec_from_file_location("render_flow", RENDER)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(RENDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAMPLE = {
    "title": "Sample stack",
    "mode": "tree",
    "chrome": "tui",
    "header": {
        "host": "sample",
        "system": "compose stack",
        "kernel": "Linux",
    },
    "stages": [
        {
            "id": "boot",
            "label": "Boot",
            "status": "running",
            "elapsed_s": 1.2,
            "units": 3,
            "failed": 0,
        }
    ],
    "nodes": [
        {
            "id": "target",
            "label": "app.target",
            "kind": "target",
            "state": "running",
            "parent": None,
            "description": "Default target",
        },
        {
            "id": "proxy",
            "label": "proxy",
            "kind": "edge",
            "state": "running",
            "parent": "target",
            "description": "TLS terminator",
            "running_s": 1.2,
            "role": "lead",
        },
        {
            "id": "app",
            "label": "app",
            "kind": "service",
            "state": "waiting",
            "parent": "target",
            "description": "API",
        },
        {
            "id": "db",
            "label": "db",
            "kind": "service",
            "state": "waiting",
            "parent": "app",
            "description": "Store",
        },
    ],
    "edges": [
        {
            "from": "proxy",
            "to": "app",
            "kind": "talks",
            "label": "HTTPS",
            "packets": True,
            "tone": "o",
        },
        {
            "from": "app",
            "to": "db",
            "kind": "talks",
            "label": "SQL",
            "packets": True,
            "tone": "b",
        },
    ],
    "failures": [],
    "timeline": [
        {
            "id": "proxy",
            "label": "proxy",
            "start_s": 0.0,
            "end_s": 1.2,
            "state": "running",
        }
    ],
    "footer": {"done": 0, "running": 2, "waiting": 2, "failed": 0},
    "log": [{"t": "00:00:01", "tag": "proxy", "tone": "o", "text": "listen :443"}],
    "gates": [{"id": "g1", "label": "before start", "active": True}],
    "cli": "render-flow --graph sample.json",
    "keyframes": [
        {
            "t": 0.0,
            "nodes": {"app": {"state": "waiting"}, "db": {"state": "waiting"}},
        },
        {
            "t": 0.5,
            "nodes": {"app": {"state": "running"}},
            "footer": {"done": 0, "running": 3, "waiting": 1, "failed": 0},
        },
        {
            "t": 0.9,
            "nodes": {
                "app": {"state": "done"},
                "db": {"state": "failed"},
            },
            "footer": {"done": 1, "running": 1, "waiting": 0, "failed": 1},
            "failures": [
                {
                    "unit": "db",
                    "reason": "exited with status 1",
                    "lines": ["FATAL: role app does not exist"],
                }
            ],
        },
    ],
}


class RenderFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_mod()

    def test_tree_contains_node_labels(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.0, paused=True)
        for label in ("app.target", "proxy", "app", "db", "TLS terminator"):
            self.assertIn(label, html)

    def test_footer_census(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.0, paused=True)
        self.assertIn("0 done", html)
        self.assertIn("2 running", html)
        self.assertIn("2 waiting", html)
        self.assertIn("0 failed", html)

    def test_state_classes_and_glyphs(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.0, paused=True)
        self.assertIn('id="n-proxy"', html)
        self.assertIn("state-running", html)
        self.assertIn("state-waiting", html)
        self.assertIn("[|]", html)
        self.assertIn("[ ]", html)

    def test_failure_panel_absent_when_empty(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.0, paused=True)
        self.assertNotIn('class="failures"', html)
        self.assertNotIn("FATAL: role app does not exist", html)

    def test_failure_panel_from_keyframe(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.9, paused=True)
        self.assertIn('class="failures"', html)
        self.assertIn("exited with status 1", html)
        self.assertIn("FATAL: role app does not exist", html)
        self.assertIn("1 failed", html)
        self.assertIn("state-failed", html)
        self.assertIn("[×]", html)

    def test_timeline_present(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.0, paused=True)
        self.assertIn('class="timeline"', html)
        self.assertIn('class="tbar', html)

    def test_packet_mode_wires_and_packets(self) -> None:
        graph = dict(SAMPLE)
        graph["mode"] = "packet"
        html = self.mod.render_html(graph, t=0.2, paused=True)
        self.assertIn('class="pkt', html)
        self.assertIn("HTTPS", html)
        self.assertIn("SQL", html)
        self.assertIn("--play: paused", html)
        self.assertIn("animation-delay: calc(var(--d) - var(--dur) * var(--t))", html)

    def test_css_play_and_t_vars(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.25, paused=True)
        self.assertIn("--t:", html)
        self.assertIn("--play:", html)
        self.assertIn("animation-play-state: var(--play)", html)

    def test_frozen_html_pauses_and_strips_script(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.4, paused=True)
        self.assertIn("--play: paused", html)
        self.assertNotIn("<script", html.lower())

    def test_live_html_may_include_script(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.0, paused=False)
        self.assertIn("--play: running", html)
        self.assertIn("<script", html.lower())

    def test_html_escapes_labels(self) -> None:
        graph = dict(SAMPLE)
        graph["nodes"] = [
            {
                "id": "x",
                "label": "<script>alert(1)</script>",
                "kind": "service",
                "state": "waiting",
                "parent": None,
                "description": "a & b",
            }
        ]
        html = self.mod.render_html(graph, t=0.0, paused=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("a &amp; b", html)

    def test_gate_active_is_a_class_not_a_comment(self) -> None:
        html = self.mod.render_html(SAMPLE, t=0.0, paused=True)
        self.assertIn('class="gate active"', html)
        self.assertNotIn('class="gate<!--', html)

    def test_combo_mode_has_tree_and_packets(self) -> None:
        graph = dict(SAMPLE)
        graph["mode"] = "combo"
        html = self.mod.render_html(graph, t=0.2, paused=True)
        self.assertIn('class="tree"', html)
        self.assertIn('class="pkt', html)
        self.assertIn('class="stage-list"', html)

    def test_example_json_renders(self) -> None:
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        html = self.mod.render_html(data, t=0.4, paused=True)
        self.assertIn("proxy", html)
        self.assertIn("app", html)
        self.assertIn("db", html)
        self.assertGreater(len(html), 2000)

    def test_write_html_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "flow.html"
            self.mod.write_html(SAMPLE, out, t=0.0, paused=True)
            text = out.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("<!DOCTYPE html>"))
            self.assertIn("Sample stack", text)

    def test_volume_high_is_faster_and_denser_than_low(self) -> None:
        high_d, high_n = self.mod.volume_to_motion("high", kind="drop")
        med_d, med_n = self.mod.volume_to_motion("medium", kind="drop")
        low_d, low_n = self.mod.volume_to_motion("low", kind="drop")
        self.assertEqual((high_d, high_n), (0.60, 6))
        self.assertEqual((med_d, med_n), (1.60, 3))
        self.assertEqual((low_d, low_n), (4.00, 2))
        self.assertLess(high_d, med_d)
        self.assertLess(med_d, low_d)
        self.assertGreater(high_n, med_n)
        self.assertGreater(med_n, low_n)

    def test_volume_slide_keeps_drop_ratio(self) -> None:
        drop_d, drop_n = self.mod.volume_to_motion("medium", kind="drop")
        slide_d, slide_n = self.mod.volume_to_motion("medium", kind="slide")
        self.assertEqual((drop_d, drop_n), (1.60, 3))
        self.assertEqual((slide_d, slide_n), (2.20, 3))

    def test_volume_missing_defaults_to_medium(self) -> None:
        self.assertEqual(self.mod.volume_to_motion(None, kind="drop"), (1.60, 3))
        self.assertEqual(self.mod.volume_to_motion({}, kind="drop"), (1.60, 3))

    def test_volume_from_edge_dict_and_bps(self) -> None:
        high_edge = {"volume": "high"}
        low_bps = {"bps": 800}
        busy_bps = {"bps": 8_000_000}
        self.assertEqual(self.mod.volume_to_motion(high_edge, kind="drop"), (0.60, 6))
        low_d, low_n = self.mod.volume_to_motion(low_bps, kind="drop")
        high_d, high_n = self.mod.volume_to_motion(busy_bps, kind="drop")
        self.assertGreater(low_d, high_d)
        self.assertGreaterEqual(high_n, low_n)

    def test_volume_rate_zero_to_one(self) -> None:
        idle_d, idle_n = self.mod.volume_to_motion(0.0, kind="drop")
        full_d, full_n = self.mod.volume_to_motion(1.0, kind="drop")
        self.assertEqual((idle_d, idle_n), (4.00, 2))
        self.assertEqual((full_d, full_n), (0.60, 6))

    def test_html_inline_dur_follows_edge_volume(self) -> None:
        graph = {
            "title": "Volume wires",
            "mode": "packet",
            "chrome": "tui",
            "header": {"host": "sample", "system": "data flow", "kernel": "Linux"},
            "nodes": [
                {
                    "id": "proxy",
                    "label": "proxy",
                    "kind": "edge",
                    "state": "running",
                    "role": "lead",
                },
                {
                    "id": "app",
                    "label": "app",
                    "kind": "service",
                    "state": "running",
                    "role": "swarm",
                },
                {
                    "id": "db",
                    "label": "db",
                    "kind": "service",
                    "state": "waiting",
                },
            ],
            "edges": [
                {
                    "from": "proxy",
                    "to": "app",
                    "kind": "talks",
                    "label": "HTTPS",
                    "packets": True,
                    "tone": "o",
                    "volume": "high",
                },
                {
                    "from": "app",
                    "to": "db",
                    "kind": "talks",
                    "label": "SQL",
                    "packets": True,
                    "tone": "b",
                    "volume": "low",
                },
            ],
        }
        html = self.mod.render_html(graph, t=0.2, paused=True)
        self.assertIn("--dur:0.60s", html)
        self.assertIn("--dur:4.00s", html)
        self.assertEqual(html.count("--dur:0.60s"), 6)
        self.assertEqual(html.count("--dur:4.00s"), 2)


class SkillDocsTests(unittest.TestCase):
    SKILL = HERE.parent / "SKILL.md"

    def test_description_triggers_data_flow_paths(self) -> None:
        text = self.SKILL.read_text(encoding="utf-8")
        head = text.split("---", 2)[1].lower()
        self.assertIn("data flow", head)
        self.assertIn("data flow path", head)
        self.assertIn("traffic between systems", head)

    def test_docs_preview_assets_exist(self) -> None:
        docs = HERE.parent / "docs"
        html = docs / "compose-stack.html"
        gif = docs / "compose-stack.gif"
        self.assertTrue(html.is_file(), f"missing {html}")
        self.assertTrue(gif.is_file(), f"missing {gif}")
        self.assertGreater(html.stat().st_size, 2000)
        self.assertGreater(gif.stat().st_size, 10_000)
        self.assertLess(gif.stat().st_size, 500_000)


if __name__ == "__main__":
    if not RENDER.is_file():
        print(f"FAIL: missing {RENDER}", file=sys.stderr)
        sys.exit(1)
    unittest.main()
