"""F.E. Walter reference extensions; excluded from the installed general package.

The simulator loads this package only when an example YAML explicitly registers
it. Native policy/profile rules live here; provider transport, journals, physics
and routing remain framework services.
"""
from pathlib import Path

from llm_reservoir_agent.audit import json_snapshot
from .reference_backend import ReferenceBackend, preview_backend, validate_reference
from .dkp_audit import DKPStrategyAudit, DKP_RESPONSE_SCHEMA, validate_dkp_decision
from .seasonal_prompt_context import (
    SeasonalContextBackend, SeasonalPromptContext, SeasonalWindowContext,
    load_seasonal_prompt_context,
)

# Opt in to the framework's source-pinned, lazily constructed prompt callbacks.
supports_prompt_context = True


def validate_backend(spec, *, base_path, runtime_root, physical, mode, days, model, auditor_settings):
    allowed = {"reservoir", "mode", "strategy", "reference", "auditors",
               "prompt_variables", "context_providers"}
    if mode == "llm":
        allowed.add("model")
    if set(spec) - allowed:
        raise ValueError("reference extension accepts native reference settings only")
    if mode == "llm" and model is None:
        raise ValueError("LLM reference requires a known model profile")
    if "native_prompt" in set(spec.get("prompt_variables", {})) | set(spec.get("context_providers", {})):
        raise ValueError("native_prompt is reserved by the FE Walter formatter")
    checks = spec.get("auditors", [])
    if not isinstance(checks, list) or not all(isinstance(a, str) for a in checks):
        raise ValueError("reference auditors must be unique configured IDs")
    if any(auditor_settings[a].get("type") == "dkp_strategy" for a in spec.get("auditors", []) if a in auditor_settings):
        raise ValueError("reference preserves its native audit; generic DKP audit context must not modify its prompt")
    reference, pins, count = validate_reference(
        spec.get("reference"), base_path, runtime_root, mode=mode)
    if physical["reservoir_id"] != reference["profile"]:
        raise ValueError("reference profile must match physical reservoir_id")
    if mode == "offline" and count != days:
        raise ValueError("reference fixture requires one response per selected day")
    return {"reference": reference}, pins


def build_backend(settings, *, physical, runtime_root, mode, model, transport,
                  agent_id="fe_walter", context_providers=None):
    return ReferenceBackend(settings["reference"], physical,
                            runtime_root=runtime_root, mode=mode,
                            model=model, transport=transport, agent_id=agent_id,
                            information=settings.get("information"),
                            prompt_variables=settings.get("prompt_variables"),
                            context_providers=context_providers)


def validate_auditor(settings):
    DKPStrategyAudit.validate_settings(settings)


def build_auditor(identifier, settings, *, base_path, knowledge_paths, runtime_root):
    return DKPStrategyAudit(identifier, settings, base_path=base_path,
                            knowledge_paths=knowledge_paths, project_root=runtime_root)


parser_id = "strict-dkp-decision-json.v1"


def response_instructions(identifier):
    if identifier != DKP_RESPONSE_SCHEMA:
        raise ValueError("unsupported example response contract")
    return ("Return exactly one JSON object with schema_version, release_cms, operating_mode, "
            "rules_applied, missing_inputs, reasoning, applicable_target_ft, pool_position, "
            "intended_storage_direction, release_relation_to_inflow. schema_version must be " + identifier +
            ". release_cms is m3/s; rules_applied and missing_inputs are JSON lists. No Markdown.")


def validate_response_configuration(spec, plugins, *, template):
    if not any(isinstance(p, DKPStrategyAudit) for p in plugins):
        raise ValueError("DKP response_schema requires a configured DKP strategy auditor")
    from string import Template
    if not {"observation", "knowledge"}.issubset(Template(template).get_identifiers()):
        raise ValueError("DKP prompt must include observation and knowledge placeholders")


def parse_response(value):
    decision = validate_dkp_decision(value)
    return {"schema_version": "reservoir-action.v1",
            "release_cms": decision["release_cms"]}, decision


def rebase_agent(spec, *, base_path):
    """Rebase declared native resource files; leave profile IDs and logical data alone."""
    reference = spec.get("reference", {})
    for key in ("system_prompt", "profile_file", "dkp", "responses", "seasonal_criteria_file"):
        if key in reference:
            reference[key] = str((Path(base_path) / reference[key]).resolve())


def rebase_auditor(spec, *, base_path):
    if "profile" in spec:
        spec["profile"] = str((Path(base_path) / spec["profile"]).resolve())
