"""Rebuild the editable HydroOpsLM coupling figure from preserved icon assets.

Run with Python 3.12+ from any directory. Export the resulting master with
draw.io Desktop; generated PNG icons remain independent raster objects.
"""

from pathlib import Path
import base64
import json
import xml.etree.ElementTree as ET

FIGURES = Path(__file__).resolve().parents[1]
ASSETS = FIGURES / "assets" / "coupling-framework"
OUTPUT = FIGURES / "hydrocnhs-coupling-framework-en.drawio"
INK = "#243746"
BLUE = "#527F9A"
BLUE_LIGHT = "#EEF5F8"
PURPLE = "#79647D"
PURPLE_LIGHT = "#F5F0F6"
TEAL = "#4F7F78"
TEAL_LIGHT = "#EDF5F2"
GRAY = "#7D8990"
GRAY_LIGHT = "#F4F6F7"


def build():
    document = ET.Element("mxfile", host="app.diagrams.net", version="26.0.4")
    diagram = ET.SubElement(document, "diagram", id="coupling-framework", name="Framework")
    model = ET.SubElement(
        diagram, "mxGraphModel", dx="1920", dy="1240", grid="1", gridSize="10",
        page="1", pageScale="1", pageWidth="1920", pageHeight="1240",
        background="#FFFFFF", math="0", shadow="0",
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    nodes, connections = [], []

    def vertex(identity, value, x, y, w, h, style, parent="1"):
        cell = ET.SubElement(root, "mxCell", id=identity, value=value, style=style,
                             vertex="1", parent=parent)
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h),
                      **{"as": "geometry"})
        return cell

    def text(identity, value, x, y, w, h, size=28, bold=False, parent="1",
             align="center", color=INK):
        return vertex(
            identity, value, x, y, w, h,
            "text;html=0;whiteSpace=nowrap;"
            f"align={align};verticalAlign=middle;fontFamily=Arial;"
            f"fontSize={size};fontColor={color};fontStyle={int(bold)};"
            "strokeColor=none;fillColor=none;spacing=0;", parent,
        )

    def frame(identity, x, y, w, h, color, fill, width=3):
        vertex(identity, "", x, y, w, h,
               f"rounded=1;arcSize=4;fillColor={fill};strokeColor={color};strokeWidth={width};")

    def card(identity, x, y, w, h, fill="#FFFFFF", stroke="#C4D2D8", width=3):
        vertex(identity, "", x, y, w, h,
               f"rounded=1;arcSize=8;fillColor={fill};strokeColor={stroke};strokeWidth={width};")
        nodes.append({"id": identity, "bounds": [x, y, w, h]})

    def icon(identity, key, x, y, size, parent):
        encoded = base64.b64encode((ASSETS / f"{key}.png").read_bytes()).decode("ascii")
        vertex(identity, "", x, y, size, size,
               f"shape=image;imageAspect=1;aspect=fixed;image=data:image/png,{encoded};", parent)

    def edge(identity, source, target, color, exit_xy, entry_xy, points=(), dashed=False,
             dotted=False, width=5):
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
            f"html=0;strokeColor={color};strokeWidth={width};endArrow=block;endFill=1;"
            f"exitX={exit_xy[0]};exitY={exit_xy[1]};exitDx=0;exitDy=0;"
            f"entryX={entry_xy[0]};entryY={entry_xy[1]};entryDx=0;entryDy=0;"
            "jumpStyle=arc;jumpSize=10;"
        )
        if dashed or dotted:
            style += "dashed=1;dashPattern=" + ("1 5;" if dotted else "8 5;")
        cell = ET.SubElement(root, "mxCell", id=identity, style=style, edge="1",
                             parent="1", source=source, target=target)
        geometry = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        if points:
            array = ET.SubElement(geometry, "Array", **{"as": "points"})
            for x, y in points:
                ET.SubElement(array, "mxPoint", x=str(x), y=str(y))
        connections.append({"id": identity, "source": source, "target": target,
                            "exit": list(exit_xy), "entry": list(entry_xy),
                            "via": list(points)})

    # Boundaries show ownership, not execution order.
    frame("framework-boundary", 20, 15, 1880, 1210, INK, "#FFFFFF", width=4)
    text("title", "HydroOpsLM", 55, 30, 850, 62, 48, True, align="left")
    text("subtitle", "HydroCNHS coupling with selectable reservoir policy",
         55, 88, 1000, 38, 25, align="left", color=GRAY)
    frame("llm-boundary", 450, 145, 1010, 365, "#B9A8BE", PURPLE_LIGHT)
    text("llm-heading", "LLM modules", 475, 160, 560, 42, 34, True, align="left")
    text("llm-status", "CHECKED · OPTIONAL POLICY", 1105, 162, 320, 34, 19, True, color=PURPLE)
    frame("hydrocnhs-boundary", 50, 820, 1820, 365, "#97B7CB", BLUE_LIGHT)
    text("core-heading", "Native HydroCNHS", 75, 838, 650, 46, 36, True, align="left")

    card("prompt", 480, 220, 220, 205, "#FFFFFF", "#BAA9BE")
    icon("prompt-icon", "knowledge", 38, 0, 145, "prompt")
    text("prompt-name", "Prompt", 5, 157, 210, 40, 31, True, "prompt")
    card("language-model", 755, 220, 235, 205, "#EEE7F0", "#BAA9BE")
    icon("language-model-icon", "decision", 45, 0, 145, "language-model")
    text("language-model-name", "Language model", 5, 157, 225, 40, 28, True, "language-model")
    card("rule-output", 1045, 245, 190, 150, "#FFFFFF", "#BAA9BE")
    vertex("rule-output-icon", "", 48, 12, 94, 62,
           "shape=document;whiteSpace=wrap;html=0;boundedLbl=1;fillColor=#E9E1EA;"
           "strokeColor=#79647D;strokeWidth=3;", "rule-output")
    text("rule-output-name", "Rule output", 5, 76, 180, 34, 27, True, "rule-output")
    text("rule-output-detail", "Requested release", 5, 112, 180, 28, 21, parent="rule-output")
    card("checker", 1285, 220, 145, 205, TEAL_LIGHT, "#8DB3AC")
    icon("checker-icon", "audit", 12, 0, 120, "checker")
    text("checker-name", "Checker", 5, 130, 135, 38, 27, True, "checker")
    text("checker-detail", "Format + values", 5, 167, 135, 27, 19, parent="checker")
    card("knowledge", 480, 448, 250, 42, GRAY_LIGHT, "#C4D2D8", width=2)
    text("knowledge-name", "Optional knowledge", 5, 4, 240, 34, 22, parent="knowledge")

    # Record-only sidecar: never a controller gate or physics acceptance step.
    card("audit", 1510, 170, 325, 320, TEAL_LIGHT, "#8DB3AC")
    icon("audit-icon", "audit", 92, 5, 140, "audit")
    text("audit-name", "Audit / trace", 5, 146, 315, 40, 31, True, "audit")
    text("audit-detail", "Prompt + reply\nProposal + check\nPhysical execution",
         5, 190, 315, 95, 23, parent="audit", color=TEAL)
    text("audit-sidecar", "RECORD ONLY", 70, 286, 185, 26, 18, True, "audit", color=TEAL)

    # User rule and checked LLM are sibling alternatives that converge once.
    text("choice-heading", "Choose one policy per reservoir", 65, 535, 555, 40, 30, True, align="left")
    card("user-rule", 75, 590, 330, 145, PURPLE_LIGHT, "#BAA9BE")
    vertex("user-rule-icon", "", 24, 30, 78, 78,
           "rounded=1;arcSize=8;html=0;fillColor=#D7C9DA;"
           "strokeColor=#79647D;strokeWidth=3;",
           "user-rule")
    text("user-rule-if", "IF", 8, 12, 62, 24, 18, True, "user-rule-icon", color="#5E4962")
    text("user-rule-then", "THEN", 8, 42, 62, 24, 16, True, "user-rule-icon", color="#5E4962")
    text("user-rule-name", "User rule policy", 118, 25, 198, 50, 29, True, "user-rule")
    text("user-rule-detail", "Requested release", 118, 76, 198, 36, 22, parent="user-rule")
    text("or-label", "OR", 475, 592, 90, 40, 28, True, color=PURPLE)

    # Added deterministic operations sit outside the native HydroCNHS boundary.
    card("operations", 660, 555, 650, 200, BLUE_LIGHT, BLUE, width=4)
    icon("operations-icon", "reservoir", 30, 15, 160, "operations")
    text("operations-badge", "ADDED", 210, 18, 120, 30, 19, True,
         "operations", align="left", color=BLUE)
    text("operations-name", "Reservoir operations", 210, 48, 405, 48, 34, True,
         "operations", align="left")
    text("operations-detail", "Deterministic state update\nImplemented release + spill",
         210, 103, 410, 72, 25, parent="operations", align="left", color=BLUE)

    card("runoff", 75, 900, 255, 245)
    icon("runoff-icon", "hydrology", 48, 0, 155, "runoff")
    text("runoff-name", "Rainfall-runoff", 5, 160, 245, 38, 27, True, "runoff")
    text("runoff-detail", "GWLF / ABCD", 5, 202, 245, 32, 25, parent="runoff")
    card("upstream", 390, 900, 265, 245)
    icon("upstream-icon", "routing", 55, 0, 155, "upstream")
    text("upstream-name", "Upstream routing", 5, 160, 255, 38, 27, True, "upstream")
    text("upstream-detail", "Lohmann", 5, 202, 255, 32, 25, parent="upstream")
    card("dam-api", 815, 900, 260, 245, "#FFFFFF", "#97B7CB", width=4)
    vertex("dam-api-icon", "", 65, 20, 130, 100,
           "shape=mxgraph.flowchart.direct_data;fillColor=#DCEAF0;"
           "strokeColor=#527F9A;strokeWidth=3;", "dam-api")
    text("dam-api-name", "Dam API", 5, 144, 250, 42, 31, True, "dam-api")
    text("dam-api-detail", "Callback host", 5, 190, 250, 34, 24,
         parent="dam-api", color=BLUE)
    card("downstream", 1240, 900, 285, 245)
    icon("downstream-icon", "routing", 65, 0, 155, "downstream")
    text("downstream-name", "Downstream routing", 5, 160, 275, 38, 26, True, "downstream")
    text("downstream-detail", "Lohmann", 5, 202, 275, 32, 25, parent="downstream")
    text("outlet-label", "Downstream\ndischarge", 1580, 938, 210, 62, 27, True)

    edge("prompt-model", "prompt", "language-model", PURPLE, (1, .5), (0, .5), width=6)
    edge("model-output", "language-model", "rule-output", PURPLE, (1, .5), (0, .5), width=6)
    edge("output-checker", "rule-output", "checker", PURPLE, (1, .5), (0, .5), width=6)
    edge("knowledge-prompt", "knowledge", "prompt", GRAY, (.5, 0), (.35, 1), dashed=True, width=4)
    edge("checked-proposal", "checker", "operations", PURPLE, (.5, 1), (1, .45),
         [(1357.5, 500), (1360, 645)], width=6)
    text("valid-label", "Valid proposal", 1380, 550, 190, 34, 23, True, color=PURPLE)
    edge("rule-proposal", "user-rule", "operations", PURPLE, (1, .5), (0, .5), width=6)

    # Inflow, state, and implemented history feed Prompt from physical operations.
    edge("operations-prompt", "operations", "prompt", TEAL, (.35, 0), (1, .72),
         [(887.5, 525), (740, 525), (740, 368)], dashed=True, width=4)
    text("state-label", "Inflow + current storage / pool\nImplemented release history",
         770, 438, 460, 58, 21, color=TEAL)

    edge("decision-trace", "checker", "audit", TEAL, (1, .35), (0, .35), dotted=True, width=4)
    edge("execution-trace", "operations", "audit", TEAL, (1, .78), (.45, 1),
         [(1590, 711), (1590, 525), (1656, 525)], dotted=True, width=4)

    # Native physical flow remains left to right through the callback host.
    edge("runoff-upstream", "runoff", "upstream", BLUE, (1, .5), (0, .5), width=7)
    edge("upstream-dam-api", "upstream", "dam-api", BLUE, (1, .5), (0, .5), width=7)
    edge("dam-api-downstream", "dam-api", "downstream", BLUE, (1, .5), (0, .5), width=7)
    vertex("outlet-anchor", "", 1790, 1020, 5, 5, "strokeColor=none;fillColor=none;")
    edge("downstream-outlet", "downstream", "outlet-anchor", BLUE, (1, .5), (0, .5), width=7)

    # The host invokes added operations and receives total outflow exactly once.
    edge("dam-callback", "dam-api", "operations", GRAY, (.34, 0), (.42, 1),
         dashed=True, width=4)
    text("callback-label", "Callback", 710, 782, 170, 32, 21, True, color=GRAY)
    edge("operations-return", "operations", "dam-api", BLUE, (.62, 1), (.66, 0), width=6)
    text("return-label", "Release + spill (once)", 1110, 775, 300, 34, 21, True, color=BLUE)

    ET.indent(document)
    OUTPUT.write_bytes(ET.tostring(document, encoding="utf-8", xml_declaration=True))
    relationship_map = {
        "scope": "HydroOpsLM concept: native HydroCNHS hydrology and Dam callback host, selectable user-rule or checked-LLM policy, and added deterministic reservoir operations.",
        "canvas": [1920, 1240], "nodes": nodes, "edges": connections,
        "responsibilities": {
            "Native HydroCNHS": "GWLF/ABCD rainfall-runoff, Lohmann routing, and the Dam API callback host. The Dam API is not a reservoir physical solver.",
            "Added reservoir operations": "Create the reservoir observation, invoke exactly one selected policy, apply the deterministic storage transition, and return implemented release plus spill once.",
            "User rule policy": "A per-reservoir policy alternative that requests a release.",
            "Checked LLM policy": "Prompt, language model, requested-release data, and strict format/value checking. A valid proposal reaches the shared deterministic operations directly.",
            "Audit / trace": "Sidecar record of prompt, reply, proposal, check, and physical execution; never a controller gate or physics acceptance step.",
        },
        "conditions": {
            "policy choice": "Each controlled reservoir uses user rule policy OR checked LLM policy.",
            "checked-proposal": "Only a format/value-valid requested release reaches physical operations.",
            "invalid proposal": "Stop before the physical transition; record available evidence; do not imply automatic fallback.",
            "operations-return": "Implemented controlled release plus spill returns to the Dam host once for downstream routing.",
            "knowledge-prompt": "Optional configured information; not a required controller stage.",
        },
        "prompt_inputs": ["reservoir inflow", "current storage / pool", "implemented release history"],
        "notes": [
            "Color encodes role, not pass status: blue physical operations, purple decisions, teal checking/records, gray optional information.",
            "Rule output is requested-release data, not executable code.",
            "No named reservoir, FE/DKP policy, or Anik case appears in the generic figure.",
            "The audit sidecar cannot advance or accept the physical workflow.",
        ],
    }
    (ASSETS / "relationship-map.json").write_text(
        json.dumps(relationship_map, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(OUTPUT)
    print(f"NATIVE_CARDS {len(nodes)} ATTACHED_EDGES {len(connections)}")


if __name__ == "__main__":
    build()
