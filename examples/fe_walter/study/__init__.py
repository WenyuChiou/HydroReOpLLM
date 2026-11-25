"""F.E. Walter study policy integrated with HydroReOpLLM's daily workflow."""

from collections import deque
from hashlib import sha256
import json
import math
from pathlib import Path

from llm_reservoir_agent.audit import json_snapshot
from llm_reservoir_agent.configured_backend import ConfiguredBackend
from llm_reservoir_agent.contracts import ACTION_SCHEMA_VERSION
from llm_reservoir_agent.prompt import PromptSpec

from .formatter import StudyPrompt
from .model import verify_serving


supports_prompt_context = True
CFS_TO_CMS = 0.028316847
_FILES = {
    "seasonal_target": "prompts/seasonal_target.system.txt",
    "dkp": "prompts/dkp.system.txt",
}


def validate_backend(spec, *, base_path, runtime_root, physical, mode, days, model, auditor_settings):
    if set(spec) - {"reservoir", "mode", "model", "strategy", "study_method", "auditors"}:
        raise ValueError("the F.E. Walter study accepts only its fixed prompt design")
    method = spec.get("study_method")
    if method not in _FILES or mode != "llm" or model is None:
        raise ValueError("the study requires a configured seasonal_target or dkp LLM policy")
    if physical["reservoir_id"] != "fe_walter" or physical["dt_seconds"] != 86_400:
        raise ValueError("the study policy requires the daily F.E. Walter physical case")
    root = Path(__file__).resolve().parents[1]
    system = root / _FILES[method]
    curve = root / "study/elevation_storage.csv"
    schemas = root / "study/response_schemas.json"
    dkp = root / "dkp.md" if method == "dkp" else None
    pins = {str(path): sha256(path.read_bytes()).hexdigest()
            for path in (system, curve, schemas, dkp) if path is not None}
    schema = json.loads(schemas.read_text(encoding="utf-8"))[method]
    return {"study": {"method": method, "system": str(system), "curve": str(curve),
                      "dkp": None if dkp is None else str(dkp), "schema": schema}}, pins


def preview_backend(settings, physical, runtime_root):
    study = settings["study"]
    return {"kind": "config_preview", "model_used": False,
            "messages": [{"role": "system", "content": _system_text(study)}],
            "response_json_schema": study["schema"]}


def _system_text(study):
    return Path(study["system"]).read_text(encoding="utf-8")


def _parse_release(value, schema, physical):
    fields = schema["properties"]
    if not isinstance(value, dict) or value.keys() != fields.keys():
        raise ValueError("the model response does not match the F.E. Walter study fields")
    for field, rule in fields.items():
        item = value[field]
        field_type = rule["type"]
        if field_type == "number":
            valid = type(item) in (int, float) and math.isfinite(item)
        elif field_type == "string":
            valid = isinstance(item, str)
        else:
            valid = isinstance(item, list) and all(isinstance(entry, str) for entry in item)
        if not valid or ("enum" in rule and item not in rule["enum"]):
            raise ValueError(f"invalid study response field: {field}")
    release = value["release_cfs"] * CFS_TO_CMS
    bounded = min(max(release, physical["minimum_release_cms"]), physical["maximum_release_cms"])
    return {"schema_version": ACTION_SCHEMA_VERSION, "release_cms": bounded}


class StudyBackend(ConfiguredBackend):
    """Track the two committed transitions used by the paper's next request."""

    def __init__(self, study, physical, model, transport, agent_id):
        self._history = deque(maxlen=2)
        dkp = None if study["dkp"] is None else Path(study["dkp"])
        self._study_prompt = StudyPrompt(Path(study["curve"]), dkp)
        system = _system_text(study)
        schema = study["schema"]
        super().__init__(
            agent_id=agent_id, mode="llm",
            prompt_spec=PromptSpec(strategy_id=f"walter_study_{study['method']}",
                                   version="3.7", template="$study_message", system_template=system),
            knowledge_texts={}, model=model, transport=transport,
            prompt_variables={"study_message": lambda context:
                              self._study_prompt.render(context.observation, tuple(self._history))},
            response_json_schema=schema,
            response_parser=lambda value: _parse_release(value, schema, physical),
        )

    def record_transition(self, record):
        super().record_transition(record)
        self._history.append(json_snapshot(record))


def build_backend(settings, *, physical, runtime_root, mode, model, transport, agent_id,
                  context_providers):
    return StudyBackend(settings["study"], physical, model, transport, agent_id)
