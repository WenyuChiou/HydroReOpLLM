"""Build the editable HydroOpsLM coupling figure from preserved icon assets."""

from pathlib import Path
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


def build():
    document = ET.Element("mxfile", host="app.diagrams.net", version="26.0.4")
    diagram = ET.SubElement(document, "diagram", id="coupling-framework", name="Framework")
    model = ET.SubElement(
        diagram, "mxGraphModel", dx="1880", dy="1250", grid="1", gridSize="10",
        page="1", pageScale="1", pageWidth="1880", pageHeight="1250",
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

    def label(identity, value, x, y, w, h, size=24):
        vertex(identity + "-background", "", x, y, w, h,
               "rounded=0;fillColor=#FFFFFF;strokeColor=none;")
        return text(identity, value, x, y, w, h, size, True)

    def frame(identity, x, y, w, h, stroke, heading, heading_x, heading_w):
        vertex(identity, "", x, y, w, h,
               f"rounded=1;arcSize=4;fillColor=#FFFFFF;strokeColor={stroke};strokeWidth=3;")
        text(identity + "-heading", heading, heading_x, y + 16, heading_w, 42,
             32, True, align="left")

    def card(identity, x, y, w, h, stroke, width=3):
        vertex(identity, "", x, y, w, h,
               f"rounded=1;arcSize=7;fillColor=#FFFFFF;strokeColor={stroke};strokeWidth={width};")
        nodes.append({"id": identity, "bounds": [x, y, w, h], "outline": stroke})

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
    vertex("framework-boundary", "", 15, 15, 1850, 1220,
           f"rounded=1;arcSize=3;fillColor=#FFFFFF;strokeColor={INK};strokeWidth=4;")
    text("title", "HydroOpsLM", 48, 25, 650, 54, 46, True, align="left")
    text("subtitle", "One policy per reservoir", 48, 78, 650, 34, 24,
         align="left", color=GRAY)

    frame("rule-boundary", 40, 125, 470, 390, ORANGE,
          "Rule-based operation", 66, 410)
    frame("llm-boundary", 540, 125, 1300, 390, PURPLE,
          "LLM modules", 566, 400)

    # Rule policy card and generated icon.
    card("rule-policy", 78, 210, 392, 250, ORANGE, width=4)
    raster_icon("rule-icon", "rule-operation.png", 18, 28, 145, "rule-policy")
    text("rule-name", "User operating\nrules", 174, 38, 200, 72, 30, True,
         "rule-policy", align="left")
    text("rule-detail", "Current inflow\n+ beginning storage\n/ pool", 174, 122, 200, 92,
         24, parent="rule-policy", align="left")

    # LLM policy sequence with optional knowledge beside Prompt.
    card("knowledge", 555, 295, 115, 92, GRAY, width=2)
    text("knowledge-name", "Optional\nknowledge", 5, 13, 105, 64, 20, True,
         "knowledge", color=GRAY)

    card("prompt", 690, 205, 220, 275, PURPLE)
    raster_icon("prompt-icon", "knowledge.png", 55, 1, 110, "prompt")
    text("prompt-name", "Prompt", 5, 112, 210, 40, 30, True, "prompt")
    text("prompt-detail", "Available\ninformation\n+ operating\ninstructions",
         5, 152, 210, 110, 24, parent="prompt")

    card("language-model", 950, 205, 220, 275, PURPLE)
    raster_icon("language-model-icon", "decision.png", 48, 3, 125, "language-model")
    text("language-model-name", "Language\nmodel", 5, 142, 210, 78, 30, True,
         "language-model")

    card("proposal", 1210, 205, 250, 275, PURPLE)
    raster_icon("proposal-icon", "operation-proposal.png", 58, -5, 135, "proposal")
    text("proposal-name", "Operation\nproposal", 5, 132, 240, 74, 30, True, "proposal")
    text("proposal-detail", "Requested release\n+ rationale", 5, 210, 240, 54, 24,
         parent="proposal")

    card("checks", 1500, 205, 300, 275, TEAL)
    raster_icon("checks-icon", "response-checks.png", 85, -5, 130, "checks")
    text("checks-name", "Response\nchecks", 5, 132, 290, 74, 30, True, "checks")
    text("checks-detail", "Completeness\nfields / units / values", 5, 210, 290, 54, 24,
         parent="checks")

    # Compact record sidecars. Audit evaluates the requested action before physics.
    card("operation-audit", 970, 540, 310, 180, TEAL)
    raster_icon("operation-audit-icon", "audit.png", 15, 15, 110, "operation-audit")
    text("operation-audit-name", "Operation\naudit", 130, 8, 170, 64, 28, True,
         "operation-audit", align="left")
    text("operation-audit-detail", "Configured\noperating\ncriteria", 130, 84, 170, 84,
         24, parent="operation-audit", align="left")

    card("trace", 1300, 570, 350, 150, TEAL)
    raster_icon("trace-icon", "trace-records.png", 12, 17, 108, "trace")
    text("trace-name", "Trace records", 130, 20, 215, 40, 28, True,
         "trace", align="left")
    text("trace-detail", "Prompt, reply, check,\nexecution", 130, 70, 205, 54,
         22, parent="trace", align="left")

    # Native HydroCNHS chain.
    frame("hydrocnhs-boundary", 40, 840, 1800, 375, BLUE,
          "Native HydroCNHS", 66, 500)

    card("runoff", 65, 915, 245, 260, BLUE)
    raster_icon("runoff-icon", "hydrology.png", 43, 0, 160, "runoff")
    text("runoff-name", "Rainfall-runoff", 5, 164, 235, 42, 30, True, "runoff")
    text("runoff-detail", "GWLF / ABCD", 5, 215, 235, 34, 24, parent="runoff")

    card("upstream", 365, 915, 255, 260, BLUE)
    raster_icon("upstream-icon", "routing.png", 48, 0, 160, "upstream")
    text("upstream-name", "Upstream\nrouting", 5, 145, 245, 66, 30, True, "upstream")
    text("upstream-detail", "Lohmann", 5, 216, 245, 34, 24, parent="upstream")

    card("reservoir-operation", 830, 875, 500, 310, BLUE, width=4)
    raster_icon("reservoir-icon", "reservoir.png", 28, 48, 200, "reservoir-operation")
    text("reservoir-name", "Reservoir\noperation", 250, 24, 225, 76, 30, True,
         "reservoir-operation", align="left")
    text("reservoir-api", "via native Dam API", 250, 105, 225, 38, 24,
         parent="reservoir-operation", align="left", color=BLUE)
    text("reservoir-responsibility", "HydroOpsLM adds:\nstorage balance\nrelease + spill",
         250, 150, 225, 92, 24, parent="reservoir-operation", align="left")
    text("reservoir-output", "Implemented outflow", 250, 253, 225, 38, 24, True,
         "reservoir-operation", align="left", color=BLUE)

    card("downstream", 1400, 915, 270, 260, BLUE)
    raster_icon("downstream-icon", "routing.png", 55, 0, 160, "downstream")
    text("downstream-name", "Downstream\nrouting", 5, 154, 260, 68, 30, True,
         "downstream")
    text("downstream-detail", "Lohmann", 5, 218, 260, 34, 24, parent="downstream")
    text("outlet-label", "Downstream\ndischarge", 1680, 944, 150, 66, 24, True)

    # Top policy sequence and short optional input.
    edge("knowledge-prompt", "knowledge", "prompt", INK, (1, .5), (0, .5), width=4)
    edge("prompt-model", "prompt", "language-model", INK, (1, .42), (0, .42), width=5)
    edge("model-proposal", "language-model", "proposal", INK, (1, .42), (0, .42), width=5)
    edge("proposal-checks", "proposal", "checks", INK, (1, .42), (0, .42), width=5)

    # Two non-intersecting release corridors enter the shared operation from above.
    edge("rule-reservoir", "rule-policy", "reservoir-operation", INK, (1, .5), (.88, 0),
         [(520, 335), (520, 100), (1820, 100), (1820, 825), (1270, 825)], width=5)
    label("rule-release-label", "Rule release", 1600, 68, 170, 36)
    edge("checks-reservoir", "checks", "reservoir-operation", INK, (.87, 1), (.7, 0),
         [(1761, 535), (1761, 785), (1180, 785)], width=5)
    label("checked-release-label", "Checked release", 1480, 744, 210, 36)

    # Two separated information lanes enter Prompt from below.
    edge("inflow-prompt", "upstream", "prompt", INK, (.62, 0), (.27, 1),
         [(523, 800), (610, 800), (610, 540), (749, 540)], width=4)
    label("inflow-label", "Current inflow", 410, 646, 175, 38)
    edge("history-prompt", "reservoir-operation", "prompt", INK, (.2, 0), (.73, 1),
         [(930, 760), (660, 760), (660, 560), (851, 560)], width=4)
    label("history-label", "Beginning storage / pool\n+ implemented\nrelease history",
          690, 628, 265, 88)

    # Audit receives the release request at the shared operation interface, before physics.
    # Trace subsequently binds that verdict to committed physical execution.
    edge("proposal-trace", "proposal", "trace", INK, (.45, 1), (.065, 0), width=4)
    edge("checks-trace", "checks", "trace", INK, (.18, 1), (.725, 0), width=4)
    edge("execution-audit", "reservoir-operation", "operation-audit", INK, (.34, 0), (.097, 1),
         width=4)
    label("audit-request-label", "Release\nrequest", 1030, 742, 135, 60)
    edge("audit-trace", "operation-audit", "trace", INK, (1, .625), (0, .55), width=4)

    # Blue water path only.
    edge("runoff-upstream", "runoff", "upstream", BLUE, (1, .5), (0, .5), width=7)
    edge("upstream-reservoir", "upstream", "reservoir-operation", BLUE,
         (1, .5), (0, .5), width=7)
    edge("reservoir-downstream", "reservoir-operation", "downstream", BLUE,
         (1, .5), (0, .5), width=7)
    vertex("outlet-anchor", "", 1835, 1045, 5, 5, "strokeColor=none;fillColor=none;")
    edge("downstream-outlet", "downstream", "outlet-anchor", BLUE,
         (1, .5), (0, .5), width=7)

    ET.indent(document)
    OUTPUT.write_bytes(ET.tostring(document, encoding="utf-8", xml_declaration=True))
    relationship_map = {
        "scope": "HydroOpsLM: one selected policy feeds one shared reservoir operation in the native HydroCNHS chain.",
        "canvas": [1880, 1250],
        "nodes": nodes,
        "edges": edges,
        "line_semantics": {
            "blue": "solid water and implemented outflow",
            "black": "solid information, release requests, audit evidence, and trace records",
            "dashed_or_dotted": "not used",
            "crossings_or_jump_arcs": "not used",
        },
        "responsibilities": {
            "Rule-based operation": "Selectable user operating rules produce a requested release.",
            "LLM modules": "Prompt, language model, operation proposal, and response checks form the alternative policy.",
            "Native HydroCNHS": "Provides GWLF/ABCD rainfall-runoff, Lohmann routing, and the native Dam API.",
            "Reservoir operation": "HydroOpsLM adds storage balance, release, and spill inside the native Dam API operation node.",
            "Operation audit": "Evaluates the current observation and requested action from either selected policy before physical execution.",
            "Trace records": "Binds policy records and decision-audit verdicts to implemented release, storage, and spill after physical execution.",
        },
        "policy_choice": "Each reservoir chooses exactly one policy: user operating rules or a checked LLM proposal.",
        "prompt_inputs": {
            "current": "current inflow",
            "beginning_of_step": "beginning storage / pool and implemented release history",
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
    (ASSETS / "relationship-map.json").write_text(
        json.dumps(relationship_map, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(OUTPUT)
    print(f"NODES {len(nodes)} EDGES {len(edges)} GENERATED_ICONS 4")


if __name__ == "__main__":
    build()
