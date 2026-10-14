"""Build the editable HydroOpsLM coupling figure from preserved icon assets."""

from pathlib import Path
import argparse
import base64
import json
import xml.etree.ElementTree as ET


FIGURES = Path(__file__).resolve().parents[1]
ASSETS = FIGURES / "assets" / "coupling-framework"
OUTPUT = FIGURES / "hydrocnhs-coupling-framework-en.drawio"

INK = "#1F2933"
BLUE = "#4F7F9C"
ORANGE = "#C46A28"
PURPLE = "#765780"
TEAL = "#3F7F78"
GRAY = "#7B858C"
FILLS = {BLUE: "#DEEDF5", ORANGE: "#FBE7D2", PURPLE: "#EDE2F3",
         TEAL: "#DDEFEA", GRAY: "#EEF1F4"}
REGION_FILLS = {BLUE: "#EEF6FA", ORANGE: "#FFF3E6", PURPLE: "#F5EFF8"}


def build(output_dir=None):
    # A separate output directory lets the rendered candidate be reviewed before replacement.
    destination = Path(output_dir) if output_dir else FIGURES
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / OUTPUT.name
    metadata_dir = destination if output_dir else ASSETS
    document = ET.Element("mxfile", host="app.diagrams.net", version="26.0.4")
    diagram = ET.SubElement(document, "diagram", id="coupling-framework", name="Framework")
    model = ET.SubElement(
        diagram, "mxGraphModel", dx="1880", dy="1090", grid="1", gridSize="10",
        page="1", pageScale="1", pageWidth="1880", pageHeight="1090",
        background="#FFFFFF", math="0", shadow="0",
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    nodes, edges = [], []

    def vertex(identity, value, x, y, w, h, style, parent="1"):
        cell = ET.SubElement(
            root, "mxCell", id=identity, value=value, style=style, vertex="1", parent=parent
        )
        ET.SubElement(
            cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h),
            **{"as": "geometry"},
        )
        return cell

    def text(identity, value, x, y, w, h, size=30, bold=False, parent="1",
             align="center", color=INK):
        return vertex(
            identity, value, x, y, w, h,
            "text;html=0;whiteSpace=nowrap;overflow=visible;"
            f"align={align};verticalAlign=middle;fontFamily=Arial;"
            f"fontSize={size};fontColor={color};fontStyle={int(bold)};"
            "strokeColor=none;fillColor=none;spacing=0;",
            parent,
        )

    def label(identity, value, x, y, w, h, size=30):
        vertex(identity + "-background", "", x, y, w, h,
               "rounded=0;fillColor=#FFFFFF;strokeColor=none;")
        return text(identity, value, x, y, w, h, size, True)

    def frame(identity, x, y, w, h, stroke, heading, heading_x, heading_w):
        vertex(identity, "", x, y, w, h,
               f"rounded=1;arcSize=4;fillColor={REGION_FILLS[stroke]};strokeColor={stroke};strokeWidth=3;")
        text(identity + "-heading", heading, heading_x, y + 16, heading_w, 42,
             32, True, align="left")

    def card(identity, x, y, w, h, stroke, width=3):
        vertex(identity, "", x, y, w, h,
               f"rounded=1;arcSize=7;fillColor={FILLS[stroke]};strokeColor={stroke};strokeWidth={width};")
        nodes.append({"id": identity, "bounds": [x, y, w, h], "outline": stroke,
                      "fill": FILLS[stroke]})

    def raster_icon(identity, filename, x, y, size, parent):
        encoded = base64.b64encode((ASSETS / filename).read_bytes()).decode("ascii")
        vertex(identity, "", x, y, size, size,
               f"shape=image;imageAspect=1;aspect=fixed;image=data:image/png,{encoded};", parent)

    def edge(identity, source, target, color, exit_xy, entry_xy, points=(), width=5):
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
            f"html=0;strokeColor={color};strokeWidth={width};endArrow=block;endFill=1;"
            f"exitX={exit_xy[0]};exitY={exit_xy[1]};exitDx=0;exitDy=0;"
            f"entryX={entry_xy[0]};entryY={entry_xy[1]};entryDx=0;entryDy=0;"
        )
        cell = ET.SubElement(
            root, "mxCell", id=identity, style=style, edge="1", parent="1",
            source=source, target=target,
        )
        geometry = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        if points:
            array = ET.SubElement(geometry, "Array", **{"as": "points"})
            for point_x, point_y in points:
                ET.SubElement(array, "mxPoint", x=str(point_x), y=str(point_y))
        edges.append({
            "id": identity, "source": source, "target": target, "color": color,
            "exit": list(exit_xy), "entry": list(entry_xy), "via": list(points),
        })

    # Outer framework and sibling policy regions.
    vertex("framework-boundary", "", 15, 15, 1850, 1060,
           f"rounded=1;arcSize=3;fillColor=#FFFFFF;strokeColor={INK};strokeWidth=4;")
    text("title", "HydroOpsLM", 48, 25, 650, 54, 46, True, align="left")
    text("subtitle", "One policy per reservoir", 48, 78, 650, 34, 30,
         align="left")

    frame("rule-boundary", 40, 125, 470, 330, ORANGE,
          "Rule-based operation", 66, 410)
    frame("llm-boundary", 540, 125, 1300, 330, PURPLE,
          "LLM modules", 566, 400)

    # Rule policy card and generated icon.
    card("rule-policy", 78, 210, 392, 220, ORANGE, width=4)
    raster_icon("rule-icon", "rule-operation.png", 18, 28, 145, "rule-policy")
    text("rule-name", "Operating\nrules", 174, 38, 200, 72, 30, True,
         "rule-policy", align="left")

    # Information is selected for the decision; it is not limited to local inflow.
    card("information", 555, 205, 180, 220, PURPLE)
    raster_icon("information-icon", "trace-records.png", 35, 2, 110, "information")
    text("information-name", "Available\ninformation", 5, 128, 170, 80, 30, True,
         "information")
    card("external-data", 555, 480, 180, 140, GRAY, width=2)
    raster_icon("external-data-icon", "hydrology.png", 58, 0, 64, "external-data")
    text("external-data-name", "External\ndata", 5, 65, 170, 70, 30, True, "external-data")
    card("knowledge", 780, 480, 180, 140, GRAY, width=2)
    raster_icon("knowledge-icon", "knowledge.png", 58, 0, 64, "knowledge")
    text("knowledge-name", "Optional\nknowledge", 5, 65, 170, 70, 30, True, "knowledge")

    card("prompt", 765, 205, 210, 220, PURPLE)
    raster_icon("prompt-icon", "knowledge.png", 50, 1, 110, "prompt")
    text("prompt-name", "Prompt", 5, 112, 200, 40, 30, True, "prompt")

    card("language-model", 1015, 205, 210, 220, PURPLE)
    raster_icon("language-model-icon", "decision.png", 43, 3, 125, "language-model")
    text("language-model-name", "Language\nmodel", 5, 132, 200, 78, 30, True,
         "language-model")

    card("proposal", 1265, 205, 240, 220, PURPLE)
    raster_icon("proposal-icon", "operation-proposal.png", 53, -5, 135, "proposal")
    text("proposal-name", "Operation\nproposal", 5, 132, 230, 74, 30, True, "proposal")

    card("checks", 1545, 205, 270, 220, TEAL)
    raster_icon("checks-icon", "response-checks.png", 70, -5, 130, "checks")
    text("checks-name", "Response\nchecks", 5, 132, 260, 74, 30, True, "checks")

    # Compact record sidecars. Audit evaluates the requested action before physics.
    card("operation-audit", 970, 470, 310, 155, TEAL)
    raster_icon("operation-audit-icon", "audit.png", 15, 15, 110, "operation-audit")
    text("operation-audit-name", "Operation\naudit", 130, 30, 170, 70, 30, True,
         "operation-audit", align="left")

    card("trace", 1300, 500, 350, 125, TEAL)
    raster_icon("trace-icon", "trace-records.png", 12, 8, 108, "trace")
    text("trace-name", "Trace records", 130, 45, 215, 40, 30, True,
         "trace", align="left")

    # Native HydroCNHS chain.
    frame("hydrocnhs-boundary", 40, 710, 1800, 340, BLUE,
          "Native HydroCNHS", 66, 500)

    card("runoff", 65, 775, 300, 260, BLUE)
    raster_icon("runoff-icon", "hydrology.png", 70, 0, 160, "runoff")
    text("runoff-name", "Rainfall-runoff", 5, 164, 290, 42, 30, True, "runoff")
    text("runoff-detail", "GWLF / ABCD", 5, 215, 290, 34, 30, parent="runoff")

    card("upstream", 435, 775, 300, 260, BLUE)
    raster_icon("upstream-icon", "routing.png", 70, 0, 160, "upstream")
    text("upstream-name", "Upstream\nrouting", 5, 145, 290, 66, 30, True, "upstream")
    text("upstream-detail", "Lohmann", 5, 216, 290, 34, 30, parent="upstream")

    # All four water-path centres are y=905: no automatic elbow in the water arrows.
    card("reservoir-operation", 805, 775, 300, 260, BLUE, width=4)
    raster_icon("reservoir-icon", "reservoir.png", 70, 0, 160, "reservoir-operation")
    text("reservoir-name", "Reservoir", 5, 164, 290, 42, 32, True,
         "reservoir-operation")
    text("reservoir-api", "Dam API", 5, 215, 290, 34, 30,
         parent="reservoir-operation")

    card("downstream", 1175, 775, 300, 260, BLUE)
    raster_icon("downstream-icon", "routing.png", 70, 0, 160, "downstream")
    text("downstream-name", "Downstream\nrouting", 5, 154, 290, 68, 30, True,
         "downstream")
    text("downstream-detail", "Lohmann", 5, 218, 290, 34, 30, parent="downstream")
    text("outlet-label", "Downstream\ndischarge", 1550, 804, 240, 76, 30, True)

    # Top policy sequence and short optional input.
    edge("information-prompt", "information", "prompt", INK, (1, .42), (0, .42), width=4)
    edge("external-information", "external-data", "information", INK, (.5, 0), (.5, 1), width=4)
    edge("knowledge-prompt", "knowledge", "prompt", INK, (.5, 0), (.5, 1), width=4)
    edge("prompt-model", "prompt", "language-model", INK, (1, .42), (0, .42), width=5)
    edge("model-proposal", "language-model", "proposal", INK, (1, .42), (0, .42), width=5)
    edge("proposal-checks", "proposal", "checks", INK, (1, .42), (0, .42), width=5)

    # Policy requests meet the same operation; neither passes through the other policy.
    edge("rule-reservoir", "rule-policy", "reservoir-operation", INK, (.5, 1),
         (45 / 300, 0), [(274, 650), (850, 650)], width=5)
    label("rule-release-label", "Rule-based release", 310, 610, 300, 38)
    edge("checks-reservoir", "checks", "reservoir-operation", INK, (.87, 1),
         (1, 58 / 260), [(1779.9, 725), (1130, 725), (1130, 833)], width=5)
    label("checked-release-label", "Checked release", 1460, 657, 260, 38)

    # The region supplies selected native values, including completed gauge flows.
    # The offset corridor avoids the external-data and knowledge source cards.
    edge("simulation-information", "hydrocnhs-boundary", "information", INK,
         (840 / 1800, 0), (1, .78), [(880, 635), (755, 635), (755, 376.6)], width=4)
    edge("information-rule", "reservoir-operation", "rule-policy", INK,
         (15 / 300, 0), (122 / 392, 1), [(820, 695), (200, 695)], width=4)

    # Audit receives the release request at the shared operation interface, before physics.
    # Trace subsequently binds that verdict to committed physical execution.
    edge("proposal-trace", "proposal", "trace", INK, (.45, 1), (73 / 350, 0), width=4)
    edge("checks-trace", "checks", "trace", INK, (.18, 1), (293.6 / 350, 0), width=4)
    edge("execution-audit", "reservoir-operation", "operation-audit", INK,
         (225 / 300, 0), (60 / 310, 1),
         width=4)
    label("audit-request-label", "Release\nrequest", 895, 635, 120, 68)
    edge("audit-trace", "operation-audit", "trace", INK, (1, .6), (0, .504), width=4)
    # Committed release, spill and storage are recorded separately from the proposal.
    edge("execution-trace", "reservoir-operation", "trace", INK,
         (285 / 300, 0), (150 / 350, 1), [(1090, 645), (1450, 645)], width=4)
    text("execution-record-label", "Actual operation", 1180, 653, 280, 38, 30, True)

    # Blue water path only.
    edge("runoff-upstream", "runoff", "upstream", BLUE, (1, .5), (0, .5), width=7)
    edge("upstream-reservoir", "upstream", "reservoir-operation", BLUE,
         (1, .5), (0, .5), width=7)
    edge("reservoir-downstream", "reservoir-operation", "downstream", BLUE,
         (1, .5), (0, .5), width=7)
    vertex("outlet-anchor", "", 1835, 902.5, 5, 5, "strokeColor=none;fillColor=none;")
    edge("downstream-outlet", "downstream", "outlet-anchor", BLUE,
         (1, .5), (0, .5), width=7)

    ET.indent(document)
    output.write_bytes(ET.tostring(document, encoding="utf-8", xml_declaration=True))
    relationship_map = {
        "scope": "HydroOpsLM: one selected policy feeds one shared reservoir operation in the native HydroCNHS chain.",
        "canvas": [1880, 1090],
        "nodes": nodes,
        "edges": edges,
        "line_semantics": {
            "blue": "solid water and implemented outflow",
            "black": "solid information, release requests, audit evidence, and trace records",
            "dashed_or_dotted": "not used",
            "crossings_or_jump_arcs": "not used",
        },
        "color_semantics": {
            "blue": "Hydrology, routing and reservoir calculation; pale fill shares the role of its border.",
            "orange": "Rule-based operation.",
            "purple": "LLM information and decision modules; teal checks remain distinct within the LLM region.",
            "teal": "Response checks, operation audit and trace recording; never PASS or FAIL.",
            "gray": "External data and optional knowledge sources.",
        },
        "responsibilities": {
            "Rule-based operation": "Selectable user operating rules produce a requested release.",
            "LLM modules": "Selected decision information, prompt, language model, operation proposal, and response checks form the alternative policy.",
            "Native HydroCNHS": "Provides GWLF/ABCD rainfall-runoff, Lohmann routing, and the native Dam API.",
            "Reservoir": "HydroOpsLM adds storage balance, release, and spill inside the native Dam API operation node.",
            "Operation audit": "Checks configured decision criteria before physics; optional control-point checks separately inspect routed outcomes.",
            "Trace records": "Binds policy records and decision-audit verdicts to implemented release, storage, and spill after physical execution.",
        },
        "policy_choice": "Each reservoir chooses exactly one policy: user operating rules or a checked LLM proposal.",
        "prompt_inputs": {
            "source": "A configured selection from simulation information and external data",
            "types": "Reservoir conditions, river/gauge conditions, executed history, demand, forecasts, and operating targets",
            "causality": "Downstream simulated flow uses completed steps; external records must be available by the decision clock",
            "legacy_examples": "The preserved FE Walter examples retain their original inflow, pool and release-history inputs",
            "optional": "optional knowledge",
        },
        "execution_contract": "Only a requested release enters reservoir operation; LLM rationale is retained in trace records.",
        "record_flow": "The shared operation interface supplies the release request to decision audit before physics. Trace later binds its verdict to committed physical execution; LLM proposal and checker records are retained separately.",
        "asset_hooks": {
            "rule": "docs/figures/assets/coupling-framework/rule-operation.png",
            "proposal": "docs/figures/assets/coupling-framework/operation-proposal.png",
            "checks": "docs/figures/assets/coupling-framework/response-checks.png",
            "trace": "docs/figures/assets/coupling-framework/trace-records.png",
        },
        "notes": [
            "Color identifies role, never verdict.",
            "All labels and connectors are native editable draw.io objects; illustrations are independently movable raster objects.",
            "The FAIL diagnostic caveat belongs in the external caption, not inside the diagram.",
        ],
    }
    (metadata_dir / "relationship-map.json").write_text(
        json.dumps(relationship_map, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(output)
    print(f"NODES {len(nodes)} EDGES {len(edges)} GENERATED_ICONS_REUSED_NO_NEW_GENERATION")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Render a candidate without replacing the figure.")
    build(parser.parse_args().output_dir)
