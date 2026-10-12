"""Rebuild the generic, editable coupling figure from preserved icon assets.

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
PLUM = "#79647D"
GREEN = "#597D69"
GRAY = "#7D8990"


def build():
    document = ET.Element("mxfile", host="app.diagrams.net", version="26.0.4")
    diagram = ET.SubElement(document, "diagram", id="coupling-framework", name="Framework")
    model = ET.SubElement(diagram, "mxGraphModel", dx="1800", dy="1160", grid="1",
                          gridSize="10", page="1", pageScale="1", pageWidth="1800",
                          pageHeight="1320", background="#FFFFFF", math="0", shadow="0")
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

    def text(identity, value, x, y, w, h, size=28, bold=False, parent="1", align="center", color=INK):
        return vertex(identity, value, x, y, w, h,
                      f"text;html=0;whiteSpace=nowrap;align={align};verticalAlign=middle;"
                      f"fontFamily=Arial;fontSize={size};fontColor={color};fontStyle={int(bold)};"
                      "strokeColor=none;fillColor=none;spacing=0;", parent)

    def frame(identity, x, y, w, h, color, fill):
        vertex(identity, "", x, y, w, h,
                f"rounded=1;arcSize=4;fillColor={fill};strokeColor={color};strokeWidth=3;")

    def card(identity, x, y, w, h, fill="#FFFFFF", stroke="#C4D2D8"):
        vertex(identity, "", x, y, w, h,
                f"rounded=1;arcSize=8;fillColor={fill};strokeColor={stroke};strokeWidth=3;")
        nodes.append({"id": identity, "bounds": [x, y, w, h]})

    def icon(identity, key, x, y, size, parent):
        encoded = base64.b64encode((ASSETS / f"{key}.png").read_bytes()).decode("ascii")
        vertex(identity, "", x, y, size, size,
               f"shape=image;imageAspect=1;aspect=fixed;image=data:image/png,{encoded};", parent)

    def edge(identity, source, target, color, exit_xy, entry_xy, points=(), dashed=False,
              dotted=False, width=5):
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
                 f"html=0;strokeColor={color};strokeWidth={width};endArrow=block;endFill=1;"
                 f"exitX={exit_xy[0]};exitY={exit_xy[1]};exitDx=0;exitDy=0;"
                 f"entryX={entry_xy[0]};entryY={entry_xy[1]};entryDx=0;entryDy=0;"
                 "jumpStyle=arc;jumpSize=10;")
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

    # The outer boundary is the framework; inner boundaries identify provenance.
    frame("framework-boundary", 20, 15, 1760, 1290, INK, "#FFFFFF")
    text("title", "HydroOpsLM", 55, 35, 1650, 65, 48, True, align="left")
    frame("operations-boundary", 50, 135, 1700, 550, "#B9A8BE", "#FAF8FB")
    text("operations-heading", "Added LLM modules", 75, 155, 900, 50, 38, True, align="left")
    frame("hydrocnhs-boundary", 50, 830, 1700, 435, "#97B7CB", "#F4F8FA")
    text("core-heading", "Native HydroCNHS", 75, 850, 700, 48, 38, True, align="left")

    card("prompt", 85, 230, 270, 270)
    icon("prompt-icon", "knowledge", 30, 0, 210, "prompt")
    text("prompt-name", "Prompt", 5, 214, 260, 44, 36, True, "prompt")
    card("language-model", 465, 230, 300, 270, "#F1EBF2", "#BAA9BE")
    icon("language-model-icon", "decision", 45, 0, 210, "language-model")
    text("language-model-name", "Language model", 5, 214, 290, 44, 33, True, "language-model")
    card("rule-output", 875, 290, 250, 150)
    text("rule-output-name", "Rule output", 5, 15, 240, 50, 35, True, "rule-output")
    text("rule-output-detail", "Requested release", 5, 82, 240, 40, 27, parent="rule-output")
    card("checker", 1235, 230, 270, 270)
    icon("checker-icon", "audit", 35, 0, 200, "checker")
    text("checker-name", "Checker", 5, 190, 260, 40, 36, True, "checker")
    text("checker-detail", "Format / values", 5, 234, 260, 30, 27, parent="checker")

    card("knowledge", 85, 550, 420, 70)
    text("knowledge-name", "Optional knowledge", 5, 10, 410, 50, 31, parent="knowledge")
    card("audit", 680, 550, 560, 115, "#EFF5F0", "#ADC3B2")
    text("audit-name", "Audit / trace", 5, 5, 550, 45, 34, True, "audit")
    text("audit-detail", "Prompt · output · checks\nExecuted release · strategy audit", 5, 50, 550, 60, 27, parent="audit")
    card("stop", 1360, 550, 350, 115, "#F8EEE8", "#B58A70")
    text("stop-name", "Stop + record error", 5, 10, 340, 50, 31, True, "stop")
    text("stop-detail", "No release applied", 5, 65, 340, 38, 27, parent="stop")

    card("runoff", 75, 920, 275, 325)
    icon("runoff-icon", "hydrology", 32, 0, 210, "runoff")
    text("runoff-name", "Rainfall–runoff", 5, 215, 265, 45, 32, True, "runoff")
    text("runoff-detail", "GWLF / ABCD", 5, 270, 265, 40, 32, parent="runoff")
    card("upstream", 420, 920, 300, 325)
    icon("upstream-icon", "routing", 45, 0, 210, "upstream")
    text("upstream-name", "Upstream routing", 5, 215, 290, 45, 30, True, "upstream")
    text("upstream-detail", "Lohmann", 5, 270, 290, 40, 32, parent="upstream")
    card("reservoir", 810, 915, 320, 335, "#FAF3E7", "#B59864")
    text("reservoir-provenance", "Added operations", 5, 5, 310, 36, 32, True, "reservoir")
    icon("reservoir-icon", "reservoir", 55, 40, 210, "reservoir")
    text("reservoir-name", "Reservoir / Dam API", 5, 247, 310, 40, 30, True, "reservoir")
    text("reservoir-choice", "Rules OR checked LLM", 5, 293, 310, 34, 27, parent="reservoir")
    card("downstream", 1200, 920, 350, 325)
    icon("downstream-icon", "routing", 70, 0, 210, "downstream")
    text("downstream-name", "Downstream routing", 5, 215, 340, 45, 30, True, "downstream")
    text("downstream-detail", "Lohmann", 5, 270, 340, 40, 32, parent="downstream")
    text("outlet-label", "Downstream\ndischarge", 1575, 990, 150, 95, 28, True)

    edge("prompt-model", "prompt", "language-model", PLUM, (1, .5), (0, .5))
    edge("model-output", "language-model", "rule-output", PLUM, (1, .5), (0, .5))
    edge("output-checker", "rule-output", "checker", PLUM, (1, .5), (0, .5))
    edge("knowledge-prompt", "knowledge", "prompt", GRAY, (.25, 0), (.4, 1), dashed=True, width=4)
    edge("checker-stop", "checker", "stop", "#916D58", (.85, 1), (.6, 0), width=4)
    text("invalid-label", "Invalid", 1530, 480, 180, 36, 29, color="#916D58")
    edge("checker-audit", "checker", "audit", GREEN, (.1, 1), (.85, 0), [(1262, 525), (1156, 525)], dashed=True, width=4)
    edge("checked-release", "checker", "reservoir", PLUM, (1, .65), (.9, 0), [(1730, 405.5), (1730, 730), (1098, 730)], width=5)
    text("valid-label", "Valid release proposal", 1280, 743, 450, 48, 32, color=PLUM)
    edge("runoff-upstream", "runoff", "upstream", BLUE, (1, .5), (0, .5), width=6)
    edge("upstream-reservoir", "upstream", "reservoir", BLUE, (1, .5), (0, .5), width=6)
    edge("reservoir-downstream", "reservoir", "downstream", BLUE, (1, .5), (0, .5), width=6)
    # A terminal label represents the river result, not another model.
    vertex("outlet-anchor", "", 1710, 1080, 5, 5, "strokeColor=none;fillColor=none;")
    edge("downstream-outlet", "downstream", "outlet-anchor", BLUE, (1, .5), (0, .5), width=6)
    edge("inflow-prompt", "upstream", "prompt", GRAY, (.3, 0), (0, .5), [(510, 705), (65, 705), (65, 365)], dashed=True, width=4)
    text("inflow-label", "Reservoir inflow", 75, 720, 340, 45, 32, color=INK)
    edge("reservoir-feedback", "reservoir", "prompt", GREEN, (.1, 0), (.85, 1), [(842, 795), (555, 795), (555, 520), (314.5, 520)], dashed=True, width=4)
    text("history-label", "Storage / water level\nExecuted release history", 575, 714, 415, 72, 29, color=GREEN)
    edge("execution-record", "reservoir", "audit", GREEN, (.65, 0), (.65, 1), [(1018, 860), (1044, 860)], dashed=True, width=4)

    ET.indent(document)
    OUTPUT.write_bytes(ET.tostring(document, encoding="utf-8", xml_declaration=True))
    (ASSETS / "relationship-map.json").write_text(json.dumps({
        "scope": "Generic HydroCNHS flow plus an independent LLM decision extension; one policy choice per reservoir, optional context, no named case.",
        "canvas": [1800, 1320], "nodes": nodes, "edges": connections,
        "responsibilities": {
            "HydroCNHS": "Native GWLF/ABCD rainfall-runoff, Lohmann routing and Dam coupling API.",
            "LLM modules": "Prompt assembled from available information, language model, response parsing, release proposal and strict action checking. The concept does not prescribe a timestep; the shipped operations driver is daily.",
            "policy alternatives": "The native Dam API accepts a user-defined rule policy or an added LLM policy; choose one per controlled reservoir.",
            "reservoir physics": "Added shared deterministic solver: feasible release, spill, storage and water balance. Not a built-in native HydroCNHS reservoir solver.",
            "audit / trace": "Record decision and physical execution; never infer strategy acceptance from rendering."
        },
        "conditions": {"checked-release": "Format and value checks valid; only the selected LLM policy returns this proposal through the Dam API.",
                       "checker-stop": "Malformed, incomplete or invalid action; stop before physical transition, without a fallback policy.",
                       "knowledge-prompt": "Optional configured information, not a mandatory decision stage."},
        "notes": ["Rule output is a requested release value, not executable code. Parsing and checking are combined conceptual roles; a malformed reply stops before reservoir execution.",
                  "Checker PASS means the action contract passed, not that a strategy audit accepted the policy.",
                  "Invalid actions stop before storage changes; no automatic rule-policy fallback is implied.",
                  "Controlled release plus spill enters downstream routing once.",
                  "Actual executed release and resulting state feed later observations.",
                  "A configured river network determines coupling between reservoirs.",
                  "No arrow changes climate inputs or upstream rainfall-runoff equations."]
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(OUTPUT)
    print(f"NATIVE_CARDS {len(nodes)} ATTACHED_EDGES {len(connections)}")


if __name__ == "__main__":
    build()
