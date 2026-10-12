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
    model = ET.SubElement(diagram, "mxGraphModel", dx="1800", dy="1120", grid="1",
                          gridSize="10", page="1", pageScale="1", pageWidth="1800",
                          pageHeight="1120", background="#FFFFFF", math="0", shadow="0")
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

    # Boundaries describe responsibility, not a separate simulation runtime.
    frame("operations-boundary", 65, 160, 1645, 370, "#D6CDD5", "#FAF8FB")
    frame("hydrocnhs-boundary", 65, 675, 1645, 340, "#BDD0DB", "#F4F8FA")
    text("title", "Coupled hydrology & reservoir operations", 80, 35, 1640, 60, 44, True, align="left")
    text("subtitle", "HydroCNHS + configurable operation modules", 80, 105, 1640, 35, 28, align="left")
    text("operations-heading", "Reservoir operation extension", 95, 180, 760, 40, 30, True, align="left")
    text("core-heading", "HydroCNHS · rainfall–runoff & river routing", 95, 687, 880, 38, 30, True, align="left")

    card("settings", 100, 270, 205, 185)
    icon("settings-icon", "knowledge", 52, 0, 100, "settings")
    text("settings-name", "Settings", 10, 102, 185, 40, 29, True, "settings")
    text("settings-detail", "Policy context", 5, 145, 195, 32, 23, parent="settings")
    card("observation", 390, 290, 240, 145)
    text("observation-name", "Observation", 8, 12, 224, 43, 29, True, "observation")
    text("observation-detail", "Daily inflow\nState · history", 8, 68, 224, 64, 24, parent="observation")
    card("policy", 735, 245, 300, 205, "#F1EBF2", "#BAA9BE")
    icon("policy-icon", "decision", 100, 3, 100, "policy")
    text("policy-name", "Operation policy", 10, 110, 280, 40, 30, True, "policy")
    text("policy-detail", "LLM / custom controller", 5, 158, 290, 32, 24, parent="policy")
    card("validation", 1130, 310, 230, 105)
    text("validation-name", "Validate action", 8, 10, 214, 38, 29, True, "validation")
    text("validation-detail", "Schema · values", 8, 59, 214, 34, 24, parent="validation")
    card("stop", 1165, 455, 160, 52, "#F8EEE8", "#B58A70")
    text("stop-name", "Stop", 5, 2, 150, 46, 27, True, "stop")
    card("audit", 1460, 270, 200, 185, "#EFF5F0", "#ADC3B2")
    icon("audit-icon", "audit", 50, 0, 100, "audit")
    text("audit-name", "Audit / trace", 5, 108, 190, 45, 28, True, "audit")

    card("runoff", 95, 755, 225, 215)
    icon("runoff-icon", "hydrology", 58, 0, 110, "runoff")
    text("runoff-name", "Rainfall–runoff", 5, 113, 215, 45, 29, True, "runoff")
    text("runoff-detail", "Climate · catchment", 5, 166, 215, 35, 23, parent="runoff")
    card("upstream", 390, 755, 230, 215)
    icon("upstream-icon", "routing", 60, 0, 110, "upstream")
    text("upstream-name", "Upstream\nrouting", 5, 118, 220, 65, 29, True, "upstream")
    card("physics", 735, 745, 300, 250, "#FAF3E7", "#C5AA78")
    icon("physics-icon", "reservoir", 95, 0, 110, "physics")
    text("physics-name", "Reservoir physics", 5, 105, 290, 43, 30, True, "physics")
    text("physics-detail", "Limits · storage · spill\nWater balance", 5, 150, 290, 62, 24, parent="physics")
    text("physics-api", "Added solver · Dam API", 5, 220, 290, 25, 22, parent="physics", color="#7D6C46")
    card("downstream", 1130, 755, 230, 215)
    icon("downstream-icon", "routing", 60, 0, 110, "downstream")
    text("downstream-name", "Downstream\nrouting", 5, 118, 220, 65, 29, True, "downstream")
    card("river-flow", 1460, 800, 200, 125)
    text("river-flow-name", "River flow", 5, 30, 190, 60, 32, True, "river-flow")
    text("network-label", "Configured river network", 1360, 687, 320, 38, 23, align="right", color=BLUE)

    edge("settings-policy", "settings", "policy", PLUM, (0.5, 0), (0.12, 0),
         [(203, 235), (771, 235)], dotted=True, width=2.5)
    text("settings-policy-label", "Policy settings", 405, 240, 210, 30, 22, color=PLUM)
    edge("observation-policy", "observation", "policy", PLUM, (1, 0.48), (0, 0.57), dashed=True)
    edge("policy-validation", "policy", "validation", PLUM, (1, 0.57), (0, 0.48), dashed=True)
    text("request-label", "Requested\nrelease", 1005, 263, 175, 55, 22, color=PLUM)
    edge("invalid-stop", "validation", "stop", "#A27C64", (0.5, 1), (0.5, 0), width=2.5)
    text("invalid-label", "Invalid", 1255, 420, 110, 28, 22, color="#916D58")
    edge("valid-physics", "validation", "physics", PLUM, (0, 0.85), (0.8, 0),
         [(1090, 399), (1090, 560), (975, 560)], dashed=True)
    text("valid-label", "Valid release", 1110, 549, 185, 32, 23, color=PLUM)
    edge("runoff-upstream", "runoff", "upstream", BLUE, (1, 0.5), (0, 0.5), width=4)
    edge("upstream-physics", "upstream", "physics", BLUE, (1, 0.5), (0, 0.47), width=4)
    edge("physics-downstream", "physics", "downstream", BLUE, (1, 0.47), (0, 0.5), width=4)
    text("outflow-label", "Release\n+ spill", 1039, 888, 87, 65, 22, color=BLUE)
    edge("downstream-river", "downstream", "river-flow", BLUE, (1, 0.5), (0, 0.5), width=4)
    edge("inflow-observation", "upstream", "observation", GRAY, (0.5, 0), (0.5, 1), dotted=True, width=2.5)
    text("inflow-label", "Routed inflow", 350, 546, 190, 28, 23, color=GRAY)
    edge("state-feedback", "physics", "observation", GREEN, (0.3, 0), (1, 0.85),
         [(825, 610), (670, 610), (670, 414)], dashed=True, width=3)
    text("state-label", "Next-day state\nExecuted history", 620, 615, 190, 48, 22, color=GREEN)
    edge("decision-record", "policy", "audit", GRAY, (0.85, 0), (0.5, 0),
         [(990, 225), (1560, 225)], dotted=True, width=2.5)
    text("decision-record-label", "Decision record", 1170, 233, 220, 30, 22, color=GRAY)
    edge("execution-record", "physics", "audit", GRAY, (0.95, 0), (0.25, 1),
         [(1020, 720), (1410, 720), (1410, 485), (1510, 485)], dotted=True, width=2.5)
    text("execution-record-label", "Execution record", 1160, 670, 235, 30, 22, color=GRAY)

    # Compact legend; colors also have names, line styles and endpoint labels.
    for index, (name, color, dash) in enumerate([
        ("Water flow", BLUE, ""), ("Decision", PLUM, "8 5"),
        ("State feedback", GREEN, "8 5"), ("Data / records", GRAY, "1 5")
    ]):
        x = 190 + index * 370
        cell = ET.SubElement(root, "mxCell", id=f"legend-{index}", style=
                             f"strokeColor={color};strokeWidth=3;endArrow=block;endFill=1;"
                             + (f"dashed=1;dashPattern={dash};" if dash else ""),
                             edge="1", parent="1")
        geo = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        ET.SubElement(geo, "mxPoint", x=str(x), y="1070", **{"as": "sourcePoint"})
        ET.SubElement(geo, "mxPoint", x=str(x+75), y="1070", **{"as": "targetPoint"})
        text(f"legend-label-{index}", name, x+88, 1048, 245, 44, 25, align="left")

    ET.indent(document)
    OUTPUT.write_bytes(ET.tostring(document, encoding="utf-8", xml_declaration=True))
    (ASSETS / "relationship-map.json").write_text(json.dumps({
        "scope": "Generic coupled hydrology/reservoir-operation framework; no case examples.",
        "canvas": [1800, 1120], "nodes": nodes, "edges": connections,
        "responsibilities": {
            "HydroCNHS": "Climate/catchment inputs, rainfall-runoff and configured river routing.",
            "operation extension": "Observation, configurable decision policy and action validation.",
            "reservoir physics": "Deterministic feasible release, spill, storage and water balance via Dam API.",
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
