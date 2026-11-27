"""Xindian River Feitsui Reservoir joint-dispatch study policy integrated with HydroReOpLLM."""

from __future__ import annotations

from collections import deque
import csv
from hashlib import sha256
import json
import math
from pathlib import Path

from llm_reservoir_agent.audit import json_snapshot
from llm_reservoir_agent.configured_backend import ConfiguredBackend
from llm_reservoir_agent.contracts import ACTION_SCHEMA_VERSION
from llm_reservoir_agent.prompt import PromptSpec

from .formatter import XindianStudyPrompt


supports_prompt_context = True


def validate_backend(spec, *, base_path, runtime_root, physical, mode, days, model, auditor_settings):
    if set(spec) - {"reservoir", "mode", "model", "strategy", "auditors"}:
        raise ValueError("xindian_study accepts only its fixed prompt design (reservoir, mode, model, strategy, auditors)")
    if mode != "llm" or model is None:
        raise ValueError("xindian_study requires an LLM mode and model profile")
    if physical["reservoir_id"] != "feitsui" or physical["dt_seconds"] != 86_400:
        raise ValueError("xindian_study requires the daily Feitsui Reservoir physical case")
    root = Path(__file__).resolve().parents[1]
    system = root / "prompts/feitsui.system.txt"
    curve = root / "study/elevation_storage.csv"
    schemas = root / "study/response_schemas.json"
    inflows = root / "inflows.csv"
    pins = {str(path): sha256(path.read_bytes()).hexdigest() for path in (system, curve, schemas)}
    schema = json.loads(schemas.read_text(encoding="utf-8"))["feitsui"]
    return {
        "study": {
            "system": str(system),
            "curve": str(curve),
            "inflows": str(inflows),
            "schema": schema,
        }
    }, pins


def _system_text(study):
    return Path(study["system"]).read_text(encoding="utf-8")


def _load_node_inflows(study, node_id: str) -> dict[str, float]:
    path = Path(study["inflows"])
    if not path.is_file():
        return {}
    out: dict[str, float] = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["node"] == node_id:
                out[row["date"]] = float(row["local_inflow_cms"])
    return out


def preview_backend(settings, physical, runtime_root):
    study = settings["study"]
    prompt = XindianStudyPrompt(
        Path(study["curve"]),
        physical["capacity_m3"],
        physical["minimum_release_cms"],
        physical["maximum_release_cms"],
    )
    feitsui_flows = _load_node_inflows(study, "feitsui_local")
    zhitan_flows = _load_node_inflows(study, "zhitan_local")
    sample_obs = {
        "timestamp": "2025-01-01T00:00:00",
        "inflow_cms": feitsui_flows.get("2025-01-01", 0.0),
        "state": {"storage_m3": physical["initial_storage_m3"]},
    }
    return {
        "kind": "config_preview",
        "model_used": False,
        "messages": [
            {"role": "system", "content": _system_text(study)},
            {
                "role": "user",
                "content": prompt.render(
                    sample_obs,
                    (),
                    downstream_lateral_cms=zhitan_flows.get("2025-01-01"),
                ),
            },
        ],
        "response_json_schema": study["schema"],
    }


def _parse_release(value, schema, physical):
    fields = schema["properties"]
    if not isinstance(value, dict) or value.keys() != fields.keys():
        raise ValueError("the model response does not match the Xindian study fields")
    for field, rule in fields.items():
        item = value[field]
        field_type = rule["type"]
        if field_type == "number":
            valid = type(item) in (int, float) and math.isfinite(item)
        elif field_type == "string":
            valid = isinstance(item, str)
        else:
            valid = False
        if not valid or ("enum" in rule and item not in rule["enum"]):
            raise ValueError(f"invalid study response field: {field}")
    release = float(value["release_cms"])
    bounded = min(max(release, physical["minimum_release_cms"]), physical["maximum_release_cms"])
    return {"schema_version": ACTION_SCHEMA_VERSION, "release_cms": bounded}


class XindianStudyBackend(ConfiguredBackend):
    """Track two prior committed transitions and downstream lateral inflow for unified Feitsui prompts."""

    def __init__(self, study, physical, model, transport, agent_id):
        self._history = deque(maxlen=2)
        self._zhitan_lateral = _load_node_inflows(study, "zhitan_local")
        self._study_prompt = XindianStudyPrompt(
            Path(study["curve"]),
            physical["capacity_m3"],
            physical["minimum_release_cms"],
            physical["maximum_release_cms"],
        )
        system = _system_text(study)
        schema = study["schema"]
        super().__init__(
            agent_id=agent_id,
            mode="llm",
            prompt_spec=PromptSpec(
                strategy_id="xindian_study_feitsui",
                version="2.0",
                template="$study_message",
                system_template=system,
            ),
            knowledge_texts={},
            model=model,
            transport=transport,
            prompt_variables={
                "study_message": lambda context: self._study_prompt.render(
                    context.observation,
                    tuple(self._history),
                    downstream_lateral_cms=self._zhitan_lateral.get(
                        context.observation["timestamp"][:10]
                    ),
                )
            },
            response_json_schema=schema,
            response_parser=lambda value: _parse_release(value, schema, physical),
        )

    def record_transition(self, record):
        super().record_transition(record)
        self._history.append(json_snapshot(record))


def build_backend(
    settings,
    *,
    physical,
    runtime_root,
    mode,
    model,
    transport,
    agent_id,
    context_providers,
):
    return XindianStudyBackend(settings["study"], physical, model, transport, agent_id)
