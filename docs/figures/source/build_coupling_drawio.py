"""Preserve the reviewed Figure 1 and derive its editable relationship manifest.

The canonical source is the adjacent .drawio file, including embedded icons.
Edit that source in draw.io. This command copies its exact bytes for review;
it does not recreate an obsolete layout or rerender accepted PNG/PDF exports.
"""
from pathlib import Path
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

FIGURES = Path(__file__).resolve().parents[1]
ASSETS = FIGURES / "assets" / "coupling-framework"
OUTPUT = FIGURES / "hydrocnhs-coupling-framework-en.drawio"


def build(output_dir=None):
    """Copy the canonical source and describe every displayed information flow."""
    raw = OUTPUT.read_bytes()
    document = ET.fromstring(raw)
    cells = list(document.iter("mxCell"))
    identities = {cell.get("id") for cell in cells}
    edges, nodes, labels = [], [], {}
    for cell in cells:
        identity = cell.get("id")
        value = cell.get("value")
        if value:
            labels[identity] = value.replace("<br>", " ")
        if cell.get("edge") == "1":
            source, target = cell.get("source"), cell.get("target")
            if source not in identities or target not in identities:
                raise ValueError("Figure 1 has a disconnected edge: " + str(identity))
            edges.append({"id": identity, "source": source, "target": target,
                          "label": value or "", "style": cell.get("style", "")})
        elif cell.get("vertex") == "1":
            # Keep semantic styles, not duplicated embedded image/base64 bytes.
            style = dict(part.split("=", 1) for part in cell.get("style", "").split(";")
                         if "=" in part)
            nodes.append({"id": identity, "parent": cell.get("parent"),
                          "fill": style.get("fillColor"), "border": style.get("strokeColor"),
                          "optional": style.get("dashed") == "1"})
    manifest = {
        "source": OUTPUT.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "scope": "HydroReOpLLM adds reservoir decisions, checking and records to HydroCNHS.",
        "nodes": nodes, "labels": labels, "edges": edges,
        "execution": {
            "hydrology": "precomputed continuous upstream hydrology",
            "operation": "daily decision, physics, downstream routing and commit",
            "feedback": "current inlet and beginning state plus previously committed history",
            "downstream_causality": "same-step downstream outcome is not returned to its producing decision",
        },
        "line_semantics": {
            "solid": "directed water, decision information or recorded evidence",
            "dashed_border": "optional knowledge or operating-rule audit",
            "water": "runoff, inlet, implemented controlled release plus spill",
        },
        "color_semantics": {
            "region_fills": "HydroCNHS host versus highlighted LLM decision extension",
            "decision_cards": "rule-based or LLM decision functions, not source ownership",
            "validation_and_record_cards": "response validation, optional audit and trace; never a PASS/FAIL color",
        },
        "responsibilities": {
            "response_validation": "Parse the response contract before producing a normalized requested release.",
            "operating_rule_audit": "Record configured diagnostic criteria; target failure does not resample the model.",
            "trace_records": "Bind actual messages, proposals, audits and committed physical execution.",
        },
        "exports": "Accepted PNG, SVG and 180 mm PDF are reviewed separately; this command does not overwrite them.",
    }
    destination = Path(output_dir) if output_dir else FIGURES
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / OUTPUT.name
    if target.resolve() != OUTPUT.resolve():
        target.write_bytes(raw)
    metadata_dir = destination if output_dir else ASSETS
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "relationship-map.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(target)
    print("NODES", len(nodes), "EDGES", len(edges), "REVIEWED_SOURCE_PRESERVED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Copy an editable candidate without changing publication exports.")
    build(parser.parse_args().output_dir)
