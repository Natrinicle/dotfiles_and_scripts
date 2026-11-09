#!/usr/bin/env python3
"""Render a system-flow graph to labeled HTML, and bake a CSS-packet GIF."""

from __future__ import annotations

import argparse
import copy
import html
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

STATES = ("waiting", "running", "done", "failed", "blocked")
GLYPH = {
    "waiting": "[ ]",
    "running": "[|]",
    "done": "[√]",
    "failed": "[×]",
    "blocked": "[\\]",
}
STAGE_GLYPH = {
    "waiting": "◇",
    "running": "◆",
    "done": "√",
    "failed": "×",
    "blocked": "◇",
}
TONES = ("o", "b", "g", "p", "a", "r")
DROP_DUR_BUSY = 0.60
DROP_DUR_MED = 1.60
DROP_DUR_TRICKLE = 4.00
SLIDE_SCALE = 2.2 / 1.6
COUNT_BUSY = 6
COUNT_MED = 3
COUNT_TRICKLE = 2
VOLUME_BANDS = {
    "high": (DROP_DUR_BUSY, COUNT_BUSY),
    "busy": (DROP_DUR_BUSY, COUNT_BUSY),
    "medium": (DROP_DUR_MED, COUNT_MED),
    "med": (DROP_DUR_MED, COUNT_MED),
    "low": (DROP_DUR_TRICKLE, COUNT_TRICKLE),
    "trickle": (DROP_DUR_TRICKLE, COUNT_TRICKLE),
}

CSS = r"""
:root {
  --bg: #101218;
  --chrome: #1c1f27;
  --card: #16181f;
  --muted: #8b919c;
  --dim: #6a717c;
  --text: #e6e8ee;
  --orange: #e89562;
  --blue: #6ea0ff;
  --green: #7dffa3;
  --green-dim: #3dba72;
  --purple: #c4b5fd;
  --red: #f07178;
  --magenta: #e06090;
  --amber: #e6c07b;
  --cyan: #5ec8e8;
  --yellow: #f0d24a;
  --t: 0;
  --play: running;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  width: VAR_WIDTHpx; height: VAR_HEIGHTpx; overflow: hidden;
  background: #0b0c10;
  font-family: "FiraCode Nerd Font", "Fira Code", "DejaVu Sans Mono", ui-monospace, monospace;
  color: var(--text);
  font-size: 13px;
  line-height: 1.35;
}
.window {
  width: VAR_WIDTHpx; height: VAR_HEIGHTpx;
  background: var(--bg);
  border: 1px solid #2b303b;
  display: flex; flex-direction: column;
}
.titlebar {
  height: 36px;
  background: var(--chrome);
  display: flex; align-items: center;
  padding: 0 14px;
  border-bottom: 1px solid #2b303b;
  gap: 12px;
  flex-shrink: 0;
}
.dots { display: flex; gap: 7px; }
.dots i { width: 12px; height: 12px; border-radius: 50%; display: block; }
.dots .r { background: #ff5f57; }
.dots .y { background: #febc2e; }
.dots .g { background: #28c840; }
.titlebar .path {
  flex: 1; text-align: center;
  color: var(--muted); font-size: 12px;
}
.header {
  display: flex; align-items: baseline; gap: 10px;
  padding: 10px 18px 4px;
  flex-shrink: 0;
  letter-spacing: 0.01em;
}
.header .host { font-weight: 700; }
.header .sep { color: var(--dim); }
.header .sys { color: var(--muted); }
.header .elapsed { margin-left: auto; color: var(--text); font-weight: 700; }
.stage-list { padding: 2px 18px 8px; flex-shrink: 0; }
.stage {
  display: flex; gap: 10px; align-items: baseline;
  color: var(--muted); font-size: 13px;
}
.stage .dia { width: 14px; color: var(--cyan); }
.stage.status-running .dia, .stage.status-running .lab { color: var(--yellow); font-weight: 700; }
.stage.status-done .dia, .stage.status-done .lab { color: var(--green); }
.stage.status-failed .dia, .stage.status-failed .lab { color: var(--magenta); }
.stage .meta { color: var(--dim); }
.body {
  flex: 1;
  display: grid;
  grid-template-columns: VAR_RAIL 1fr;
  gap: 12px;
  padding: 0 18px 8px;
  min-height: 0;
}
.rail {
  border: 1px solid #6d5bbd;
  border-radius: 6px;
  background: linear-gradient(180deg, #1a1726 0%, #14151c 40%);
  padding: 12px 10px;
  color: var(--purple);
  display: flex; flex-direction: column; gap: 6px;
  min-height: 0;
}
.rail h2 { font-size: 12px; letter-spacing: 0.08em; text-align: center; }
.gate {
  display: flex; align-items: flex-start; gap: 8px;
  font-size: 12px; color: #d6ccff;
  padding: 5px 6px; border-radius: 4px;
}
.gate span { white-space: nowrap; }
.gate .dia {
  width: 8px; height: 8px; transform: rotate(45deg);
  border: 1.5px solid var(--purple); margin-top: 4px; flex-shrink: 0;
}
.gate.active { background: #3b2f66; color: #fff; }
.gate.active .dia { background: var(--purple); box-shadow: 0 0 8px var(--purple); }
.main {
  display: flex; flex-direction: column; min-height: 0; min-width: 0; gap: 10px;
}
.tree {
  flex: 0 0 auto;
  min-height: 0;
  overflow: hidden;
}
.unit {
  display: grid;
  grid-template-columns: minmax(240px, 1.5fr) 88px 1fr 64px;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  padding: 1px 0;
}
.unit .idcell { display: flex; align-items: center; min-width: 0; }
.unit .glyph { color: var(--dim); margin-right: 6px; flex-shrink: 0; }
.unit .name { color: var(--text); }
.unit .kind { color: var(--dim); }
.unit .desc { color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.unit .run { color: var(--yellow); text-align: right; }
.unit.state-running .glyph, .unit.state-running .name { color: var(--yellow); }
.unit.state-done .glyph, .unit.state-done .name { color: var(--green); }
.unit.state-failed .glyph, .unit.state-failed .name { color: var(--magenta); font-weight: 700; }
.unit.state-blocked .glyph, .unit.state-blocked .name { color: #a05060; }
.unit.state-waiting .name { color: var(--text); }
.unit.kind-target .name { color: var(--cyan); font-weight: 700; }
.unit.kind-target.state-running .name { color: var(--yellow); }
.unit.kind-target.state-done .name { color: var(--green); }
.cols {
  display: grid;
  grid-template-columns: minmax(240px, 1.5fr) 88px 1fr 64px;
  gap: 8px;
  color: var(--dim); font-size: 11px; padding: 0 0 4px;
}
.packet-stage {
  display: flex; align-items: stretch; gap: 0;
  flex: 0 0 auto;
  min-height: 110px;
}
.packet-stage.vertical { flex-direction: column; flex: 1; }
.packet-stage.horizontal {
  flex-direction: row;
  align-items: center;
  flex: 1 1 auto;
  min-height: 180px;
}
.pcard {
  border: 1.5px solid #2b303b;
  background: var(--card);
  border-radius: 6px;
  padding: 12px 14px;
  min-width: 150px;
  min-height: 96px;
  position: relative;
}
.pcard h4 { font-size: 14px; }
.pcard .model { color: var(--muted); font-size: 11px; margin: 2px 0 6px; }
.pcard.role-lead { border-color: var(--orange); }
.pcard.role-lead h4 { color: var(--orange); }
.pcard.role-swarm { border-color: var(--blue); }
.pcard.role-swarm h4 { color: var(--blue); }
.pcard.role-local { border-color: var(--green); }
.pcard.role-local h4 { color: var(--green); }
.pcard.role-advisor { border-color: var(--purple); }
.pcard.role-advisor h4 { color: var(--purple); }
.pcard.state-failed { border-color: var(--magenta); }
.pcard.state-failed h4 { color: var(--magenta); }
.pcard .elabel {
  position: absolute; top: -10px; left: 10px;
  background: var(--bg); padding: 0 5px;
  font-size: 10px; color: var(--dim);
}
.vline, .hline { position: relative; background: #2b303b; }
.vline { width: 2px; flex: 1 1 28px; min-height: 18px; margin: 0 auto; }
.hline { height: 2px; flex: 1 1 36px; min-width: 28px; margin: 18px 0; }
.pkt {
  position: absolute;
  width: 8px; height: 8px; border-radius: 50%;
  z-index: 5; pointer-events: none;
  animation-play-state: var(--play);
}
.pkt.o { background: var(--orange); box-shadow: 0 0 8px var(--orange); }
.pkt.b { background: var(--blue); box-shadow: 0 0 8px var(--blue); }
.pkt.g { background: var(--green); box-shadow: 0 0 8px var(--green); }
.pkt.p { background: var(--purple); box-shadow: 0 0 8px var(--purple); }
.pkt.a { background: var(--amber); box-shadow: 0 0 8px var(--amber); }
.pkt.r { background: var(--magenta); box-shadow: 0 0 8px var(--magenta); }
.pkt.drop {
  left: 50%; margin-left: -4px;
  --dur: 1.6s; --d: 0s;
  animation: fall var(--dur) linear infinite;
  animation-delay: calc(var(--d) - var(--dur) * var(--t));
}
.pkt.slide {
  top: -3px;
  --dur: 2.2s; --d: 0s;
  animation: slide var(--dur) linear infinite;
  animation-delay: calc(var(--d) - var(--dur) * var(--t));
}
@keyframes fall {
  0% { top: 0; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: calc(100% - 8px); opacity: 0; }
}
@keyframes slide {
  0% { left: 0; opacity: 0; }
  8% { opacity: 1; }
  92% { opacity: 1; }
  100% { left: calc(100% - 8px); opacity: 0; }
}
.failures {
  margin: 0 18px 6px;
  border-top: 1px solid #5a3040;
  padding-top: 8px;
  flex-shrink: 0;
  color: var(--magenta);
}
.failures h3 { font-size: 13px; margin-bottom: 4px; }
.failures .reason { color: var(--text); }
.failures pre {
  color: var(--muted); font-size: 12px;
  font-family: inherit; white-space: pre-wrap;
}
.timeline {
  margin: 0 18px 6px;
  border-top: 1px solid #2b303b;
  padding-top: 8px;
  flex-shrink: 0;
}
.timeline h3 { font-size: 12px; color: var(--dim); margin-bottom: 4px; }
.trow {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 8px;
  align-items: center;
  margin: 2px 0;
  font-size: 12px;
}
.trow .tl { color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ttrack { position: relative; height: 10px; background: #1a1d24; }
.tbar {
  position: absolute; top: 0; height: 100%;
  background: var(--green-dim);
}
.tbar.state-running { background: var(--yellow); }
.tbar.state-waiting { background: repeating-linear-gradient(90deg, #3a3f4a 0 4px, transparent 4px 8px); }
.tbar.state-failed { background: var(--magenta); }
.taxis { display: flex; justify-content: space-between; color: var(--dim); font-size: 11px; margin-bottom: 4px; }
.logwrap {
  margin: 0 18px 6px;
  border: 1px solid #2b303b;
  background: #0c0e14;
  padding: 8px 12px 8px;
  height: 92px;
  flex-shrink: 0;
  position: relative;
}
.loghead {
  position: absolute; top: -9px; left: 10px;
  background: var(--bg); padding: 0 6px;
  font-size: 11px; color: var(--dim);
}
.log { font-size: 12px; color: var(--muted); overflow: hidden; padding-top: 4px; }
.log .row { display: grid; grid-template-columns: 64px 88px 1fr; gap: 10px; padding: 1px 0; white-space: nowrap; }
.tag.o { color: var(--orange); }
.tag.b { color: var(--blue); }
.tag.g { color: var(--green); }
.tag.p { color: var(--purple); }
.tag.a { color: var(--amber); }
.tag.r { color: var(--magenta); }
.footer {
  margin: 0 18px 6px;
  font-size: 13px;
  flex-shrink: 0;
  display: flex; gap: 16px;
}
.footer .done { color: var(--green); }
.footer .running { color: var(--yellow); }
.footer .waiting { color: var(--muted); }
.footer .failed { color: var(--magenta); }
.cli {
  margin: 0 18px 10px;
  font-size: 12.5px;
  flex-shrink: 0;
}
.cli .prompt { color: var(--muted); }
.cli .cmd { color: var(--green); }
.cursor {
  display: inline-block; width: 8px; height: 14px; background: var(--green);
  vertical-align: text-bottom; margin-left: 2px;
  animation: blink 1s steps(1) infinite;
  animation-play-state: var(--play);
}
@keyframes blink { 50% { opacity: 0; } }
.hidden { display: none; }
""".strip()

LIVE_SCRIPT = """
<script>
(function () {
  var start = performance.now();
  var dur = 8000;
  function tick(now) {
    var t = ((now - start) % dur) / dur;
    document.documentElement.style.setProperty("--t", t.toFixed(4));
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})();
</script>
"""


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _state(node: dict[str, Any]) -> str:
    state = str(node.get("state") or "waiting")
    return state if state in STATES else "waiting"


def _tone(value: Any, default: str = "b") -> str:
    tone = str(value or default)
    return tone if tone in TONES else default


def apply_keyframes(graph: dict[str, Any], t: float) -> dict[str, Any]:
    """Return a copy of graph with every keyframe at or before t merged in order."""
    out = copy.deepcopy(graph)
    frames = sorted(out.get("keyframes") or [], key=lambda k: float(k.get("t") or 0))
    for kf in frames:
        if float(kf.get("t") or 0) > t + 1e-9:
            break
        by_id = {n["id"]: n for n in out.get("nodes") or []}
        for nid, patch in (kf.get("nodes") or {}).items():
            if nid in by_id and isinstance(patch, dict):
                by_id[nid].update(patch)
        if "footer" in kf:
            out["footer"] = dict(kf["footer"])
        if "failures" in kf:
            out["failures"] = list(kf["failures"])
        if "log" in kf:
            out["log"] = list(kf["log"])
        if "timeline" in kf:
            out["timeline"] = list(kf["timeline"])
        if "cli" in kf:
            out["cli"] = kf["cli"]
        if "gates" in kf:
            active = {str(x) for x in kf["gates"]}
            for gate in out.get("gates") or []:
                gate["active"] = str(gate.get("id")) in active
        if "stages" in kf:
            stage_by = {s["id"]: s for s in out.get("stages") or []}
            for patch in kf["stages"]:
                sid = patch.get("id")
                if sid in stage_by:
                    stage_by[sid].update(patch)
    return out


def _children(nodes: list[dict[str, Any]]) -> dict[str | None, list[dict[str, Any]]]:
    tree: dict[str | None, list[dict[str, Any]]] = {}
    for node in nodes:
        parent = node.get("parent")
        tree.setdefault(parent, []).append(node)
    return tree


def _render_units(nodes: list[dict[str, Any]]) -> str:
    tree = _children(nodes)
    known = {n["id"] for n in nodes}
    lines: list[str] = [
        (
            '<div class="cols"><span>Unit</span><span>Kind</span>'
            "<span>Description</span><span>Running</span></div>"
        )
    ]

    def walk(parent: str | None, depth: int) -> None:
        for node in tree.get(parent, []):
            state = _state(node)
            kind = str(node.get("kind") or "service")
            run = node.get("running_s")
            run_s = (
                f"{float(run):.1f}s" if run is not None and state == "running" else ""
            )
            pad = 4 + depth * 18
            lines.append(
                f'<div class="unit state-{_esc(state)} kind-{_esc(kind)}" '
                f'id="n-{_esc(node["id"])}">'
                f'<span class="idcell" style="padding-left:{pad}px">'
                f'<span class="glyph">{_esc(GLYPH[state])}</span>'
                f'<span class="name">{_esc(node.get("label") or node["id"])}</span></span>'
                f'<span class="kind">{_esc(kind)}</span>'
                f'<span class="desc">{_esc(node.get("description") or "")}</span>'
                f'<span class="run">{_esc(run_s)}</span></div>'
            )
            walk(str(node["id"]), depth + 1)

    roots = tree.get(None, [])
    dangling_parents = [p for p in tree if p is not None and p not in known]
    walk(None, 0)
    for parent in dangling_parents:
        walk(parent, 0)
    if not roots and not dangling_parents:
        for node in nodes:
            walk(node["id"], 0)  # pragma: no cover
            break
    return "\n".join(lines)


def _scale_kind(drop_dur: float, count: int, kind: str) -> tuple[float, int]:
    if kind == "slide":
        return (round(drop_dur * SLIDE_SCALE, 2), count)
    return (drop_dur, count)


def _motion_from_rate(rate: float, kind: str) -> tuple[float, int]:
    rate = max(0.0, min(1.0, float(rate)))
    drop = DROP_DUR_TRICKLE - rate * (DROP_DUR_TRICKLE - DROP_DUR_BUSY)
    count = COUNT_TRICKLE + round(rate * (COUNT_BUSY - COUNT_TRICKLE))
    return _scale_kind(round(drop, 2), int(count), kind)


def _bps_to_rate(bps: float) -> float:
    if bps <= 0:
        return 0.0
    return max(0.0, min(1.0, (math.log10(bps) - 2.0) / 6.0))


def volume_to_motion(source: Any, *, kind: str = "drop") -> tuple[float, int]:
    """Map expected data volume to (duration_s, packet_count).

    Busy pipes get a shorter CSS `--dur` and more dots. Trickle pipes get a
    longer `--dur` and fewer dots. `source` may be a band name, a 0..1 rate,
    a bps number, or an edge dict (`volume`, `rate`, `bps`, `bytes`).
    """
    volume: Any = source
    bps: Any = None
    nbytes: Any = None
    rate: Any = None
    if isinstance(source, dict):
        volume = source.get("volume")
        bps = source.get("bps") or source.get("bytes_per_sec")
        nbytes = source.get("bytes")
        rate = source.get("rate")
    if isinstance(volume, str):
        band = VOLUME_BANDS.get(volume.strip().lower())
        if band is not None:
            return _scale_kind(band[0], band[1], kind)
    if isinstance(volume, (int, float)) and not isinstance(volume, bool):
        if 0.0 <= float(volume) <= 1.0:
            return _motion_from_rate(float(volume), kind)
        bps = volume
    if rate is not None:
        try:
            return _motion_from_rate(float(rate), kind)
        except (TypeError, ValueError):
            pass
    if bps is not None:
        try:
            return _motion_from_rate(_bps_to_rate(float(bps)), kind)
        except (TypeError, ValueError):
            pass
    if nbytes is not None:
        try:
            n = float(nbytes)
            if n <= 0:
                r = 0.0
            else:
                r = max(0.0, min(1.0, (math.log10(n) - 3.0) / 6.0))
            return _motion_from_rate(r, kind)
        except (TypeError, ValueError):
            pass
    return _scale_kind(DROP_DUR_MED, COUNT_MED, kind)


def _packets(kind: str, tone: str, count: int = 3, duration_s: float = 1.60) -> str:
    bits = []
    gap = duration_s / max(count, 1)
    dur = f"{duration_s:.2f}s"
    for i in range(count):
        delay = f"{i * gap:.2f}s"
        bits.append(
            f'<i class="pkt {kind} {_esc(tone)}" style="--d:{delay};--dur:{dur}"></i>'
        )
    return "".join(bits)


def _card(node: dict[str, Any], edge_label: str = "") -> str:
    role = str(node.get("role") or "swarm")
    state = _state(node)
    label = _esc(node.get("label") or node["id"])
    kind = _esc(node.get("kind") or "service")
    desc = _esc(node.get("description") or "")
    elabel = f'<span class="elabel">{_esc(edge_label)}</span>' if edge_label else ""
    return (
        f'<div class="pcard role-{_esc(role)} state-{state}" id="p-{_esc(node["id"])}">'
        f"{elabel}<h4>{label}</h4>"
        f'<div class="model">{kind} · {state}</div>'
        f'<div class="desc">{desc}</div></div>'
    )


def _ordered_talk_chain(
    graph: dict[str, Any],
) -> list[tuple[dict[str, Any], str, str, dict[str, Any] | None]]:
    """Return (node, inbound_label, tone, inbound_edge) in talks-to order."""
    nodes = {n["id"]: n for n in graph.get("nodes") or []}
    talks = [
        e
        for e in graph.get("edges") or []
        if e.get("kind") == "talks" or e.get("packets")
    ]
    inbound: dict[str, list[dict[str, Any]]] = {}
    outbound: dict[str, list[dict[str, Any]]] = {}
    for edge in talks:
        src, dst = edge.get("from"), edge.get("to")
        if src in nodes and dst in nodes:
            inbound.setdefault(str(dst), []).append(edge)
            outbound.setdefault(str(src), []).append(edge)
    starts = [
        n
        for n in graph.get("nodes") or []
        if n["id"] not in inbound and n["id"] in nodes
    ]
    if not starts:
        starts = list(graph.get("nodes") or [])[:1]
    seen: set[str] = set()
    chain: list[tuple[dict[str, Any], str, str, dict[str, Any] | None]] = []

    def walk(
        node: dict[str, Any],
        label: str,
        tone: str,
        edge: dict[str, Any] | None,
    ) -> None:
        nid = str(node["id"])
        if nid in seen:
            return
        seen.add(nid)
        chain.append((node, label, tone, edge))
        for nxt in outbound.get(nid, []):
            dst = nodes.get(str(nxt.get("to")))
            if dst is not None:
                walk(dst, str(nxt.get("label") or ""), _tone(nxt.get("tone")), nxt)

    for start in starts:
        walk(start, "", "o", None)
    for node in graph.get("nodes") or []:
        if node["id"] not in seen:
            chain.append((node, "", "b", None))
    return chain


def _render_packets(graph: dict[str, Any], orientation: str) -> str:
    chain = _ordered_talk_chain(graph)
    if not chain:
        return ""
    pkt_kind = "drop" if orientation == "vertical" else "slide"
    wrap = "vline" if orientation == "vertical" else "hline"
    parts = [f'<div class="packet-stage {orientation}">']
    for i, (node, label, tone, edge) in enumerate(chain):
        if i:
            dur, count = volume_to_motion(edge, kind=pkt_kind)
            parts.append(
                f'<div class="{wrap}">{_packets(pkt_kind, tone, count, dur)}</div>'
            )
        parts.append(_card(node, label))
    parts.append("</div>")
    return "\n".join(parts)


def _render_stages(stages: list[dict[str, Any]]) -> str:
    if not stages:
        return ""
    rows = ['<div class="stage-list">']
    for stage in stages:
        status = str(stage.get("status") or "waiting")
        if status not in STAGE_GLYPH:
            status = "waiting"
        elapsed = stage.get("elapsed_s")
        units = stage.get("units")
        failed = stage.get("failed") or 0
        meta_bits = []
        if status == "done" and elapsed is not None:
            meta_bits.append(f"done in {float(elapsed):.1f}s")
        elif elapsed is not None:
            meta_bits.append(f"{float(elapsed):.1f}s")
        if units is not None:
            meta_bits.append(f"{int(units)} units")
        if failed:
            meta_bits.append(f"{int(failed)} failed")
        meta = " · ".join(meta_bits)
        rows.append(
            f'<div class="stage status-{_esc(status)}">'
            f'<span class="dia">{STAGE_GLYPH[status]}</span>'
            f'<span class="lab">{_esc(stage.get("label") or stage.get("id"))}</span>'
            f'<span class="meta">{_esc(meta)}</span></div>'
        )
    rows.append("</div>")
    return "\n".join(rows)


def _render_failures(failures: list[dict[str, Any]]) -> str:
    if not failures:
        return ""
    rows = ['<div class="failures"><h3>Failures</h3>']
    for item in failures:
        lines = "\n".join(_esc(x) for x in item.get("lines") or [])
        rows.append(
            f"<div><strong>× {_esc(item.get('unit') or '')}</strong> "
            f'<span class="reason">{_esc(item.get("reason") or "")}</span>'
            f"<pre>{lines}</pre></div>"
        )
    rows.append("</div>")
    return "\n".join(rows)


def _render_timeline(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    end = max((float(i.get("end_s") or 0) for i in items), default=1.0) or 1.0
    ticks = 4

    def _tick(value: float) -> str:
        return f"{value:.0f}s" if abs(value - round(value)) < 0.05 else f"{value:.1f}s"

    axis = "".join(f"<span>{_tick(end * i / ticks)}</span>" for i in range(ticks + 1))
    rows = [f'<div class="timeline"><h3>Timeline</h3><div class="taxis">{axis}</div>']
    for item in items:
        state = str(item.get("state") or "done")
        start = float(item.get("start_s") or 0)
        stop = float(item.get("end_s") or start)
        left = 100.0 * start / end
        width = max(1.5, 100.0 * (stop - start) / end)
        rows.append(
            f'<div class="trow"><span class="tl">{_esc(item.get("label") or item.get("id"))}</span>'
            f'<div class="ttrack"><i class="tbar state-{_esc(state)}" '
            f'style="left:{left:.2f}%;width:{width:.2f}%"></i></div></div>'
        )
    rows.append("</div>")
    return "\n".join(rows)


def _render_log(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    bits = [
        '<div class="logwrap"><div class="loghead">session log</div><div class="log">'
    ]
    for row in rows[-6:]:
        bits.append(
            f'<div class="row"><span>{_esc(row.get("t") or "")}</span>'
            f'<span class="tag {_esc(_tone(row.get("tone")))}">{_esc(row.get("tag") or "")}</span>'
            f"<span>{_esc(row.get('text') or '')}</span></div>"
        )
    bits.append("</div></div>")
    return "\n".join(bits)


def _render_gates(gates: list[dict[str, Any]]) -> str:
    if not gates:
        return ""
    bits = ['<aside class="rail"><h2>gates</h2>']
    for gate in gates:
        active = " active" if gate.get("active") else ""
        bits.append(
            f'<div class="gate{active}" id="g-{_esc(gate.get("id"))}">'
            f'<i class="dia"></i><span>{_esc(gate.get("label") or gate.get("id"))}</span></div>'
        )
    bits.append("</aside>")
    return "\n".join(bits)


def _footer(footer: dict[str, Any] | None) -> str:
    data = footer or {}
    done = int(data.get("done") or 0)
    running = int(data.get("running") or 0)
    waiting = int(data.get("waiting") or 0)
    failed = int(data.get("failed") or 0)
    return (
        '<div class="footer">'
        f'<span class="done">✓ {done} done</span>'
        f'<span class="running">{running} running</span>'
        f'<span class="waiting">{waiting} waiting</span>'
        f'<span class="failed">× {failed} failed</span>'
        "</div>"
    )


def _elapsed(graph: dict[str, Any]) -> str:
    stages = graph.get("stages") or []
    if not stages:
        return ""
    total = 0.0
    for stage in stages:
        total += float(stage.get("elapsed_s") or 0)
    return f"{total:.1f}s"


def render_html(graph: dict[str, Any], t: float = 0.0, paused: bool = False) -> str:
    """Build a self-contained labeled dashboard. Frozen frames set paused=True."""
    snap = apply_keyframes(graph, t)
    mode = str(snap.get("mode") or "tree")
    chrome = str(snap.get("chrome") or "tui")
    width = int(snap.get("width") or 1200)
    height = int(snap.get("height") or 1500)
    play = "paused" if paused else "running"
    gates = snap.get("gates") or []
    rail_col = "200px" if gates else "0px"
    css = (
        CSS.replace("VAR_WIDTH", str(width))
        .replace("VAR_HEIGHT", str(height))
        .replace("VAR_RAIL", rail_col)
    )
    title = snap.get("title") or "System flow"
    header = snap.get("header") or {}
    show_tree = mode in {"tree", "combo"}
    show_packets = mode in {"packet", "combo"}
    orientation = "vertical" if mode == "packet" else "horizontal"

    titlebar = ""
    if chrome == "window":
        titlebar = (
            '<div class="titlebar"><span class="dots"><i class="r"></i>'
            '<i class="y"></i><i class="g"></i></span>'
            f'<span class="path">{_esc(title)}</span></div>'
        )

    tree_html = (
        f'<div class="tree">{_render_units(snap.get("nodes") or [])}</div>'
        if show_tree
        else ""
    )
    packet_html = _render_packets(snap, orientation) if show_packets else ""
    body = (
        '<div class="body">'
        f"{_render_gates(gates)}"
        f'<div class="main">{tree_html}{packet_html}</div>'
        "</div>"
    )
    script = "" if paused else LIVE_SCRIPT
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>{_esc(title)}</title><style>\n"
        f"{css}\n:root {{ --t: {t:.4f}; --play: {play}; }}\n"
        "</style></head><body>\n"
        f'<div class="window">{titlebar}'
        '<div class="header">'
        f'<span class="host">{_esc(header.get("host") or title)}</span>'
        '<span class="sep">·</span>'
        f'<span class="sys">{_esc(header.get("system") or "")}</span>'
        '<span class="sep">·</span>'
        f'<span class="sys">{_esc(header.get("kernel") or "")}</span>'
        f'<span class="elapsed">{_esc(_elapsed(snap))}</span></div>'
        f"{_render_stages(snap.get('stages') or [])}"
        f"{body}"
        f"{_render_failures(snap.get('failures') or [])}"
        f"{_render_timeline(snap.get('timeline') or [])}"
        f"{_render_log(snap.get('log') or [])}"
        f"{_footer(snap.get('footer'))}"
        f'<div class="cli"><span class="prompt">$</span> '
        f'<span class="cmd">{_esc(snap.get("cli") or "render-flow")}</span>'
        '<i class="cursor"></i></div>'
        f"</div>\n{script}</body></html>\n"
    )


def write_html(
    graph: dict[str, Any],
    path: Path,
    t: float = 0.0,
    paused: bool = False,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(graph, t=t, paused=paused), encoding="utf-8")
    return path


def load_graph(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _chromium() -> str:
    for name in ("chromium", "chromium-browser", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    raise FileNotFoundError("chromium not on PATH")


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise FileNotFoundError("ffmpeg not on PATH")
    return found


def bake_gif(
    graph: dict[str, Any],
    out: Path,
    *,
    frames: int = 16,
    fps: int = 8,
    scale: float = 1.0,
    mp4: bool = False,
) -> dict[str, Path]:
    """Screenshot frozen HTML frames and assemble a looping GIF."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    width = int(graph.get("width") or 1200)
    height = int(graph.get("height") or 1500)
    chrome = _chromium()
    ffmpeg = _ffmpeg()
    artifacts: dict[str, Path] = {"gif": out}
    with tempfile.TemporaryDirectory(prefix="system-flow-viz-") as raw:
        tmp = Path(raw)
        frame_dir = tmp / "frames"
        frame_dir.mkdir()
        for i in range(frames):
            t = i / frames
            html_path = tmp / f"f{i:02d}.html"
            png_path = frame_dir / f"f{i:02d}.png"
            write_html(graph, html_path, t=t, paused=True)
            subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--no-sandbox",
                    "--disable-gpu",
                    f"--window-size={width},{height}",
                    f"--screenshot={png_path}",
                    html_path.resolve().as_uri(),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=60,
            )
            if not png_path.is_file():
                raise RuntimeError(f"chromium did not write {png_path}")
        palette = tmp / "palette.png"
        vf_in = str(frame_dir / "f%02d.png")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(fps),
                "-i",
                vf_in,
                "-vf",
                "palettegen",
                "-update",
                "1",
                "-frames:v",
                "1",
                str(palette),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        scale_f = f"scale={int(width * scale)}:{int(height * scale)}:flags=neighbor,"
        if scale == 1.0:
            scale_f = ""
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(fps),
                "-i",
                vf_in,
                "-i",
                str(palette),
                "-lavfi",
                f"{scale_f}paletteuse=dither=bayer",
                "-gifflags",
                "-offsetting",
                str(out),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        still = out.with_suffix(".png")
        mid = frame_dir / f"f{frames // 2:02d}.png"
        shutil.copyfile(mid, still)
        artifacts["png"] = still
        if mp4:
            mp4_path = out.with_suffix(".mp4")
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-framerate",
                    str(fps),
                    "-i",
                    vf_in,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(mp4_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=60,
            )
            artifacts["mp4"] = mp4_path
    return artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    html_p = sub.add_parser("html", help="Write a self-contained HTML dashboard")
    html_p.add_argument("graph", type=Path)
    html_p.add_argument("-o", "--output", type=Path, required=True)
    html_p.add_argument("--t", type=float, default=0.0)
    html_p.add_argument("--paused", action="store_true")

    bake_p = sub.add_parser("bake", help="Bake a looping GIF from keyframes")
    bake_p.add_argument("graph", type=Path)
    bake_p.add_argument("-o", "--output", type=Path, required=True)
    bake_p.add_argument("--frames", type=int, default=16)
    bake_p.add_argument("--fps", type=int, default=8)
    bake_p.add_argument("--scale", type=float, default=0.5)
    bake_p.add_argument("--mp4", action="store_true")

    sub.add_parser("self-test", help="Run the unit tests next to this file")

    args = parser.parse_args(argv)
    if args.cmd == "self-test":
        import unittest

        test_path = Path(__file__).with_name("test_render_flow.py")
        loader = unittest.defaultTestLoader
        suite = loader.discover(str(test_path.parent), pattern=test_path.name)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    graph = load_graph(args.graph)
    if args.cmd == "html":
        write_html(graph, args.output, t=args.t, paused=args.paused)
        print(args.output)
        return 0
    artifacts = bake_gif(
        graph,
        args.output,
        frames=args.frames,
        fps=args.fps,
        scale=args.scale,
        mp4=args.mp4,
    )
    for kind, path in artifacts.items():
        print(f"{kind}\t{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
