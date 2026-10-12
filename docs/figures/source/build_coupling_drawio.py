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

    # This is a concept view. Solver details belong in the companion notes.
    frame("operations-boundary", 50, 130, 1700, 485, "#D6CDD5", "#FAF8FB")
    frame("hydrocnhs-boundary", 50, 750, 1700, 380, "#BDD0DB", "#F4F8FA")
    text("title", "HydroCNHS + LLM Reservoir Agent", 65, 30, 1680, 65, 46, True, align="left")
    text("operations-heading", "LLM modules", 75, 150, 700, 45, 36, True, align="left")
    text("core-heading", "HydroCNHS", 75, 770, 580, 45, 36, True, align="left")

    card("prompt", 75, 240, 240, 265)
    icon("prompt-icon", "knowledge", 20, 0, 200, "prompt")
    text("prompt-name", "Prompt", 5, 211, 230, 44, 34, True, "prompt")
    card("language-model", 430, 240, 280, 265, "#F1EBF2", "#BAA9BE")
    icon("language-model-icon", "decision", 40, 0, 200, "language-model")
    text("language-model-name", "Language model", 5, 211, 270, 44, 32, True, "language-model")
    card("reader", 845, 315, 175, 115)
    text("reader-name", "Response\nreader", 5, 10, 165, 95, 32, True, "reader")
    card("decision", 1155, 315, 195, 115)
    text("decision-name", "Release\ndecision", 5, 10, 185, 95, 34, True, "decision")
    card("checker", 1485, 240, 230, 265)
    icon("checker-icon", "audit", 20, 5, 190, "checker")
    text("checker-name", "Checker", 5, 211, 220, 44, 34, True, "checker")

    # Optional context and records are secondary, rather than mandatory stages.
    card("knowledge", 375, 550, 310, 55, "#FFFFFF", "#C4D2D8")
    text("knowledge-name", "Optional knowledge", 5, 5, 300, 45, 28, parent="knowledge")
    card("audit", 1010, 550, 320, 55, "#EFF5F0", "#ADC3B2")
    text("audit-name", "Audit / trace", 5, 5, 310, 45, 30, True, "audit")
    card("stop", 1590, 550, 130, 55, "#F8EEE8", "#B58A70")
    text("stop-name", "Stop", 5, 3, 120, 46, 32, True, "stop")

    card("runoff", 75, 830, 280, 285)
    icon("runoff-icon", "hydrology", 40, 0, 200, "runoff")
    text("runoff-name", "Rainfall–runoff", 5, 207, 270, 40, 32, True, "runoff")
    text("runoff-detail", "GWLF / ABCD", 5, 249, 270, 34, 32, parent="runoff")
    card("upstream", 425, 830, 300, 285)
    icon("upstream-icon", "routing", 50, 0, 200, "upstream")
    text("upstream-name", "Upstream routing", 5, 207, 290, 40, 30, True, "upstream")
    text("upstream-detail", "Lohmann", 5, 249, 290, 34, 32, parent="upstream")
    card("reservoir", 795, 830, 300, 285, "#FAF3E7", "#C5AA78")
    icon("reservoir-icon", "reservoir", 50, 0, 200, "reservoir")
    text("reservoir-name", "Reservoir", 5, 207, 290, 40, 34, True, "reservoir")
    text("reservoir-choice", "Rule-based OR LLM", 5, 250, 290, 32, 28, parent="reservoir")
    text("api-heading", "Dam API", 795, 780, 300, 38, 32, True, align="left")
    card("downstream", 1165, 830, 330, 285)
    icon("downstream-icon", "routing", 65, 0, 200, "downstream")
    text("downstream-name", "Downstream routing", 5, 207, 320, 40, 30, True, "downstream")
    text("downstream-detail", "Lohmann", 5, 249, 320, 34, 32, parent="downstream")
    card("river-flow", 1565, 925, 150, 95)
    text("river-flow-name", "River\nflow", 5, 5, 130, 85, 34, True, "river-flow")

    edge("prompt-model", "prompt", "language-model", PLUM, (1, 0.5), (0, 0.5))
    edge("model-reader", "language-model", "reader", PLUM, (1, 0.5), (0, 0.5))
    text("response-label", "Response", 715, 323, 125, 40, 28, color=PLUM)
    edge("reader-decision", "reader", "decision", PLUM, (1, 0.5), (0, 0.5))
    text("parsed-label", "Release", 1025, 323, 125, 40, 28, color=PLUM)
    edge("decision-checker", "decision", "checker", PLUM, (1, 0.5), (0, 0.5))
    text("proposal-label", "Proposal", 1355, 323, 125, 40, 28, color=PLUM)
    edge("knowledge-prompt", "knowledge", "prompt", GRAY, (0, 0.5), (0.5, 1),
         [(195, 577.5)], dotted=True, width=2.5)
    edge("checker-stop", "checker", "stop", "#A27C64", (0.75, 1), (0.52, 0), width=2.5)
    text("fail-label", "FAIL", 1555, 508, 85, 37, 28, color="#916D58")
    edge("checked-release", "checker", "reservoir", PLUM, (0.2, 1), (0.5, 0),
         [(1531, 655), (945, 655)], dashed=True)
    text("pass-label", "PASS · checked release", 1125, 660, 370, 42, 30, color=PLUM)
    edge("runoff-upstream", "runoff", "upstream", BLUE, (1, 0.5), (0, 0.5), width=4)
    edge("upstream-reservoir", "upstream", "reservoir", BLUE, (1, 0.5), (0, 0.5), width=4)
    edge("reservoir-downstream", "reservoir", "downstream", BLUE, (1, 0.5), (0, 0.5), width=4)
    edge("downstream-river", "downstream", "river-flow", BLUE, (1, 0.5), (0, 0.5), width=4)
    edge("inflow-prompt", "upstream", "prompt", GRAY, (0.5, 0), (0.25, 1),
         [(575, 675), (135, 675)], dotted=True, width=2.5)
    text("inflow-label", "Routed inflow", 145, 628, 290, 42, 30, color=GRAY)
    edge("state-feedback", "reservoir", "prompt", GREEN, (0, 0.2), (0.75, 1),
         [(760, 887), (760, 725), (255, 725)], dashed=True, width=3)
    text("state-label", "State / release history", 320, 681, 425, 40, 30, color=GREEN)
    edge("decision-record", "decision", "audit", GRAY, (0.5, 1), (0.75, 0),
         dotted=True, width=2.5)
    edge("execution-record", "reservoir", "audit", GRAY, (1, 0.15), (0.4, 1),
         [(1135, 872.75), (1135, 725), (1138, 725)], dotted=True, width=2.5)

    ET.indent(document)
    OUTPUT.write_bytes(ET.tostring(document, encoding="utf-8", xml_declaration=True))
    (ASSETS / "relationship-map.json").write_text(json.dumps({
        "scope": "Generic HydroCNHS flow plus an independent LLM decision extension; one policy choice per reservoir, optional context, no named case.",
        "canvas": [1800, 1160], "nodes": nodes, "edges": connections,
        "responsibilities": {
            "HydroCNHS": "Native GWLF/ABCD rainfall-runoff, Lohmann routing and Dam coupling API.",
            "LLM modules": "Prompt assembled from available information, language model, response parsing, release proposal and strict action checking. The concept does not prescribe a timestep; the shipped operations driver is daily.",
            "policy alternatives": "The native Dam API accepts a user-defined rule policy or an added LLM policy; choose one per controlled reservoir.",
            "reservoir physics": "Added shared deterministic solver: feasible release, spill, storage and water balance. Not a built-in native HydroCNHS reservoir solver.",
            "audit / trace": "Record decision and physical execution; never infer strategy acceptance from rendering."
        },
        "conditions": {"checked-release": "Action contract PASS; only the selected LLM policy returns this proposal through the Dam API.",
                       "checker-stop": "Action contract FAIL; stop before physical transition, without a fallback policy.",
                       "knowledge-prompt": "Optional configured information, not a mandatory decision stage."},
        "notes": ["The reader and checker are conceptual roles, not a claim of two separate runtime services. A malformed response may fail in the reader; Stop also represents that terminal decision-path failure.",
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
