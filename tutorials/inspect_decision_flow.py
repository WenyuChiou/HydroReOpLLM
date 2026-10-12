"""Read a verified offline reference decision; never run a model or simulation."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_reservoir_agent.contracts import parse_action
from llm_reservoir_agent.verification import verify_run


def _rows(output, name):
    return [json.loads(line) for line in (output / name).read_text(encoding="utf-8").splitlines()]


def load_decision_flow(output, *, reservoir_id="fe_walter", timestep=0):
    """Keep record binding and original verdicts; recheck only the common action."""
    output = Path(output).resolve()
    verified = verify_run(output, require_offline=True)
    decisions = _rows(output, "decisions.jsonl")
    matching = [row for row in decisions
                if row["reservoir_id"] == reservoir_id and row["timestep"] == timestep]
    if len(matching) != 1:
        raise ValueError("select exactly one recorded reservoir/timestep")
    decision = matching[0]
    decision_id = decision["decision_id"]

    def bound(name):
        matches = [row for row in _rows(output, name) if row["decision_id"] == decision_id]
        if len(matches) != 1:
            raise ValueError("missing or ambiguous bound record: " + name)
        return matches[0]

    physics = bound("physics.jsonl")
    audit = bound("audit.jsonl")
    raw_path = output / "raw" / ("policy_" + decision_id + ".json")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    trace = raw.get("backend_trace")
    if not isinstance(trace, dict) or not {"system", "prompt", "raw_reply", "input_variables"} <= trace.keys():
        raise ValueError("this inspector requires a reference prompt/reply trace")
    if trace.get("model_used") is not False or trace.get("data_kind") != "synthetic_fixture":
        raise ValueError("this lesson requires explicitly synthetic offline replies")
    proposal = parse_action(decision["action"]).to_dict()
    if physics["record"]["action"] != proposal:
        raise ValueError("proposal/physics binding differs")
    following = [row for row in decisions if row["reservoir_id"] == reservoir_id
                 and row["timestep"] == timestep + 1]
    next_info = following[0]["observation"] if following else None
    original_ref = audit["original_payload_ref"]
    original_path = (output / original_ref["path"]).resolve()
    if not original_path.is_relative_to(output):
        raise ValueError("audit reference escapes output")
    original_audit = json.loads(original_path.read_text(encoding="utf-8"))
    return {
        "decision_id": decision_id,
        "data_kind": trace["data_kind"],
        "info": decision["observation"],
        "prompt_variables": trace["input_variables"],
        "system_prompt": trace["system"],
        "prompt": trace["prompt"],
        "response_schema": trace.get("schema"),
        "synthetic_reply": trace["raw_reply"],
        "proposal": proposal,
        "checker": {"action_contract_recheck": "PASS",
                    "meaning": "current normalized-action recheck; not a historical checker event"},
        "audit": {"status": audit["status"], "original": original_audit},
        "execution": physics["record"]["transition"],
        "next_info": next_info,
        "trace_files": {"policy": str(raw_path.relative_to(output)),
                        "audit": original_ref["path"], "physics": "physics.jsonl"},
        "verification": verified,
    }


def show_decision_flow(output, *, reservoir_id="fe_walter", timestep=0):
    """Print the actual saved messages in full, with explicit fixture semantics."""
    flow = load_decision_flow(output, reservoir_id=reservoir_id, timestep=timestep)
    for key in ["decision_id", "data_kind", "info", "prompt_variables", "system_prompt",
                "prompt", "response_schema", "synthetic_reply", "proposal", "checker",
                "audit", "execution", "next_info", "trace_files"]:
        print("\n=== " + key + " ===")
        value = flow[key]
        print(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False))
    return flow


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reservoir-id", default="fe_walter")
    parser.add_argument("--timestep", type=int, default=0)
    args = parser.parse_args()
    show_decision_flow(args.output, reservoir_id=args.reservoir_id, timestep=args.timestep)
