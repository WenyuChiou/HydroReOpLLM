"""Read one verified saved decision; never run a model or simulation."""

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


def _inside(output, relative):
    path = (output / relative).resolve()
    if not path.is_relative_to(output):
        raise ValueError("trace reference escapes output")
    return path


def _backend_provenance(experiment, reservoir_id):
    names = [name for name, settings in experiment["network"]["reservoirs"].items()
             if settings["physical"]["reservoir_id"] == reservoir_id]
    if len(names) != 1:
        raise ValueError("cannot bind reservoir ID to exactly one configured reservoir")
    provenance = experiment.get("backend_provenance", {}).get(names[0])
    if not isinstance(provenance, dict):
        raise ValueError("missing bound backend provenance")
    return provenance


def _provider_evidence(trace, provenance):
    """Return saved provider facts; completion is evidence, not a fresh request."""
    model_used = trace.get("model_used")
    if model_used is False:
        if trace.get("data_kind") != "synthetic_fixture":
            raise ValueError("offline trace must declare synthetic_fixture")
        return {
            "model_used": False,
            "data_kind": "synthetic_fixture",
            "backend": provenance.get("backend"),
            "completion": "saved fixture reply",
        }
    if model_used is not True:
        raise ValueError("trace must explicitly declare whether a model was used")
    model = trace.get("model")
    provider_reply = trace.get("provider_reply")
    if not isinstance(model, dict) or not isinstance(provider_reply, dict):
        raise ValueError("live trace is missing saved model/provider evidence")
    if provenance.get("model_used") is not True or provenance.get("model") != model:
        raise ValueError("live trace/model provenance mismatch")
    provider = model.get("provider")
    if provider == "ollama":
        complete = (provider_reply.get("done") is True and
                    ("done_reason" not in provider_reply or provider_reply["done_reason"] == "stop"))
        completion = {"done": provider_reply.get("done"),
                      "done_reason": provider_reply.get("done_reason")}
    elif provider == "openai_compatible":
        choices = provider_reply.get("choices")
        complete = (isinstance(choices, list) and len(choices) == 1 and
                    isinstance(choices[0], dict) and choices[0].get("finish_reason") == "stop")
        completion = {"finish_reason": choices[0].get("finish_reason")} if complete else None
    else:
        raise ValueError("unsupported saved provider evidence")
    if not complete:
        raise ValueError("saved provider reply does not prove complete generation")
    return {
        "model_used": True,
        "backend": provenance.get("backend"),
        "provider": provider,
        "model": model.get("model"),
        "temperature": model.get("temperature"),
        "completion": completion,
        "request_id": trace.get("request_id"),
        "usage": trace.get("usage"),
    }


def load_decision_flow(output, *, reservoir_id="fe_walter", timestep=0,
                       require_offline=False):
    """Keep saved record bindings/verdicts; recheck only the common action."""
    output = Path(output).resolve()
    verified = verify_run(output, require_offline=require_offline)
    experiment = json.loads((output / "experiment.json").read_text(encoding="utf-8"))
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
    raw_ref = decision.get("raw_policy_ref")
    if not isinstance(raw_ref, dict) or set(raw_ref) != {"path", "sha256"}:
        raise ValueError("decision is missing its exact raw policy reference")
    raw_path = _inside(output, raw_ref["path"])
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    trace = raw.get("backend_trace")
    if not isinstance(trace, dict) or not {"system", "prompt", "raw_reply", "input_variables"} <= trace.keys():
        raise ValueError("this inspector requires a reference prompt/reply trace")
    if (not isinstance(trace["system"], str) or not trace["system"].strip() or
            not isinstance(trace["prompt"], str) or not trace["prompt"].strip() or
            not isinstance(trace["raw_reply"], dict)):
        raise ValueError("saved prompt/reply trace is incomplete")
    variables = trace["input_variables"]
    if (not isinstance(variables, dict) or variables.get("timestep") != timestep or
            variables.get("date") != decision["timestamp"] or
            variables.get("reservoir_profile") != reservoir_id or
            variables.get("inflow_cms") != decision["observation"]["inflow_cms"] or
            variables.get("storage_start_m3") != decision["observation"]["state"]["storage_m3"]):
        raise ValueError("saved prompt variables do not match the selected decision")
    provenance = _backend_provenance(experiment, reservoir_id)
    provider_evidence = _provider_evidence(trace, provenance)
    proposal = parse_action(decision["action"]).to_dict()
    if physics["record"]["action"] != proposal:
        raise ValueError("proposal/physics binding differs")
    following = [row for row in decisions if row["reservoir_id"] == reservoir_id
                 and row["timestep"] == timestep + 1]
    next_info = following[0]["observation"] if following else None
    original_ref = audit["original_payload_ref"]
    original_path = _inside(output, original_ref["path"])
    original_audit = json.loads(original_path.read_text(encoding="utf-8"))
    saved_audit = {"status": audit["status"], "original": original_audit}
    execution = physics["record"]["transition"]
    # Preserve executable notebook consumers without inventing a saved check.
    compatibility = {
        "proposal": proposal,
        "checker": {"action_contract_recheck": "PASS",
                    "meaning": "current normalized-action recheck; not a historical checker event"},
        "audit": saved_audit,
        "execution": execution,
    }
    if not provider_evidence["model_used"]:
        compatibility.update(data_kind="synthetic_fixture", synthetic_reply=trace["raw_reply"])
    return {
        **compatibility,
        "decision_id": decision_id,
        "run_mode": "live_provider" if provider_evidence["model_used"] else "offline_fixture",
        "provider_evidence": provider_evidence,
        "info": decision["observation"],
        "prompt_variables": trace["input_variables"],
        "system_prompt": trace["system"],
        "prompt": trace["prompt"],
        "response_schema": trace.get("schema"),
        "saved_native_reply": trace["raw_reply"],
        "saved_requested_action": decision["action"],
        "current_recheck": {"action_contract": "PASS", "normalized_action": proposal,
                            "meaning": "current recheck; no historical checker event is claimed"},
        "saved_audit": saved_audit,
        "saved_implemented_physics": execution,
        "saved_native_history": variables.get("native_history"),
        "next_info": next_info,
        "trace_files": {"policy": raw_ref["path"],
                        "audit": original_ref["path"], "physics": "physics.jsonl"},
        "verification": verified,
    }


def show_decision_flow(output, *, reservoir_id="fe_walter", timestep=0,
                       require_offline=False):
    """Print the actual saved prompt, reply, decision, audit and physics in full."""
    flow = load_decision_flow(output, reservoir_id=reservoir_id, timestep=timestep,
                              require_offline=require_offline)
    for key in ["decision_id", "run_mode", "provider_evidence", "info", "prompt_variables",
                "system_prompt", "prompt", "response_schema", "saved_native_reply",
                "saved_requested_action", "current_recheck", "saved_audit",
                "saved_implemented_physics", "saved_native_history", "next_info", "trace_files"]:
        print("\n=== " + key + " ===")
        value = flow[key]
        print(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False))
    return flow


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reservoir-id", default="fe_walter")
    parser.add_argument("--timestep", type=int, default=0)
    parser.add_argument("--require-offline", action="store_true",
                        help="refuse saved runs with any provider calls")
    args = parser.parse_args()
    show_decision_flow(args.output, reservoir_id=args.reservoir_id, timestep=args.timestep,
                       require_offline=args.require_offline)
