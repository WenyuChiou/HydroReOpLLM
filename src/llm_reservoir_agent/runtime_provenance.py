"""Runtime environment & model provenance helpers for HydroReOpLLM runs.

Role: Probe live Ollama server version/model digest snapshots safely (zero credentials
persisted) and record a compact, framework-neutral ``runtime_environment`` summary inside
``summary.json`` alongside the core simulation results.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .audit import json_snapshot


_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_SHA256_HEX = re.compile(r"[0-9a-fA-F]{64}\Z")
_MAX_PROBE_RESPONSE_BYTES = 1_048_576
_KEY_DEPENDENCIES = ("numpy", "pandas", "scipy", "PyYAML", "deap", "matplotlib")
_SAFE_SNAPSHOT_FIELDS = (
    "provider",
    "base_url",
    "requested_model",
    "probe_status",
    "probed_at_utc",
    "server_version",
    "model_digest_sha256",
    "model_size_bytes",
    "modified_at",
    "model_family",
    "model_families",
    "parameter_size",
    "quantization_level",
    "model_format",
    "modelfile_sha256",
    "template_sha256",
    "model_parameters_raw",
)
_SAFE_MODEL_FIELDS = (
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


def _package_version() -> str:
    """Return installed hydroreopllm version with a safe static fallback."""
    try:
        return importlib.metadata.version("hydroreopllm")
    except Exception:
        return "0.1.1"


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
    for field in _SAFE_MODEL_FIELDS:
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


class _NoRedirect(HTTPRedirectHandler):
    """Disable HTTP redirects so credentials are never forwarded during runtime probing."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("runtime probe redirects are disabled")


def _http_json_probe(
    method: str,
    url: str,
    payload: Mapping[str, Any] | None,
    headers: Mapping[str, str],
    timeout: float = 3.0,
) -> dict[str, Any]:
    """Perform one bounded, no-redirect HTTP JSON probe and return a strict JSON object."""
    req_headers = dict(headers)
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(dict(payload), allow_nan=False, ensure_ascii=False).encode("utf-8")
        if "content-type" not in {k.lower() for k in req_headers}:
            req_headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=req_headers, method=str(method).upper())
    with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        body = response.read(_MAX_PROBE_RESPONSE_BYTES + 1)
    if len(body) > _MAX_PROBE_RESPONSE_BYTES:
        raise ValueError("probe response exceeds the 1 MiB size limit")
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("probe response must be strict UTF-8") from exc

    def _reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant in probe response: {value}")

    parsed = json.loads(decoded, parse_constant=_reject_constant)
    if not isinstance(parsed, dict):
        raise TypeError("probe response must be a JSON object")
    return parsed


def _normalize_digest(value: Any) -> str | None:
    """Normalize a model SHA-256 digest string, prefixing bare 64-hex digests with 'sha256:'."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.lower().startswith("sha256:"):
        return "sha256:" + text[7:]
    if _SHA256_HEX.fullmatch(text):
        return f"sha256:{text.lower()}"
    return text


def _nonempty_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def probe_ollama_runtime_snapshot(
    base_url: str,
    model: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 3.0,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Best-effort live probe of an Ollama server for version, digest, and quantization metadata.

    Never raises and never includes credentials or headers in the returned snapshot.
    """
    fetch = fetcher or _http_json_probe
    clean_base = _sanitize_base_url(base_url)
    root_url = clean_base.rstrip("/") if clean_base else ""
    req_headers: dict[str, str] = {"Accept": "application/json"}
    if isinstance(headers, Mapping):
        for k, v in headers.items():
            if isinstance(k, str) and isinstance(v, str):
                req_headers[k] = v

    probed_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    succeeded = 0

    server_version: str | None = None
    model_digest_sha256: str | None = None
    model_size_bytes: int | None = None
    modified_at: str | None = None
    model_family: str | None = None
    model_families: list[str] | None = None
    parameter_size: str | None = None
    quantization_level: str | None = None
    model_format: str | None = None
    modelfile_sha256: str | None = None
    template_sha256: str | None = None
    model_parameters_raw: str | None = None
    tags_details: Mapping[str, Any] | None = None

    if root_url:
        try:
            ver_resp = fetch("GET", f"{root_url}/api/version", None, req_headers, timeout)
            if isinstance(ver_resp, Mapping):
                succeeded += 1
                server_version = _nonempty_str(ver_resp.get("version"))
        except Exception:
            pass

        try:
            tags_resp = fetch("GET", f"{root_url}/api/tags", None, req_headers, timeout)
            if isinstance(tags_resp, Mapping):
                succeeded += 1
                models_list = tags_resp.get("models")
                if isinstance(models_list, list):
                    candidates = [model]
                    if ":" not in model:
                        candidates.append(f"{model}:latest")
                    matched: Mapping[str, Any] | None = None
                    for target_name in candidates:
                        for item in models_list:
                            if isinstance(item, Mapping) and (
                                item.get("name") == target_name or item.get("model") == target_name
                            ):
                                matched = item
                                break
                        if matched is not None:
                            break
                    if matched is not None:
                        model_digest_sha256 = _normalize_digest(matched.get("digest"))
                        size_val = matched.get("size")
                        if isinstance(size_val, int) and not isinstance(size_val, bool) and size_val >= 0:
                            model_size_bytes = size_val
                        modified_at = _nonempty_str(matched.get("modified_at"))
                        if isinstance(matched.get("details"), Mapping):
                            tags_details = matched["details"]
        except Exception:
            pass

        try:
            show_resp = fetch("POST", f"{root_url}/api/show", {"name": model}, req_headers, timeout)
            if isinstance(show_resp, Mapping):
                succeeded += 1
                details = show_resp.get("details")
                if isinstance(details, Mapping):
                    model_family = _nonempty_str(details.get("family"))
                    raw_families = details.get("families")
                    if isinstance(raw_families, list):
                        clean_fams = [f.strip() for f in raw_families if isinstance(f, str) and f.strip()]
                        model_families = clean_fams if clean_fams else None
                    parameter_size = _nonempty_str(details.get("parameter_size"))
                    quantization_level = _nonempty_str(details.get("quantization_level"))
                    model_format = _nonempty_str(details.get("format"))
                modelfile = show_resp.get("modelfile")
                if isinstance(modelfile, str) and modelfile:
                    modelfile_sha256 = hashlib.sha256(modelfile.encode("utf-8")).hexdigest()
                template = show_resp.get("template")
                if isinstance(template, str) and template:
                    template_sha256 = hashlib.sha256(template.encode("utf-8")).hexdigest()
                params = show_resp.get("parameters")
                if isinstance(params, str) and params.strip():
                    stripped_params = params.strip()
                    model_parameters_raw = (
                        stripped_params if len(stripped_params) <= 500 else stripped_params[:497].rstrip() + "..."
                    )
                if model_digest_sha256 is None:
                    model_digest_sha256 = _normalize_digest(show_resp.get("digest"))
                if modified_at is None:
                    modified_at = _nonempty_str(show_resp.get("modified_at"))
        except Exception:
            pass

        if isinstance(tags_details, Mapping):
            if model_family is None:
                model_family = _nonempty_str(tags_details.get("family"))
            if model_families is None and isinstance(tags_details.get("families"), list):
                clean_fams = [f.strip() for f in tags_details["families"] if isinstance(f, str) and f.strip()]
                model_families = clean_fams if clean_fams else None
            if parameter_size is None:
                parameter_size = _nonempty_str(tags_details.get("parameter_size"))
            if quantization_level is None:
                quantization_level = _nonempty_str(tags_details.get("quantization_level"))
            if model_format is None:
                model_format = _nonempty_str(tags_details.get("format"))

    if server_version is not None and (
        model_digest_sha256 is not None or quantization_level is not None or parameter_size is not None
    ):
        probe_status = "ok"
    elif succeeded > 0:
        probe_status = "partial"
    else:
        probe_status = "unavailable"

    snapshot = {
        "provider": "ollama",
        "base_url": clean_base,
        "requested_model": str(model),
        "probe_status": probe_status,
        "probed_at_utc": probed_at_utc,
        "server_version": server_version,
        "model_digest_sha256": model_digest_sha256,
        "model_size_bytes": model_size_bytes,
        "modified_at": modified_at,
        "model_family": model_family,
        "model_families": model_families,
        "parameter_size": parameter_size,
        "quantization_level": quantization_level,
        "model_format": model_format,
        "modelfile_sha256": modelfile_sha256,
        "template_sha256": template_sha256,
        "model_parameters_raw": model_parameters_raw,
    }
    return json_snapshot(snapshot, label="ollama_runtime_snapshot")


def _probe_headers_for_model(model_cfg: Mapping[str, Any]) -> dict[str, str]:
    """Build transient non-persisted headers for an Ollama probe if an API key env var is set."""
    headers: dict[str, str] = {"Accept": "application/json"}
    env_name = _sanitize_env_name(model_cfg.get("api_key_env"))
    if env_name is not None:
        secret = os.environ.get(env_name)
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
    return headers


def probe_live_model_snapshots(
    agents: Mapping[str, Mapping[str, Any]],
    *,
    timeout: float = 3.0,
    fetcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Probe unique live Ollama models across configured LLM agents, keyed by reservoir name.

    Never raises; caches probes per unique ``(base_url, model)``.
    """
    result: dict[str, Any] = {}
    if not isinstance(agents, Mapping):
        return result
    cache: dict[tuple[str, str], dict[str, Any]] = {}

    def _probe_one(model_cfg: Any) -> dict[str, Any] | None:
        if not isinstance(model_cfg, Mapping) or model_cfg.get("provider") != "ollama":
            return None
        base_url = _sanitize_base_url(model_cfg.get("base_url"))
        model_name = _nonempty_str(model_cfg.get("model"))
        if not base_url or not model_name:
            return None
        cache_key = (base_url.rstrip("/"), model_name)
        if cache_key not in cache:
            cache[cache_key] = probe_ollama_runtime_snapshot(
                base_url,
                model_name,
                headers=_probe_headers_for_model(model_cfg),
                timeout=timeout,
                fetcher=fetcher,
            )
        return json_snapshot(cache[cache_key], label="ollama_runtime_snapshot")

    try:
        for agent in agents.values():
            if not isinstance(agent, Mapping) or agent.get("mode") != "llm":
                continue
            reservoir = _nonempty_str(agent.get("reservoir"))
            if not reservoir:
                continue
            primary_snap = _probe_one(agent.get("model"))
            fallback_snaps: list[dict[str, Any]] = []
            raw_fallbacks = agent.get("fallback_models")
            if isinstance(raw_fallbacks, list):
                for fb in raw_fallbacks:
                    fb_snap = _probe_one(fb)
                    if fb_snap is not None:
                        fallback_snaps.append(fb_snap)
            if primary_snap is not None or fallback_snaps:
                result[reservoir] = {
                    "primary": primary_snap,
                    "fallbacks": fallback_snaps,
                }
    except Exception:
        return result
    return result


def _sanitize_single_snapshot(snap: Any) -> dict[str, Any] | None:
    """Keep only allow-listed, credential-free runtime snapshot fields."""
    if not isinstance(snap, Mapping):
        return None
    out: dict[str, Any] = {}
    for field in _SAFE_SNAPSHOT_FIELDS:
        if field not in snap:
            continue
        val = snap[field]
        if field == "base_url":
            out[field] = _sanitize_base_url(val)
        elif field == "model_digest_sha256":
            out[field] = _normalize_digest(val)
        else:
            out[field] = val
    return out if out else None


def _sanitize_server_runtime_snapshot(entry: Any) -> dict[str, Any] | None:
    """Return a sanitized copy of a per-reservoir ``server_runtime_snapshot`` mapping, or None."""
    if not isinstance(entry, Mapping):
        return None
    primary = _sanitize_single_snapshot(entry.get("primary"))
    fallbacks_raw = entry.get("fallbacks")
    fallbacks: list[dict[str, Any]] = []
    if isinstance(fallbacks_raw, list):
        for item in fallbacks_raw:
            cleaned = _sanitize_single_snapshot(item)
            if cleaned is not None:
                fallbacks.append(cleaned)
    if primary is None and not fallbacks:
        return None
    return {"primary": primary, "fallbacks": fallbacks}


def _key_dependency_versions() -> dict[str, str | None]:
    """Return installed versions of key scientific dependencies (or None when absent)."""
    versions: dict[str, str | None] = {}
    for pkg in _KEY_DEPENDENCIES:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except Exception:
            versions[pkg] = None
    return versions


def _collect_reply_provenance(reply: Any, versions: set[str], fingerprints: set[str]) -> None:
    """Extract observed model snapshot version IDs and system fingerprints from one provider reply."""
    if not isinstance(reply, Mapping):
        return
    for key in ("model", "modelVersion"):
        val = reply.get(key)
        if isinstance(val, str) and val.strip():
            versions.add(val.strip())
    fp = reply.get("system_fingerprint")
    if isinstance(fp, str) and fp.strip():
        fingerprints.add(fp.strip())


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


def _harvest_observed_reply_provenance(
    decisions: list[dict[str, Any]],
    provider_attempts: list[dict[str, Any]],
    output_path: Path,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Scan saved raw traces and RETURNED provider attempts for model snapshot IDs and fingerprints."""
    versions_by_rid: dict[str, set[str]] = {}
    fingerprints_by_rid: dict[str, set[str]] = {}
    raw_cache: dict[str, Any] = {}

    for event in decisions:
        rid = event.get("reservoir_id")
        ref = event.get("raw_policy_ref")
        if not isinstance(rid, str) or not isinstance(ref, Mapping):
            continue
        rel_path = ref.get("path")
        if not isinstance(rel_path, str) or not rel_path.strip():
            continue
        if rel_path not in raw_cache:
            raw_cache[rel_path] = _safe_child_json(output_path, rel_path)
        raw_trace = raw_cache[rel_path]
        unwrapped = (
            raw_trace.get("backend_trace", raw_trace)
            if isinstance(raw_trace, Mapping)
            else None
        )
        if not isinstance(unwrapped, Mapping):
            continue
        v_set = versions_by_rid.setdefault(rid, set())
        fp_set = fingerprints_by_rid.setdefault(rid, set())
        _collect_reply_provenance(unwrapped.get("provider_reply"), v_set, fp_set)
        _collect_reply_provenance(unwrapped.get("raw_reply"), v_set, fp_set)
        latest = unwrapped.get("latest_attempt")
        if isinstance(latest, Mapping):
            _collect_reply_provenance(latest.get("provider_reply"), v_set, fp_set)
        attempts = unwrapped.get("attempts")
        if isinstance(attempts, list):
            for att in attempts:
                if isinstance(att, Mapping):
                    _collect_reply_provenance(att.get("provider_reply"), v_set, fp_set)

    for attempt_event in provider_attempts:
        if attempt_event.get("status") != "RETURNED":
            continue
        rid = attempt_event.get("reservoir_id")
        if not isinstance(rid, str):
            continue
        v_set = versions_by_rid.setdefault(rid, set())
        fp_set = fingerprints_by_rid.setdefault(rid, set())
        _collect_reply_provenance(attempt_event.get("provider_reply"), v_set, fp_set)

    return (
        {rid: sorted(vals) for rid, vals in versions_by_rid.items()},
        {rid: sorted(vals) for rid, vals in fingerprints_by_rid.items()},
    )


def _sanitize_source_files(source_files: Any) -> dict[str, str]:
    """Return relative/basename keys for source_files without leaking host paths."""
    if not isinstance(source_files, Mapping):
        return {}
    out: dict[str, str] = {}
    for raw_key, digest in source_files.items():
        if not isinstance(raw_key, str) or not isinstance(digest, str):
            continue
        win = PureWindowsPath(raw_key)
        posix = PurePosixPath(raw_key)
        if win.is_absolute() or posix.is_absolute() or re.match(r"^[A-Za-z]:", raw_key) or raw_key.startswith("\\\\"):
            name = win.name if "\\" in raw_key or re.match(r"^[A-Za-z]:", raw_key) else posix.name
        else:
            name = raw_key.replace("\\", "/")
        if name:
            out[name] = digest
    return out


def build_runtime_environment(
    output_dir: Path | str,
    *,
    experiment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build compact, credential-free runtime environment & model provenance metadata for summary.json."""
    out_path = Path(output_dir)
    exp_data = dict(experiment) if isinstance(experiment, Mapping) else {}
    if not exp_data:
        loaded = _safe_child_json(out_path, "experiment.json")
        if isinstance(loaded, Mapping):
            exp_data = dict(loaded)

    provenance = exp_data.get("provenance") if isinstance(exp_data.get("provenance"), Mapping) else {}
    settings = provenance.get("settings") if isinstance(provenance.get("settings"), Mapping) else {}
    plan = provenance.get("plan") if isinstance(provenance.get("plan"), Mapping) else {}
    settings_models = settings.get("models") if isinstance(settings.get("models"), Mapping) else {}
    settings_agents = settings.get("agents") if isinstance(settings.get("agents"), Mapping) else {}
    server_snapshots = (
        provenance.get("server_runtime_snapshots")
        if isinstance(provenance.get("server_runtime_snapshots"), Mapping)
        else {}
    )
    backend_provs = exp_data.get("backend_provenance") if isinstance(exp_data.get("backend_provenance"), Mapping) else {}

    network = exp_data.get("network") if isinstance(exp_data.get("network"), Mapping) else {}
    reservoirs = network.get("reservoirs") if isinstance(network.get("reservoirs"), Mapping) else {}
    decisions = _read_jsonl(out_path / "decisions.jsonl")
    provider_attempts = _read_jsonl(out_path / "provider_attempts.jsonl")
    observed_versions, observed_fingerprints = _harvest_observed_reply_provenance(
        decisions, provider_attempts, out_path
    )

    hydrocnhs_core = exp_data.get("hydrocnhs_core") if isinstance(exp_data.get("hydrocnhs_core"), Mapping) else {}
    agents_summary: dict[str, Any] = {}
    for res_name, res_spec in reservoirs.items():
        if not isinstance(res_spec, Mapping):
            continue
        phys = res_spec.get("physical") if isinstance(res_spec.get("physical"), Mapping) else {}
        reservoir_id = phys.get("reservoir_id") if isinstance(phys.get("reservoir_id"), str) else res_name
        b_prov = backend_provs.get(res_name) if isinstance(backend_provs.get(res_name), Mapping) else {}

        agent_id = None
        agent_spec: Mapping[str, Any] = {}
        for aid, spec in settings_agents.items():
            if isinstance(spec, Mapping) and spec.get("reservoir") == res_name:
                agent_id = aid
                agent_spec = spec
                break

        raw_model = b_prov.get("model")
        if raw_model is None and isinstance(agent_spec.get("model"), str):
            raw_model = settings_models.get(agent_spec["model"])
        safe_model = _sanitize_model_entry(raw_model) or {}

        raw_fallbacks = b_prov.get("fallback_models")
        if raw_fallbacks is None and isinstance(agent_spec.get("fallback_models"), list):
            raw_fallbacks = [
                settings_models[k] for k in agent_spec["fallback_models"] if isinstance(k, str) and k in settings_models
            ]
        safe_fallbacks = []
        if isinstance(raw_fallbacks, list):
            for fb in raw_fallbacks:
                cleaned = _sanitize_model_entry(fb)
                if cleaned is not None:
                    safe_fallbacks.append(cleaned)

        seed_val = safe_model.get("seed")
        random_seed_configured = bool(seed_val is not None and not isinstance(seed_val, bool))

        mode_label = "passive_outlet"
        if res_spec.get("operation_mode") != "passive_outlet":
            plan_types = plan.get("agent_types") if isinstance(plan.get("agent_types"), Mapping) else {}
            mode_label = str(
                plan_types.get(agent_id)
                or b_prov.get("mode")
                or agent_spec.get("mode")
                or ("rule_based" if b_prov.get("backend") in {"hanasaki_benchmark", "rule_based"} else "offline")
            )

        agents_summary[res_name] = {
            "agent_id": agent_id,
            "reservoir_id": reservoir_id,
            "mode": mode_label,
            "provider": safe_model.get("provider"),
            "model": safe_model.get("model"),
            "base_url": safe_model.get("base_url"),
            "temperature": safe_model.get("temperature"),
            "seed": seed_val,
            "random_seed_configured": random_seed_configured,
            "max_tokens": safe_model.get("max_tokens"),
            "num_ctx": safe_model.get("num_ctx"),
            "think": safe_model.get("think"),
            "keep_alive": safe_model.get("keep_alive"),
            "api_key_env": safe_model.get("api_key_env"),
            "fallback_models": safe_fallbacks,
            "server_runtime_snapshot": _sanitize_server_runtime_snapshot(server_snapshots.get(res_name)),
            "observed_model_versions": list(observed_versions.get(reservoir_id, [])),
            "observed_system_fingerprints": list(observed_fingerprints.get(reservoir_id, [])),
        }

    env = {
        "python_version": exp_data.get("python") or platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "hydroreopllm_version": _package_version(),
        "hydrocnhs_core_commit": hydrocnhs_core.get("hydrocnhs_commit"),
        "key_dependencies": _key_dependency_versions(),
        "source_file_sha256": _sanitize_source_files(provenance.get("source_files")),
        "agents": agents_summary,
    }
    return json_snapshot(env, label="runtime_environment")
