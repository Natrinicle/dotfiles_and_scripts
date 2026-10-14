#!/usr/bin/env python3
"""Write Dia 0.97 XML for flowchart diagrams (uncompressed .dia)."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

NS = "http://www.lysator.liu.se/~alla/dia/"


def _text_block(
    text: str, cx: float, cy: float, height: float, color: str, align: int = 1
) -> str:
    # Dia strings are wrapped in #...#
    body = escape(text).replace("\n", "&#xA;")
    return f"""        <dia:attribute name="text">
          <dia:composite type="text">
            <dia:attribute name="string">
              <dia:string>#{body}#</dia:string>
            </dia:attribute>
            <dia:attribute name="font">
              <dia:font family="sans" style="0" name="Helvetica"/>
            </dia:attribute>
            <dia:attribute name="height">
              <dia:real val="{height}"/>
            </dia:attribute>
            <dia:attribute name="pos">
              <dia:point val="{cx},{cy}"/>
            </dia:attribute>
            <dia:attribute name="color">
              <dia:color val="{color}"/>
            </dia:attribute>
            <dia:attribute name="alignment">
              <dia:enum val="{align}"/>
            </dia:attribute>
          </dia:composite>
        </dia:attribute>"""


def flowchart_box(
    oid: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    fill: str,
    ink: str = "#1b1f24",
    font: float = 0.55,
) -> str:
    return f"""    <dia:object type="Flowchart - Box" version="0" id="{oid}">
      <dia:attribute name="obj_pos">
        <dia:point val="{x},{y}"/>
      </dia:attribute>
      <dia:attribute name="obj_bb">
        <dia:rectangle val="{x - 0.05},{y - 0.05};{x + w + 0.05},{y + h + 0.05}"/>
      </dia:attribute>
      <dia:attribute name="elem_corner">
        <dia:point val="{x},{y}"/>
      </dia:attribute>
      <dia:attribute name="elem_width">
        <dia:real val="{w}"/>
      </dia:attribute>
      <dia:attribute name="elem_height">
        <dia:real val="{h}"/>
      </dia:attribute>
      <dia:attribute name="border_width">
        <dia:real val="0.06"/>
      </dia:attribute>
      <dia:attribute name="inner_color">
        <dia:color val="{fill}"/>
      </dia:attribute>
      <dia:attribute name="show_background">
        <dia:boolean val="true"/>
      </dia:attribute>
      <dia:attribute name="padding">
        <dia:real val="0.25"/>
      </dia:attribute>
{_text_block(text, x + w / 2, y + h / 2, font, ink)}
    </dia:object>"""


def flowchart_decision(
    oid: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    fill: str,
    ink: str = "#1b1f24",
    font: float = 0.5,
) -> str:
    return f"""    <dia:object type="Flowchart - Diamond" version="1" id="{oid}">
      <dia:attribute name="obj_pos">
        <dia:point val="{x},{y}"/>
      </dia:attribute>
      <dia:attribute name="obj_bb">
        <dia:rectangle val="{x - 0.05},{y - 0.05};{x + w + 0.05},{y + h + 0.05}"/>
      </dia:attribute>
      <dia:attribute name="elem_corner">
        <dia:point val="{x},{y}"/>
      </dia:attribute>
      <dia:attribute name="elem_width">
        <dia:real val="{w}"/>
      </dia:attribute>
      <dia:attribute name="elem_height">
        <dia:real val="{h}"/>
      </dia:attribute>
      <dia:attribute name="border_width">
        <dia:real val="0.06"/>
      </dia:attribute>
      <dia:attribute name="inner_color">
        <dia:color val="{fill}"/>
      </dia:attribute>
      <dia:attribute name="show_background">
        <dia:boolean val="true"/>
      </dia:attribute>
      <dia:attribute name="padding">
        <dia:real val="0.2"/>
      </dia:attribute>
{_text_block(text, x + w / 2, y + h / 2, font, ink)}
    </dia:object>"""


def flowchart_ellipse(
    oid: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    fill: str,
    ink: str = "#1b1f24",
    font: float = 0.5,
) -> str:
    return f"""    <dia:object type="Flowchart - Ellipse" version="1" id="{oid}">
      <dia:attribute name="obj_pos">
        <dia:point val="{x},{y}"/>
      </dia:attribute>
      <dia:attribute name="obj_bb">
        <dia:rectangle val="{x - 0.05},{y - 0.05};{x + w + 0.05},{y + h + 0.05}"/>
      </dia:attribute>
      <dia:attribute name="elem_corner">
        <dia:point val="{x},{y}"/>
      </dia:attribute>
      <dia:attribute name="elem_width">
        <dia:real val="{w}"/>
      </dia:attribute>
      <dia:attribute name="elem_height">
        <dia:real val="{h}"/>
      </dia:attribute>
      <dia:attribute name="border_width">
        <dia:real val="0.06"/>
      </dia:attribute>
      <dia:attribute name="inner_color">
        <dia:color val="{fill}"/>
      </dia:attribute>
      <dia:attribute name="show_background">
        <dia:boolean val="true"/>
      </dia:attribute>
      <dia:attribute name="padding">
        <dia:real val="0.2"/>
      </dia:attribute>
{_text_block(text, x + w / 2, y + h / 2, font, ink)}
    </dia:object>"""


# Directional connection points on flowchart Element objects:
# 0 N, 1 S, 2 E, 3 W, 4 NE, 5 NW, 6 SE, 7 SW
N, S, E, W, NE, NW, SE, SW = 0, 1, 2, 3, 4, 5, 6, 7


def line(
    oid: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: str = "#1b1f24",
    start: tuple[str, int] | None = None,
    end: tuple[str, int] | None = None,
) -> str:
    xmin, xmax = (x1, x2) if x1 <= x2 else (x2, x1)
    ymin, ymax = (y1, y2) if y1 <= y2 else (y2, y1)
    connections = ""
    if start or end:
        parts = []
        if start:
            parts.append(
                f'        <dia:connection handle="0" to="{start[0]}" connection="{start[1]}"/>'
            )
        if end:
            parts.append(
                f'        <dia:connection handle="1" to="{end[0]}" connection="{end[1]}"/>'
            )
        connections = (
            "      <dia:connections>\n"
            + "\n".join(parts)
            + "\n      </dia:connections>\n"
        )
    return f"""    <dia:object type="Standard - Line" version="0" id="{oid}">
      <dia:attribute name="obj_pos">
        <dia:point val="{x1},{y1}"/>
      </dia:attribute>
      <dia:attribute name="obj_bb">
        <dia:rectangle val="{xmin - 0.2},{ymin - 0.2};{xmax + 0.2},{ymax + 0.2}"/>
      </dia:attribute>
      <dia:attribute name="conn_endpoints">
        <dia:point val="{x1},{y1}"/>
        <dia:point val="{x2},{y2}"/>
      </dia:attribute>
      <dia:attribute name="numcp">
        <dia:int val="1"/>
      </dia:attribute>
      <dia:attribute name="line_colour">
        <dia:color val="{color}"/>
      </dia:attribute>
      <dia:attribute name="line_width">
        <dia:real val="0.07"/>
      </dia:attribute>
      <dia:attribute name="end_arrow">
        <dia:enum val="22"/>
      </dia:attribute>
      <dia:attribute name="end_arrow_length">
        <dia:real val="0.55"/>
      </dia:attribute>
      <dia:attribute name="end_arrow_width">
        <dia:real val="0.45"/>
      </dia:attribute>
{connections}    </dia:object>"""


def title(
    oid: str, x: float, y: float, text: str, color: str, height: float = 0.85
) -> str:
    return f"""    <dia:object type="Standard - Text" version="1" id="{oid}">
      <dia:attribute name="obj_pos">
        <dia:point val="{x},{y}"/>
      </dia:attribute>
      <dia:attribute name="obj_bb">
        <dia:rectangle val="{x},{y - height};{x + 18},{y + 0.2}"/>
      </dia:attribute>
{_text_block(text, x, y, height, color, align=0)}
      <dia:attribute name="valign">
        <dia:enum val="3"/>
      </dia:attribute>
    </dia:object>"""


def document(objects: list[str], paper_name: str = "Letter") -> str:
    body = "\n".join(objects)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<dia:diagram xmlns:dia="{NS}">
  <dia:diagramdata>
    <dia:attribute name="background">
      <dia:color val="#f7f4ee"/>
    </dia:attribute>
    <dia:attribute name="pagebreak">
      <dia:color val="#dddddd"/>
    </dia:attribute>
    <dia:attribute name="paper">
      <dia:composite type="paper">
        <dia:attribute name="name">
          <dia:string>#{paper_name}#</dia:string>
        </dia:attribute>
        <dia:attribute name="tmargin">
          <dia:real val="1"/>
        </dia:attribute>
        <dia:attribute name="bmargin">
          <dia:real val="1"/>
        </dia:attribute>
        <dia:attribute name="lmargin">
          <dia:real val="1"/>
        </dia:attribute>
        <dia:attribute name="rmargin">
          <dia:real val="1"/>
        </dia:attribute>
        <dia:attribute name="is_portrait">
          <dia:boolean val="false"/>
        </dia:attribute>
        <dia:attribute name="scaling">
          <dia:real val="1"/>
        </dia:attribute>
        <dia:attribute name="fitto">
          <dia:boolean val="false"/>
        </dia:attribute>
      </dia:composite>
    </dia:attribute>
    <dia:attribute name="grid">
      <dia:composite type="grid">
        <dia:attribute name="width_x">
          <dia:real val="1"/>
        </dia:attribute>
        <dia:attribute name="width_y">
          <dia:real val="1"/>
        </dia:attribute>
        <dia:attribute name="visible_x">
          <dia:int val="1"/>
        </dia:attribute>
        <dia:attribute name="visible_y">
          <dia:int val="1"/>
        </dia:attribute>
      </dia:composite>
    </dia:attribute>
  </dia:diagramdata>
  <dia:layer name="Background" visible="true" active="true">
{body}
  </dia:layer>
</dia:diagram>
"""


def write_dia(path: Path, objects: list[str]) -> None:
    path.write_text(document(objects), encoding="utf-8")
