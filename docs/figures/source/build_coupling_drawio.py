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
                          pageHeight="1160", background="#FFFFFF", math="0", shadow="0")
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
               f"rounded=1;arcSize=4;fillColor={fill};strokeColor={color};strokeWidth=1.5;")

    def card(identity, x, y, w, h, fill="#FFFFFF", stroke="#C4D2D8"):
        vertex(identity, "", x, y, w, h,
               f"rounded=1;arcSize=8;fillColor={fill};strokeColor={stroke};strokeWidth=1.8;")
        nodes.append({"id": identity, "bounds": [x, y, w, h]})

    def icon(identity, key, x, y, size, parent):
        encoded = base64.b64encode((ASSETS / f"{key}.png").read_bytes()).decode("ascii")
        vertex(identity, "", x, y, size, size,
               f"shape=image;imageAspect=1;aspect=fixed;image=data:image/png,{encoded};", parent)

    def edge(identity, source, target, color, exit_xy, entry_xy, points=(), dashed=False,
             dotted=False, width=3.5):
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

    # Native HydroCNHS hosts both policies; the physical solver is an addition.
    frame("operations-boundary", 50, 130, 1700, 400, "#D6CDD5", "#FAF8FB")
    frame("hydrocnhs-boundary", 50, 670, 1700, 440, "#BDD0DB", "#F4F8FA")
    text("title", "HydroCNHS + LLM Reservoir Agent", 65, 30, 1680, 65, 46, True, align="left")
    text("operations-heading", "LLM modules", 75, 150, 700, 45, 36, True, align="left")
    text("core-heading", "HydroCNHS", 75, 687, 580, 45, 36, True, align="left")
    text("api-heading", "Dam API", 730, 687, 320, 45, 36, True, align="left")

    card("observation", 85, 215, 330, 255)
    text("observation-name", "Daily prompt", 10, 18, 310, 48, 34, True, "observation")
    text("observation-detail", "Date · inflow\nStorage / water level\nPast executed releases", 12, 92, 306, 130, 30, parent="observation")
    card("knowledge", 480, 215, 240, 255)
    icon("knowledge-icon", "knowledge", 30, 0, 180, "knowledge")
    text("knowledge-name", "Knowledge", 5, 177, 230, 40, 34, True, "knowledge")
    text("knowledge-detail", "Optional · e.g. DKP", 5, 219, 230, 30, 26, parent="knowledge")
    card("policy", 790, 215, 240, 255, "#F1EBF2", "#BAA9BE")
    icon("policy-icon", "decision", 30, 0, 180, "policy")
    text("policy-name", "LLM decision", 5, 188, 230, 48, 34, True, "policy")
    card("validation", 1115, 265, 220, 125)
    text("validation-name", "Checker", 5, 15, 210, 44, 34, True, "validation")
    text("validation-detail", "Format · values", 5, 73, 210, 35, 28, parent="validation")
    card("stop", 1150, 445, 150, 55, "#F8EEE8", "#B58A70")
    text("stop-name", "Stop", 5, 3, 140, 46, 32, True, "stop")
    card("audit", 1405, 215, 280, 255, "#EFF5F0", "#ADC3B2")
    icon("audit-icon", "audit", 50, 0, 180, "audit")
    text("audit-name", "Audit / trace", 5, 188, 270, 48, 34, True, "audit")

    card("runoff", 75, 800, 250, 270)
    icon("runoff-icon", "hydrology", 35, 0, 180, "runoff")
    text("runoff-name", "Rainfall–runoff", 5, 178, 240, 45, 32, True, "runoff")
    text("runoff-detail", "GWLF / ABCD", 5, 225, 240, 38, 32, parent="runoff")
    card("upstream", 380, 800, 270, 270)
    icon("upstream-icon", "routing", 45, 0, 180, "upstream")
    text("upstream-name", "Upstream routing", 5, 178, 260, 45, 30, True, "upstream")
    text("upstream-detail", "Lohmann", 5, 225, 260, 38, 32, parent="upstream")
    card("rule-mode", 730, 745, 225, 65)
    text("rule-mode-name", "Rule-based", 5, 8, 215, 48, 34, True, "rule-mode")
    card("llm-mode", 1010, 745, 185, 65, "#F1EBF2", "#BAA9BE")
    text("llm-mode-name", "LLM", 5, 8, 175, 48, 34, True, "llm-mode")
    card("physics", 760, 850, 370, 225, "#FAF3E7", "#C5AA78")
    icon("physics-icon", "reservoir", 2, 4, 180, "physics")
    text("physics-name", "Reservoir", 184, 15, 178, 45, 34, True, "physics")
    text("physics-detail", "Limits\nStorage · spill", 181, 82, 184, 80, 28, parent="physics")
    text("physics-api", "Added solver · water balance", 5, 181, 360, 37, 27, parent="physics", color="#7D6C46")
    card("downstream", 1230, 800, 270, 270)
    icon("downstream-icon", "routing", 45, 0, 180, "downstream")
    text("downstream-name", "Downstream\nrouting", 5, 176, 260, 60, 30, True, "downstream")
    text("downstream-detail", "Lohmann", 5, 236, 260, 32, 32, parent="downstream")
    card("river-flow", 1575, 887, 140, 95)
    text("river-flow-name", "River\nflow", 5, 5, 130, 85, 34, True, "river-flow")

    edge("observation-policy", "observation", "policy", PLUM, (0.5, 0), (0.5, 0),
         [(250, 200), (910, 200)], dashed=True)
    edge("knowledge-policy", "knowledge", "policy", GRAY, (1, 0.5), (0, 0.5), dotted=True)
    edge("policy-validation", "policy", "validation", PLUM, (1, 0.44), (0, 0.5), dashed=True)
    edge("invalid-stop", "validation", "stop", "#A27C64", (0.5, 1), (0.5, 0), width=2.5)
    text("invalid-label", "Invalid", 1250, 402, 100, 35, 28, color="#916D58")
    edge("valid-llm-mode", "validation", "llm-mode", PLUM, (1, 0.75), (0.5, 0),
         [(1370, 359), (1370, 600), (1102.5, 600)], dashed=True)
    text("valid-label", "Valid release", 1120, 552, 230, 42, 30, color=PLUM)
    edge("rule-physics", "rule-mode", "physics", PLUM, (0.5, 1), (0.22, 0), dashed=True)
    edge("llm-physics", "llm-mode", "physics", PLUM, (0.5, 1), (0.8, 0), dashed=True)
    edge("runoff-upstream", "runoff", "upstream", BLUE, (1, 0.5), (0, 0.5), width=4)
    edge("upstream-physics", "upstream", "physics", BLUE, (1, 0.5), (0, 0.38), width=4)
    edge("physics-downstream", "physics", "downstream", BLUE, (1, 0.38), (0, 0.5), width=4)
    text("outflow-label", "Release\n+ spill", 1129, 990, 100, 72, 27, color=BLUE)
    edge("downstream-river", "downstream", "river-flow", BLUE, (1, 0.5), (0, 0.5), width=4)
    edge("inflow-observation", "upstream", "observation", GRAY, (0.5, 0), (0.3, 1),
         [(515, 590), (184, 590)], dotted=True, width=2.5)
    text("inflow-label", "Daily inflow", 160, 540, 260, 42, 30, color=GRAY)
    edge("state-feedback", "physics", "observation", GREEN, (0, 0.12), (0.8, 1),
         [(695, 877), (695, 640), (349, 640)], dashed=True, width=3)
    text("state-label", "State + executed history", 560, 592, 500, 42, 30, color=GREEN)
    edge("decision-record", "policy", "audit", GRAY, (0.75, 0), (0.5, 0),
         [(970, 200), (1545, 200)], dotted=True, width=2.5)
    edge("execution-record", "physics", "audit", GRAY, (1, 0.08), (0.5, 1),
         [(1210, 868), (1210, 655), (1545, 655)], dotted=True, width=2.5)
    text("execution-record-label", "Execution\nrecord", 1580, 570, 150, 80, 28, color=GRAY)

    # Compact legend; colors also have names, line styles and endpoint labels.
    for index, (name, color, dash) in enumerate([
        ("Water flow", BLUE, ""), ("Decision", PLUM, "8 5"),
        ("State feedback", GREEN, "8 5"), ("Data / records", GRAY, "1 5")
    ]):
        x = 150 + index * 400
        cell = ET.SubElement(root, "mxCell", id=f"legend-{index}", style=
                             f"strokeColor={color};strokeWidth=3;endArrow=block;endFill=1;"
                             + (f"dashed=1;dashPattern={dash};" if dash else ""),
                             edge="1", parent="1")
        geo = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        ET.SubElement(geo, "mxPoint", x=str(x), y="1137", **{"as": "sourcePoint"})
        ET.SubElement(geo, "mxPoint", x=str(x+65), y="1137", **{"as": "targetPoint"})
        text(f"legend-label-{index}", name, x+78, 1117, 295, 40, 28, align="left")

    ET.indent(document)
    OUTPUT.write_bytes(ET.tostring(document, encoding="utf-8", xml_declaration=True))
    (ASSETS / "relationship-map.json").write_text(json.dumps({
        "scope": "Generic HydroCNHS coupling: rule-based and LLM policies; optional knowledge, no reservoir-specific case.",
        "canvas": [1800, 1160], "nodes": nodes, "edges": connections,
        "responsibilities": {
            "HydroCNHS": "Native GWLF/ABCD rainfall-runoff, Lohmann routing and Dam coupling API.",
            "LLM modules": "Daily prompt, optional knowledge/retrieval, LLM proposal and format/value checking.",
            "policy alternatives": "The native Dam API accepts a user-defined rule policy or an added LLM policy; choose one per controlled reservoir.",
            "reservoir physics": "Added shared deterministic solver: feasible release, spill, storage and water balance. Not a built-in native HydroCNHS reservoir solver.",
            "audit / trace": "Record decision and physical execution; never infer strategy acceptance from rendering."
        },
        "notes": ["Invalid actions stop before storage changes.",
                  "Controlled release plus spill enters downstream routing once.",
                  "Actual executed release and resulting state feed later observations.",
                  "A configured river network determines coupling between reservoirs.",
                  "No arrow changes climate inputs or upstream rainfall-runoff equations."]
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(OUTPUT)
    print(f"NATIVE_CARDS {len(nodes)} ATTACHED_EDGES {len(connections)}")


if __name__ == "__main__":
    build()
