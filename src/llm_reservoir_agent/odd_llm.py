"""ODD+LLM (CoALA-grounded ABM extension) reproducibility manifest, Markdown report, and CLI export.

Role: Persist, render, and export deterministic five-block ODD+LLM artifacts
(Blocks A-E) from completed HydroReOpLLM runs without performing model inference
or modifying physical outputs.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import csv
import importlib.metadata
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .audit import json_snapshot
from .time_axis import TimeAxis


ODD_LLM_SCHEMA_VERSION = "odd-llm-reproducibility.v1"
ODD_LLM_PROTOCOL = "ODD+LLM (CoALA-grounded ABM extension)"
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_SAFE_FALLBACK_MODEL_FIELDS = (
    "provider",
    "model",
    "base_url",
    "temperature",
    "seed",
    "max_tokens",
    "num_ctx",
    "think",
    "keep_alive",
    "max_attempts",
    "retry_delay_seconds",
    "timeout_seconds",
    "api_key_env",
    "retryable_http_statuses",
    "anthropic_version",
)
_SYSTEM_PREVIEW_MAX_CHARS = 240


def _package_version() -> str:
    """Return installed hydroreopllm version with a safe static fallback."""
    try:
        return importlib.metadata.version("hydroreopllm")
    except Exception:
        return "0.1.1"


def _sanitize_path(value: Any) -> str | None:
    """Return a clean relative path or basename, never leaking host absolute paths."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    win = PureWindowsPath(text)
    posix = PurePosixPath(text)
    if (
        win.is_absolute()
        or posix.is_absolute()
        or re.match(r"^[A-Za-z]:", text) is not None
        or text.startswith("\\\\")
    ):
        if "\\" in text or re.match(r"^[A-Za-z]:", text) is not None:
            return win.name or None
        return posix.name or None
    parts = [part for part in PurePosixPath(text.replace("\\", "/")).parts if part not in ("", ".")]
    if not parts:
        return None
    if ".." in parts:
        last_up = max(idx for idx, part in enumerate(parts) if part == "..")
        tail = parts[last_up + 1 :]
        return "/".join(tail) if tail else None
    return "/".join(parts)


def _sanitize_base_url(value: Any) -> str | None:
    """Preserve HTTP(S) base URL while stripping any accidental embedded credentials."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    parsed = urlsplit(text)
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        netloc = parsed.hostname
        if parsed.port is not None:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    return None


def _sanitize_env_name(value: Any) -> str | None:
    """Keep only valid environment variable identifiers, never raw secrets."""
    if isinstance(value, str) and _ENV_NAME.fullmatch(value):
        return value
    return None


def _sanitize_model_entry(model: Any) -> dict[str, Any] | None:
    """Extract only safe, non-secret model configuration fields."""
    if not isinstance(model, Mapping):
        return None
    out: dict[str, Any] = {}
    for field in _SAFE_FALLBACK_MODEL_FIELDS:
        if field not in model:
            continue
        val = model[field]
        if field == "base_url":
            out[field] = _sanitize_base_url(val)
        elif field == "api_key_env":
            out[field] = _sanitize_env_name(val)
        else:
            out[field] = val
    return out


def _truncate_preview(text: Any, max_chars: int = _SYSTEM_PREVIEW_MAX_CHARS) -> str | None:
    """Return a single-line bounded preview of prompt text, or None if unavailable."""
    if not isinstance(text, str):
        return None
    collapsed = " ".join(text.split())
    if not collapsed:
        return None
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 3].rstrip() + "..."


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL stream if it exists, returning parsed mapping records."""
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if isinstance(item, dict):
            events.append(item)
    return events


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read CSV rows if the file exists."""
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_child_json(root: Path, relative: Any) -> Any:
    """Read a JSON file contained inside root, returning None on missing or escaping paths."""
    if not isinstance(relative, str) or not relative.strip():
        return None
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_system_message(messages: Any) -> str | None:
    """Find the first non-empty system message content in a role/content list."""
    if not isinstance(messages, list):
        return None
    for message in messages:
        if isinstance(message, Mapping) and message.get("role") == "system":
            preview = _truncate_preview(message.get("content"))
            if preview is not None:
                return preview
    return None


def _resolve_agent_type(
    res_spec: Mapping[str, Any],
    backend_prov: Mapping[str, Any],
    agent_id: str | None,
    plan: Mapping[str, Any],
) -> str:
    """Classify a reservoir agent as 'llm', 'rule_based', or 'passive_outlet'."""
    if (
        res_spec.get("operation_mode") == "passive_outlet"
        or backend_prov.get("provider") == "physical"
        or backend_prov.get("operation_mode") == "passive_outlet"
    ):
        return "passive_outlet"
    plan_types = plan.get("agent_types")
    if isinstance(plan_types, Mapping) and agent_id in plan_types:
        declared = plan_types[agent_id]
        if declared in {"llm", "rule_based"}:
            return declared
    backend_kind = backend_prov.get("backend")
    if backend_kind in {"hanasaki_benchmark", "rule_based"}:
        return "rule_based"
    if backend_prov.get("data_kind") == "recorded_llm_response":
        return "llm"
    if backend_prov.get("model_used") is True or backend_prov.get("mode") == "llm":
        return "llm"
    return "rule_based"


def _resolve_strategy(
    agent_type: str,
    agent_id: str | None,
    agent_spec: Mapping[str, Any],
    backend_prov: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> str:
    """Determine the declared or inferred strategy label for one reservoir."""
    if agent_type == "passive_outlet":
        return "passive_outlet"
    plan_strategies = plan.get("agent_strategies")
    if isinstance(plan_strategies, Mapping) and agent_id in plan_strategies:
        value = plan_strategies[agent_id]
        if isinstance(value, str) and value.strip():
            return value
    if isinstance(agent_spec.get("strategy"), str) and agent_spec["strategy"].strip():
        return agent_spec["strategy"]
    if isinstance(backend_prov.get("backend"), str) and backend_prov["backend"].strip():
        return backend_prov["backend"]
    if isinstance(backend_prov.get("data_kind"), str) and backend_prov["data_kind"].strip():
        return backend_prov["data_kind"]
    return "custom"


def _is_offline_only(
    agent_type: str,
    agent_spec: Mapping[str, Any],
    backend_prov: Mapping[str, Any],
) -> bool:
    """Return True when this reservoir does not invoke live LLM network transport."""
    if agent_type in {"passive_outlet", "rule_based"}:
        return True
    if agent_spec.get("mode") == "offline":
        return True
    if backend_prov.get("data_kind") in {"recorded_llm_response", "synthetic_fixture"}:
        return True
    if backend_prov.get("model_used") is False or backend_prov.get("network_enabled") is False:
        return True
    return False


def _decision_loop_label(agent_type: str, offline_only: bool) -> str:
    if agent_type == "passive_outlet":
        return "implicit_backward_euler_rating -> host_physics -> causal_routing"
    if agent_type == "rule_based":
        return "observe -> deterministic_rule -> audit -> host_physics -> commit_feedback"
    if offline_only:
        return "observe -> replay_recorded_action -> audit -> host_physics -> commit_feedback"
    return "observe -> render_prompt -> llm_inference -> parse_action -> audit -> host_physics -> commit_feedback"


def _extract_knowledge(
    agent_spec: Mapping[str, Any],
    backend_prov: Mapping[str, Any],
    first_decision: Mapping[str, Any] | None,
    settings: Mapping[str, Any],
) -> dict[str, Any]:
    """Collect long-term knowledge package IDs and SHA-256 digests."""
    sha_map: dict[str, str] = {}
    ordered_ids: list[str] = []

    def add_pair(pkg_id: Any, digest: Any) -> None:
        if isinstance(pkg_id, str) and pkg_id.strip():
            if pkg_id not in ordered_ids:
                ordered_ids.append(pkg_id)
            if isinstance(digest, str) and digest.strip():
                sha_map[pkg_id] = digest

    # 1. Backend provenance declarations
    prov_ids = backend_prov.get("knowledge_package_ids")
    prov_hashes = backend_prov.get("knowledge_package_sha256")
    if isinstance(prov_ids, list):
        for pkg_id in prov_ids:
            digest = prov_hashes.get(pkg_id) if isinstance(prov_hashes, Mapping) else None
            add_pair(pkg_id, digest)
    if isinstance(prov_hashes, Mapping):
        for pkg_id, digest in prov_hashes.items():
            add_pair(pkg_id, digest)

    nested_knowledge = backend_prov.get("knowledge")
    if isinstance(nested_knowledge, Mapping):
        nested_ids = nested_knowledge.get("package_ids")
        nested_sha = nested_knowledge.get("sha256")
        if isinstance(nested_ids, list):
            for pkg_id in nested_ids:
                digest = nested_sha.get(pkg_id) if isinstance(nested_sha, Mapping) else None
                add_pair(pkg_id, digest)
        if isinstance(nested_sha, Mapping):
            for pkg_id, digest in nested_sha.items():
                add_pair(pkg_id, digest)

    # 2. First decision provenance fallback
    if isinstance(first_decision, Mapping):
        dec_prov = first_decision.get("provenance")
        if isinstance(dec_prov, Mapping):
            dec_ids = dec_prov.get("knowledge_package_ids")
            dec_hashes = dec_prov.get("knowledge_package_sha256")
            if isinstance(dec_ids, list):
                for pkg_id in dec_ids:
                    digest = dec_hashes.get(pkg_id) if isinstance(dec_hashes, Mapping) else None
                    add_pair(pkg_id, digest)
            if isinstance(dec_hashes, Mapping):
                for pkg_id, digest in dec_hashes.items():
                    add_pair(pkg_id, digest)

    # 3. Study-specific DKP source dependency when knowledge_texts is externalized
    source_deps = settings.get("source_dependencies")
    if isinstance(source_deps, Mapping) and agent_spec.get("study_method") == "dkp":
        for dep_key, digest in source_deps.items():
            clean = _sanitize_path(dep_key)
            if clean and clean.lower().endswith("dkp.md"):
                add_pair("dkp.md", digest)

    return {
        "package_ids": ordered_ids,
        "sha256": {pkg_id: sha_map[pkg_id] for pkg_id in ordered_ids if pkg_id in sha_map},
    }


def _extract_prompt_files(
    agent_spec: Mapping[str, Any],
    settings: Mapping[str, Any],
    total_llm_agents: int,
) -> tuple[str | None, str | None]:
    """Return sanitized (system_prompt_file, user_prompt_file) relative names."""
    system_file: str | None = None
    user_file: str | None = None
    prompt_cfg = agent_spec.get("prompt")
    if isinstance(prompt_cfg, str):
        user_file = _sanitize_path(prompt_cfg)
    elif isinstance(prompt_cfg, Mapping):
        system_file = _sanitize_path(prompt_cfg.get("system"))
        user_file = _sanitize_path(prompt_cfg.get("user"))

    if system_file is None:
        source_deps = settings.get("source_dependencies")
        if isinstance(source_deps, Mapping):
            method = agent_spec.get("study_method")
            candidates = []
            for key in source_deps:
                clean = _sanitize_path(key)
                if clean and clean.lower().endswith(".system.txt"):
                    candidates.append(clean)
            if isinstance(method, str) and method:
                matched = [c for c in candidates if method.lower() in c.lower()]
                if len(matched) == 1:
                    system_file = matched[0]
            elif len(candidates) == 1 and total_llm_agents == 1:
                system_file = candidates[0]

    return system_file, user_file


def _resolve_coupled_dir(output_dir: Path | str) -> Path:
    """Resolve either a coupled preparation root (preparation.json -> operation/) or flat run dir."""
    root = Path(output_dir)
    prep = root / "preparation.json"
    if prep.is_file():
        if any((root / name).exists() for name in ("summary.json", "index.json", "experiment.json")):
            raise ValueError("ambiguous flat and coupled run directory")
        operation = root / "operation"
        if not operation.is_dir():
            raise FileNotFoundError(f"coupled run directory has no operation/ folder: {root}")
        return operation
    return root


def build_odd_llm_manifest(
    output_dir: Path | str,
    *,
    experiment: Mapping[str, Any] | None = None,
    summary: Mapping[str, Any] | None = None,
    streams_dir: Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic, finite-JSON ODD+LLM reproducibility manifest (Blocks A-E).

    Parameters
    ----------
    output_dir : Path or str
        Run output directory containing ``experiment.json`` and output tables.
    experiment : Mapping or None, optional
        Already loaded ``experiment.json`` metadata; read from ``output_dir`` when omitted.
    summary : Mapping or None, optional
        Run summary dict (either inner summary or full ``summary.json``); read from ``output_dir`` when omitted.
    streams_dir : Path or None, optional
        Directory holding JSONL trace streams; defaults to ``output_dir``.

    Returns
    -------
    dict[str, Any]
        Deterministic finite-JSON manifest conforming to ``odd-llm-reproducibility.v1``.
    """
    output_path = Path(output_dir)
    streams_root = Path(streams_dir) if streams_dir is not None else output_path

    if experiment is None:
        exp_data: Mapping[str, Any] = json.loads((output_path / "experiment.json").read_text(encoding="utf-8"))
    else:
        exp_data = experiment

    summary_data: Mapping[str, Any]
    if summary is None:
        summary_file = output_path / "summary.json"
        if summary_file.is_file():
            loaded_summary = json.loads(summary_file.read_text(encoding="utf-8"))
            summary_data = (
                loaded_summary.get("summary", loaded_summary)
                if isinstance(loaded_summary, Mapping)
                else {}
            )
        else:
            summary_data = {}
    else:
        if (
            "summary" in summary
            and "streams" in summary
            and isinstance(summary.get("summary"), Mapping)
        ):
            summary_data = summary["summary"]
        else:
            summary_data = summary

    decisions = _read_jsonl(streams_root / "decisions.jsonl")
    physics_events = _read_jsonl(streams_root / "physics.jsonl")
    audits = _read_jsonl(streams_root / "audit.jsonl")
    _backend_events = _read_jsonl(streams_root / "backend_events.jsonl")
    provider_attempts = _read_jsonl(streams_root / "provider_attempts.jsonl")

    traj_path = output_path / "reservoir_trajectory.csv"
    if not traj_path.is_file() and streams_root != output_path:
        traj_path = streams_root / "reservoir_trajectory.csv"
    trajectory_rows = _read_csv_rows(traj_path)

    run_id = str(exp_data.get("run_id") or "")
    network = exp_data.get("network") or {}
    rows = exp_data.get("inflow_records") or []
    clock = TimeAxis.from_network(network)
    if rows:
        start_label = rows[0].get(clock.key)
        end_label = rows[-1].get(clock.key)
    else:
        start_label = network.get("start_date") if clock.legacy_daily else network.get("start_time")
        end_label = start_label

    time_axis = {
        "step_type": "daily" if clock.legacy_daily else "interval",
        "dt_seconds": float(clock.dt_seconds),
        "start": start_label,
        "end": end_label,
        "steps": len(rows),
    }

    provenance = exp_data.get("provenance") if isinstance(exp_data.get("provenance"), Mapping) else {}
    plan = provenance.get("plan") if isinstance(provenance.get("plan"), Mapping) else {}
    settings = provenance.get("settings") if isinstance(provenance.get("settings"), Mapping) else {}
    settings_agents = settings.get("agents") if isinstance(settings.get("agents"), Mapping) else {}
    settings_models = settings.get("models") if isinstance(settings.get("models"), Mapping) else {}
    prompt_previews = plan.get("prompt_previews") if isinstance(plan.get("prompt_previews"), Mapping) else {}
    backend_provenance_all = (
        exp_data.get("backend_provenance") if isinstance(exp_data.get("backend_provenance"), Mapping) else {}
    )
    info_config = (
        exp_data.get("information_config") if isinstance(exp_data.get("information_config"), Mapping) else {}
    )
    info_bindings = info_config.get("bindings") if isinstance(info_config.get("bindings"), Mapping) else {}

    source_files_map = provenance.get("source_files")
    if not isinstance(source_files_map, Mapping):
        source_files_map = plan.get("source_files")
    if not isinstance(source_files_map, Mapping):
        source_files_map = network.get("source_files")
    pinned_count = len(source_files_map) if isinstance(source_files_map, Mapping) else 0

    # Map reservoir name -> (agent_id, agent_spec)
    reservoir_to_agent: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for aid, aspec in settings_agents.items():
        if isinstance(aspec, Mapping) and isinstance(aspec.get("reservoir"), str):
            reservoir_to_agent[aspec["reservoir"]] = (str(aid), aspec)

    # First decision per physical reservoir_id
    first_decision_by_rid: dict[str, dict[str, Any]] = {}
    for event in decisions:
        rid = event.get("reservoir_id")
        if isinstance(rid, str) and rid not in first_decision_by_rid:
            first_decision_by_rid[rid] = event

    reservoirs = network.get("reservoirs") if isinstance(network.get("reservoirs"), Mapping) else {}

    # Pre-classify agent types so prompt file inference knows how many LLM agents exist
    pre_types: dict[str, str] = {}
    for res_name, res_spec in reservoirs.items():
        backend_prov = backend_provenance_all.get(res_name)
        backend_prov = backend_prov if isinstance(backend_prov, Mapping) else {}
        agent_id_pair = reservoir_to_agent.get(res_name)
        agent_id = agent_id_pair[0] if agent_id_pair else backend_prov.get("agent_id")
        pre_types[res_name] = _resolve_agent_type(res_spec, backend_prov, agent_id, plan)
    total_llm_agents = sum(1 for t in pre_types.values() if t == "llm")

    block_a: dict[str, Any] = {}
    block_b: dict[str, Any] = {}
    block_c_agents: dict[str, Any] = {}
    block_d_signature: dict[str, Any] = {}
    block_d_binding: dict[str, Any] = {}

    live_llm_rids: set[str] = set()
    llm_rids: set[str] = set()

    for res_name, res_spec in reservoirs.items():
        physical = res_spec.get("physical") if isinstance(res_spec.get("physical"), Mapping) else {}
        reservoir_id = str(physical.get("reservoir_id") or res_name)
        backend_prov = backend_provenance_all.get(res_name)
        backend_prov = backend_prov if isinstance(backend_prov, Mapping) else {}
        agent_id_pair = reservoir_to_agent.get(res_name)
        agent_spec: Mapping[str, Any] = agent_id_pair[1] if agent_id_pair else {}
        agent_type = pre_types[res_name]
        if agent_id_pair is not None:
            agent_id: str | None = agent_id_pair[0]
        elif isinstance(backend_prov.get("agent_id"), str) and backend_prov["agent_id"].strip():
            agent_id = backend_prov["agent_id"]
        else:
            agent_id = None if agent_type == "passive_outlet" else res_name

        strategy = _resolve_strategy(agent_type, agent_id, agent_spec, backend_prov, plan)
        offline_only = _is_offline_only(agent_type, agent_spec, backend_prov)
        if agent_type == "llm":
            llm_rids.add(reservoir_id)
            if not offline_only:
                live_llm_rids.add(reservoir_id)

        first_dec = first_decision_by_rid.get(reservoir_id)
        first_dec_prov = (
            first_dec.get("provenance")
            if isinstance(first_dec, Mapping) and isinstance(first_dec.get("provenance"), Mapping)
            else {}
        )
        raw_trace: Any = None
        if isinstance(first_dec, Mapping) and isinstance(first_dec.get("raw_policy_ref"), Mapping):
            raw_trace = _safe_child_json(output_path, first_dec["raw_policy_ref"].get("path"))
            if raw_trace is None and streams_root != output_path:
                raw_trace = _safe_child_json(streams_root, first_dec["raw_policy_ref"].get("path"))
        unwrapped_raw = (
            raw_trace.get("backend_trace", raw_trace) if isinstance(raw_trace, Mapping) else None
        )

        # Working memory
        raw_history = backend_prov.get("history_steps", agent_spec.get("history_steps", 0))
        history_steps = int(raw_history) if isinstance(raw_history, int) and not isinstance(raw_history, bool) else 0
        previous_transition_included = bool(
            history_steps > 0
            or backend_prov.get("backend") == "configured"
            or (isinstance(unwrapped_raw, Mapping) and "previous_feedback" in unwrapped_raw)
        )

        long_term_knowledge = _extract_knowledge(agent_spec, backend_prov, first_dec, settings)

        info_profile = info_bindings.get(res_name)
        if info_profile is None:
            info_profile = agent_spec.get("information")
        if info_profile is None and agent_id is not None:
            plan_info = plan.get("information_bindings")
            if isinstance(plan_info, Mapping):
                info_profile = plan_info.get(agent_id)

        # Block A
        block_a[res_name] = {
            "reservoir_id": reservoir_id,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "strategy": strategy,
            "working_memory": {
                "history_steps": history_steps,
                "previous_transition_included": previous_transition_included,
            },
            "long_term_knowledge": long_term_knowledge,
            "information_profile": info_profile,
            "action_space": {
                "minimum_release_cms": float(physical.get("minimum_release_cms", 0.0)),
                "maximum_release_cms": float(physical.get("maximum_release_cms", 0.0)),
                "dead_storage_m3": float(physical.get("dead_storage_m3", 0.0)),
                "capacity_m3": float(physical.get("capacity_m3", 0.0)),
                "unit": "m3/s",
            },
            "decision_loop": _decision_loop_label(agent_type, offline_only),
        }

        # Block B
        prompt_meta = backend_prov.get("prompt") if isinstance(backend_prov.get("prompt"), Mapping) else {}
        prompt_id = backend_prov.get("prompt_id") or first_dec_prov.get("prompt_id")
        prompt_strategy_id = (
            backend_prov.get("prompt_strategy_id")
            or prompt_meta.get("strategy_id")
            or first_dec_prov.get("prompt_strategy_id")
        )
        prompt_version = (
            backend_prov.get("prompt_version")
            or prompt_meta.get("version")
            or agent_spec.get("prompt_version")
            or first_dec_prov.get("prompt_version")
        )
        prompt_sha256 = (
            backend_prov.get("prompt_sha256")
            or prompt_meta.get("template_sha256")
            or first_dec_prov.get("prompt_sha256")
        )
        system_file, user_file = _extract_prompt_files(agent_spec, settings, total_llm_agents)

        system_preview: str | None = None
        if agent_id is not None and isinstance(prompt_previews.get(agent_id), Mapping):
            system_preview = _extract_system_message(prompt_previews[agent_id].get("messages"))
        if system_preview is None and isinstance(unwrapped_raw, Mapping):
            system_preview = _extract_system_message(unwrapped_raw.get("messages"))

        block_b[res_name] = {
            "agent_id": agent_id,
            "reservoir_id": reservoir_id,
            "prompt_id": prompt_id,
            "prompt_strategy_id": prompt_strategy_id,
            "prompt_version": prompt_version,
            "prompt_sha256": prompt_sha256,
            "system_prompt_file": system_file,
            "user_prompt_file": user_file,
            "system_prompt_preview": system_preview,
            "source_files_pinned_count": pinned_count,
        }

        # Block C (per-reservoir inference profile)
        raw_model = backend_prov.get("model")
        if raw_model is None and isinstance(agent_spec.get("model"), str):
            raw_model = settings_models.get(agent_spec["model"])
        safe_model = _sanitize_model_entry(raw_model) or {}

        raw_fallbacks = backend_prov.get("fallback_models")
        if raw_fallbacks is None and isinstance(agent_spec.get("fallback_models"), list):
            raw_fallbacks = [
                settings_models[key]
                for key in agent_spec["fallback_models"]
                if isinstance(key, str) and key in settings_models
            ]
        safe_fallbacks: list[dict[str, Any]] = []
        if isinstance(raw_fallbacks, list):
            for item in raw_fallbacks:
                cleaned = _sanitize_model_entry(item)
                if cleaned is not None:
                    safe_fallbacks.append(cleaned)

        max_attempts_val = safe_model.get("max_attempts")
        agent_auto_retry = bool(
            (isinstance(max_attempts_val, int) and not isinstance(max_attempts_val, bool) and max_attempts_val > 1)
            or (not offline_only and bool(exp_data.get("automatic_retry", False)))
        )

        block_c_agents[res_name] = {
            "provider": safe_model.get("provider"),
            "model": safe_model.get("model"),
            "base_url": safe_model.get("base_url"),
            "temperature": safe_model.get("temperature"),
            "seed": safe_model.get("seed"),
            "max_tokens": safe_model.get("max_tokens"),
            "num_ctx": safe_model.get("num_ctx"),
            "think": safe_model.get("think"),
            "keep_alive": safe_model.get("keep_alive"),
            "max_attempts": max_attempts_val,
            "retry_delay_seconds": safe_model.get("retry_delay_seconds"),
            "api_key_env": safe_model.get("api_key_env"),
            "fallback_models": safe_fallbacks,
            "automatic_retry": agent_auto_retry,
            "offline_only": offline_only,
        }

        # Block D signature & binding
        if isinstance(first_dec, Mapping) and isinstance(first_dec.get("observation"), Mapping):
            obs_fields = sorted(str(k) for k in first_dec["observation"].keys())
        else:
            obs_fields = [
                "context",
                "inflow_cms",
                "release_upper_bound_cms",
                "state",
                "timestamp",
                "timestep",
            ]
        parser_meta = backend_prov.get("parser") if isinstance(backend_prov.get("parser"), Mapping) else {}
        response_schema = (
            parser_meta.get("schema_version")
            or agent_spec.get("response_schema")
            or "reservoir-action.v1"
        )
        response_parser_id = backend_prov.get("response_parser_id") or first_dec_prov.get("response_parser_id")
        auditor_specs = backend_prov.get("auditor_specs")
        if auditor_specs is None:
            auditor_specs = first_dec_prov.get("auditor_specs")
        if not isinstance(auditor_specs, list):
            auditor_specs = []

        block_d_signature[res_name] = {
            "observation_fields": obs_fields,
            "response_schema": response_schema,
            "response_parser_id": response_parser_id,
            "auditor_specs": auditor_specs,
        }

        context_providers_raw = backend_prov.get("context_provider_ids")
        if not isinstance(context_providers_raw, list):
            spec_cp = agent_spec.get("context_providers")
            context_providers_raw = list(spec_cp.keys()) if isinstance(spec_cp, Mapping) else []
        context_provider_names = sorted(str(name) for name in context_providers_raw)

        prompt_var_set: set[str] = set()
        spec_pv = agent_spec.get("prompt_variables")
        if isinstance(spec_pv, Mapping):
            prompt_var_set.update(str(k) for k in spec_pv.keys())
        if isinstance(unwrapped_raw, Mapping) and isinstance(unwrapped_raw.get("context_provenance"), Mapping):
            for key in unwrapped_raw["context_provenance"].keys():
                if str(key) not in context_provider_names:
                    prompt_var_set.add(str(key))

        block_d_binding[res_name] = {
            "history_steps": history_steps,
            "information_profile": info_profile,
            "prompt_variable_names": sorted(prompt_var_set),
            "context_provider_names": context_provider_names,
            "knowledge_package_ids": list(long_term_knowledge["package_ids"]),
        }

    # Block C runtime metadata
    hydrocnhs_core = exp_data.get("hydrocnhs_core")
    hydrocnhs_commit = (
        hydrocnhs_core.get("hydrocnhs_commit")
        if isinstance(hydrocnhs_core, Mapping)
        else None
    )
    block_c = {
        "runtime": {
            "python_version": exp_data.get("python") or platform.python_version(),
            "platform": platform.platform(),
            "hydroreopllm_version": _package_version(),
            "hydrocnhs_core_commit": hydrocnhs_commit,
            "abm_module_sha256": exp_data.get("abm_module_sha256"),
        },
        "agents": block_c_agents,
    }

    # Block D empirical resolution telemetry
    total_decisions = len(decisions) if decisions else len(trajectory_rows)
    provider_attempt_events = len(provider_attempts)
    provider_started_attempts = sum(1 for e in provider_attempts if e.get("status") == "STARTED")
    provider_failed_attempts = sum(1 for e in provider_attempts if e.get("status") == "FAILED")

    target_llm_rids = live_llm_rids if live_llm_rids else llm_rids
    total_llm_decisions = sum(1 for d in decisions if d.get("reservoir_id") in target_llm_rids)
    retry_attempts = max(0, provider_started_attempts - total_llm_decisions) if provider_started_attempts > 0 else 0

    observed_calls = summary_data.get("observed_network_calls")
    if observed_calls is None and provider_started_attempts > 0:
        observed_calls = provider_started_attempts

    serving_profiles = summary_data.get("serving_profiles")
    if not isinstance(serving_profiles, Mapping):
        computed_serving: dict[str, dict[str, int]] = {}
        for d in decisions:
            served = d.get("served_by")
            rid = d.get("reservoir_id")
            if isinstance(served, Mapping) and isinstance(rid, str) and "profile" in served:
                bucket = computed_serving.setdefault(rid, {})
                pkey = str(served["profile"])
                bucket[pkey] = bucket.get(pkey, 0) + 1
        serving_profiles = {
            rid: dict(sorted(row.items(), key=lambda item: int(item[0])))
            for rid, row in computed_serving.items()
        }
    else:
        serving_profiles = {str(k): dict(v) for k, v in serving_profiles.items()}

    if "fallback_served_decisions" in summary_data and isinstance(summary_data["fallback_served_decisions"], int):
        fallback_served = int(summary_data["fallback_served_decisions"])
    else:
        fallback_served = sum(
            int(count)
            for row in serving_profiles.values()
            for profile, count in row.items()
            if str(profile) != "0"
        )
    fallback_used = bool(summary_data.get("fallback_used", fallback_served > 0))

    if trajectory_rows:
        traj_total = len(trajectory_rows)
        physical_clipping_steps = sum(
            1
            for row in trajectory_rows
            if (row.get("adjustments") or "").strip() not in ("", "[]")
        )
        spill_steps = sum(
            1
            for row in trajectory_rows
            if math.isfinite(float(row.get("spill_cms") or 0.0)) and float(row.get("spill_cms") or 0.0) > 0.0
        )
    else:
        traj_total = len(physics_events)
        physical_clipping_steps = sum(
            1
            for event in physics_events
            if bool(((event.get("record") or {}).get("transition") or {}).get("adjustments"))
        )
        spill_steps = sum(
            1
            for event in physics_events
            if float(((event.get("record") or {}).get("transition") or {}).get("spill_cms") or 0.0) > 0.0
        )

    physical_clipping_rate = round(physical_clipping_steps / traj_total, 6) if traj_total > 0 else 0.0

    raw_audit_counts = summary_data.get("audit_counts")
    if isinstance(raw_audit_counts, Mapping):
        audit_counts = {str(k): int(v) for k, v in sorted(raw_audit_counts.items())}
    else:
        counted = Counter(str(event.get("status", "UNKNOWN")) for event in audits)
        audit_counts = {k: int(v) for k, v in sorted(counted.items())}

    block_d = {
        "signature": block_d_signature,
        "binding": block_d_binding,
        "resolution": {
            "total_decisions": total_decisions,
            "observed_network_calls": observed_calls,
            "provider_attempt_events": provider_attempt_events,
            "provider_started_attempts": provider_started_attempts,
            "provider_failed_attempts": provider_failed_attempts,
            "retry_attempts": retry_attempts,
            "fallback_served_decisions": fallback_served,
            "fallback_used": fallback_used,
            "serving_profiles": serving_profiles,
            "physical_clipping_steps": physical_clipping_steps,
            "physical_clipping_rate": physical_clipping_rate,
            "spill_steps": spill_steps,
            "audit_counts": audit_counts,
        },
    }

    # Block E validation
    output_files_sha = summary_data.get("output_files")
    output_files_sha256 = (
        {str(k): str(v) for k, v in output_files_sha.items()}
        if isinstance(output_files_sha, Mapping)
        else {}
    )
    provider_attempts_sha = summary_data.get("provider_attempts_sha256")
    all_offline = all(agent_c["offline_only"] for agent_c in block_c_agents.values())
    llm_decisions_with_raw = [
        d for d in decisions if d.get("reservoir_id") in live_llm_rids
    ]
    offline_replay_capable = bool(
        all_offline
        or provider_attempts_sha is not None
        or (
            bool(llm_decisions_with_raw)
            and all("raw_policy_ref" in d for d in llm_decisions_with_raw)
        )
    )

    max_mass_residual = summary_data.get("max_mass_balance_residual_m3")
    if max_mass_residual is None and trajectory_rows:
        residuals = [
            abs(float(r["mass_balance_residual_m3"]))
            for r in trajectory_rows
            if r.get("mass_balance_residual_m3") not in (None, "")
        ]
        max_mass_residual = max(residuals) if residuals else None

    final_storage = summary_data.get("final_storage_m3")
    final_storage_m3 = (
        {str(k): float(v) for k, v in final_storage.items()}
        if isinstance(final_storage, Mapping)
        else {}
    )

    block_e = {
        "verification_command": "reservoir-experiment verify <output>",
        "max_mass_balance_residual_m3": max_mass_residual,
        "max_system_balance_residual_m3": summary_data.get("max_system_balance_residual_m3"),
        "final_storage_m3": final_storage_m3,
        "output_files_sha256": output_files_sha256,
        "provider_attempts_sha256": provider_attempts_sha,
        "offline_replay_capable": offline_replay_capable,
    }

    manifest = {
        "schema_version": ODD_LLM_SCHEMA_VERSION,
        "protocol": ODD_LLM_PROTOCOL,
        "run_id": run_id,
        "time_axis": time_axis,
        "blocks": {
            "A_cognitive_architecture": block_a,
            "B_identity": block_b,
            "C_inference_configuration": block_c,
            "D_behavioral_submodel": block_d,
            "E_validation": block_e,
        },
    }
    return json_snapshot(manifest, label="odd_llm_manifest")


def _fmt(value: Any) -> str:
    """Format a scalar value concisely for Markdown tables."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value == 0.0:
            return "0"
        if abs(value) < 1e-4 or abs(value) >= 1e7:
            return f"{value:.3e}"
        return f"{value:g}"
    return str(value)


def render_odd_llm_markdown(manifest: Mapping[str, Any]) -> str:
    """Render a concise, publication-ready ODD+LLM Markdown report from a manifest."""
    run_id = manifest.get("run_id") or "unknown"
    schema_version = manifest.get("schema_version") or ODD_LLM_SCHEMA_VERSION
    protocol = manifest.get("protocol") or ODD_LLM_PROTOCOL
    axis = manifest.get("time_axis") or {}
    blocks = manifest.get("blocks") or {}
    block_a = blocks.get("A_cognitive_architecture") or {}
    block_b = blocks.get("B_identity") or {}
    block_c = blocks.get("C_inference_configuration") or {}
    block_d = blocks.get("D_behavioral_submodel") or {}
    block_e = blocks.get("E_validation") or {}

    runtime = block_c.get("runtime") or {}
    c_agents = block_c.get("agents") or {}
    d_sig = block_d.get("signature") or {}
    d_bind = block_d.get("binding") or {}
    d_res = block_d.get("resolution") or {}

    lines: list[str] = [
        f"# ODD+LLM Reproducibility Report: `{run_id}`",
        "",
        f"- **Protocol**: {protocol}",
        f"- **Schema Version**: `{schema_version}`",
        f"- **Time Axis**: `{axis.get('step_type', 'unknown')}` · "
        f"`dt = {_fmt(axis.get('dt_seconds'))} s` · "
        f"`{axis.get('start')}` to `{axis.get('end')}` (`{axis.get('steps', 0)}` steps)",
        "",
        "## Agents Summary",
        "",
        "| Reservoir | Reservoir ID | Agent ID | Type | Strategy | Model | Info Profile | Release Bounds (m³/s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for res_name, a_entry in block_a.items():
        c_entry = c_agents.get(res_name) or {}
        bounds = a_entry.get("action_space") or {}
        model_label = (
            f"{c_entry.get('provider')}:{c_entry.get('model')}"
            if c_entry.get("provider") and c_entry.get("model")
            else "offline / none"
        )
        lines.append(
            f"| `{res_name}` | `{a_entry.get('reservoir_id')}` | "
            f"{'`' + str(a_entry['agent_id']) + '`' if a_entry.get('agent_id') else '—'} | "
            f"`{a_entry.get('agent_type')}` | `{a_entry.get('strategy')}` | "
            f"`{model_label}` | `{_fmt(a_entry.get('information_profile'))}` | "
            f"`[{_fmt(bounds.get('minimum_release_cms'))}, {_fmt(bounds.get('maximum_release_cms'))}]` |"
        )

    lines.extend(["", "## Block A — Cognitive Architecture", ""])
    for res_name, a_entry in block_a.items():
        wm = a_entry.get("working_memory") or {}
        ltk = a_entry.get("long_term_knowledge") or {}
        pkg_ids = ltk.get("package_ids") or []
        pkg_sha = ltk.get("sha256") or {}
        action_space = a_entry.get("action_space") or {}
        lines.append(f"### `{res_name}` (`{a_entry.get('reservoir_id')}`)")
        lines.append(f"- **Agent Type / Strategy**: `{a_entry.get('agent_type')}` / `{a_entry.get('strategy')}`")
        lines.append(
            f"- **Working Memory**: `history_steps={wm.get('history_steps', 0)}`, "
            f"`previous_transition_included={_fmt(wm.get('previous_transition_included'))}`"
        )
        if pkg_ids:
            formatted_pkgs = ", ".join(
                f"`{pid}` (`{str(pkg_sha.get(pid, ''))[:12]}…`)" if pid in pkg_sha else f"`{pid}`"
                for pid in pkg_ids
            )
            lines.append(f"- **Long-Term Knowledge**: {formatted_pkgs}")
        else:
            lines.append("- **Long-Term Knowledge**: None declared")
        lines.append(f"- **Information Profile**: `{_fmt(a_entry.get('information_profile'))}`")
        lines.append(
            f"- **Action Space**: release `[{_fmt(action_space.get('minimum_release_cms'))}, "
            f"{_fmt(action_space.get('maximum_release_cms'))}] {action_space.get('unit', 'm3/s')}`; "
            f"storage `[{_fmt(action_space.get('dead_storage_m3'))}, {_fmt(action_space.get('capacity_m3'))}] m³`"
        )
        lines.append(f"- **Decision Loop**: `{a_entry.get('decision_loop')}`")
        lines.append("")

    lines.extend(["## Block B — Identity", ""])
    for res_name, b_entry in block_b.items():
        lines.append(f"### `{res_name}` (`{b_entry.get('reservoir_id')}`)")
        lines.append(
            f"- **Prompt Identity**: `prompt_id={_fmt(b_entry.get('prompt_id'))}`, "
            f"`strategy_id={_fmt(b_entry.get('prompt_strategy_id'))}`, "
            f"`version={_fmt(b_entry.get('prompt_version'))}`"
        )
        lines.append(f"- **Prompt SHA-256**: `{_fmt(b_entry.get('prompt_sha256'))}`")
        lines.append(
            f"- **Prompt Files**: system=`{_fmt(b_entry.get('system_prompt_file'))}`, "
            f"user=`{_fmt(b_entry.get('user_prompt_file'))}`"
        )
        lines.append(f"- **Pinned Source Files**: `{b_entry.get('source_files_pinned_count', 0)}`")
        if b_entry.get("system_prompt_preview"):
            lines.append(f"- **System Prompt Preview**: \"{b_entry['system_prompt_preview']}\"")
        lines.append("")

    lines.extend([
        "## Block C — Inference Configuration",
        "",
        f"- **Python**: `{_fmt(runtime.get('python_version'))}`",
        f"- **Platform**: `{_fmt(runtime.get('platform'))}`",
        f"- **HydroReOpLLM Version**: `{_fmt(runtime.get('hydroreopllm_version'))}`",
        f"- **HydroCNHS Core Commit**: `{_fmt(runtime.get('hydrocnhs_core_commit'))}`",
        f"- **ABM Module SHA-256**: `{_fmt(runtime.get('abm_module_sha256'))}`",
        "",
        "| Reservoir | Provider | Model | Temp | Seed | Max Tokens | `num_ctx` | `think` | Max Attempts | Auto Retry | Offline Only | Fallbacks |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for res_name, c_entry in c_agents.items():
        lines.append(
            f"| `{res_name}` | `{_fmt(c_entry.get('provider'))}` | `{_fmt(c_entry.get('model'))}` | "
            f"`{_fmt(c_entry.get('temperature'))}` | `{_fmt(c_entry.get('seed'))}` | "
            f"`{_fmt(c_entry.get('max_tokens'))}` | `{_fmt(c_entry.get('num_ctx'))}` | "
            f"`{_fmt(c_entry.get('think'))}` | `{_fmt(c_entry.get('max_attempts'))}` | "
            f"`{_fmt(c_entry.get('automatic_retry'))}` | `{_fmt(c_entry.get('offline_only'))}` | "
            f"`{len(c_entry.get('fallback_models') or [])}` |"
        )

    lines.extend(["", "## Block D — Behavioral Submodel", "", "### Signature & Binding", ""])
    for res_name in block_a:
        sig = d_sig.get(res_name) or {}
        bind = d_bind.get(res_name) or {}
        auditors = [
            f"{a.get('auditor_id')}@{a.get('version')}"
            for a in (sig.get("auditor_specs") or [])
            if isinstance(a, Mapping)
        ]
        lines.append(f"- **`{res_name}`**: schema=`{sig.get('response_schema')}`, "
                     f"parser=`{_fmt(sig.get('response_parser_id'))}`, "
                     f"auditors=`{', '.join(auditors) if auditors else 'none'}`, "
                     f"history_steps=`{bind.get('history_steps', 0)}`, "
                     f"prompt_vars=`{', '.join(bind.get('prompt_variable_names') or []) or 'none'}`, "
                     f"context_providers=`{', '.join(bind.get('context_provider_names') or []) or 'none'}`")

    lines.extend([
        "",
        "### Empirical Resolution Telemetry",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Total Decisions | `{_fmt(d_res.get('total_decisions'))}` |",
        f"| Observed Network Calls | `{_fmt(d_res.get('observed_network_calls'))}` |",
        f"| Provider Attempt Events | `{_fmt(d_res.get('provider_attempt_events'))}` |",
        f"| Provider Started Attempts | `{_fmt(d_res.get('provider_started_attempts'))}` |",
        f"| Provider Failed Attempts | `{_fmt(d_res.get('provider_failed_attempts'))}` |",
        f"| Retry Attempts | `{_fmt(d_res.get('retry_attempts'))}` |",
        f"| Fallback Served Decisions | `{_fmt(d_res.get('fallback_served_decisions'))}` |",
        f"| Fallback Used | `{_fmt(d_res.get('fallback_used'))}` |",
        f"| Physical Clipping Steps | `{_fmt(d_res.get('physical_clipping_steps'))}` |",
        f"| Physical Clipping Rate | `{_fmt(d_res.get('physical_clipping_rate'))}` |",
        f"| Spill Steps | `{_fmt(d_res.get('spill_steps'))}` |",
        f"| Audit Counts | `{json.dumps(d_res.get('audit_counts') or {}, sort_keys=True)}` |",
        f"| Serving Profiles | `{json.dumps(d_res.get('serving_profiles') or {}, sort_keys=True)}` |",
        "",
        "## Block E — Validation & SHA-256 Verification Summary",
        "",
        f"- **Verification Command**: `{block_e.get('verification_command', 'reservoir-experiment verify <output>')}`",
        f"- **Offline Replay Capable**: `{_fmt(block_e.get('offline_replay_capable'))}`",
        f"- **Max Reservoir Mass-Balance Residual (m³)**: `{_fmt(block_e.get('max_mass_balance_residual_m3'))}`",
        f"- **Max System Balance Residual (m³)**: `{_fmt(block_e.get('max_system_balance_residual_m3'))}`",
        f"- **Final Storage (m³)**: `{json.dumps(block_e.get('final_storage_m3') or {}, sort_keys=True)}`",
        "",
        "| Artifact | SHA-256 |",
        "| --- | --- |",
    ])
    for name, digest in sorted((block_e.get("output_files_sha256") or {}).items()):
        lines.append(f"| `{name}` | `{digest}` |")
    if block_e.get("provider_attempts_sha256"):
        lines.append(f"| `provider_attempts.jsonl` | `{block_e['provider_attempts_sha256']}` |")
    lines.append("")
    return "\n".join(lines)


def export_odd_report(
    output_dir: Path | str,
    *,
    json_out: Path | str | None = None,
    markdown_out: Path | str | None = None,
) -> dict[str, Any]:
    """Load or compute an ODD+LLM manifest for a run directory and optionally export JSON/Markdown.

    Handles both flat run directories and coupled preparation roots (``preparation.json`` -> ``operation/``).
    """
    resolved_dir = _resolve_coupled_dir(output_dir)
    manifest_file = resolved_dir / "odd_llm_manifest.json"
    if manifest_file.is_file():
        loaded = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not isinstance(loaded, Mapping) or loaded.get("schema_version") != ODD_LLM_SCHEMA_VERSION:
            raise ValueError("saved odd_llm_manifest.json is invalid or unsupported")
        manifest = json_snapshot(loaded, label="odd_llm_manifest")
        source = "saved"
    else:
        manifest = build_odd_llm_manifest(resolved_dir)
        source = "computed"

    report: dict[str, Any] = {
        "schema_version": manifest["schema_version"],
        "run_id": manifest["run_id"],
        "source": source,
        "manifest": manifest,
    }
    if json_out is not None:
        json_target = Path(json_out)
        json_target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        json_target.write_text(payload, encoding="utf-8")
        report["json_out"] = str(json_target.resolve())
    if markdown_out is not None:
        md_target = Path(markdown_out)
        md_target.parent.mkdir(parents=True, exist_ok=True)
        md_target.write_text(render_odd_llm_markdown(manifest), encoding="utf-8")
        report["markdown_out"] = str(md_target.resolve())
    return report
