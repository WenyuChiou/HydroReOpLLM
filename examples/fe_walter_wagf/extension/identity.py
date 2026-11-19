"""Run identity, model version record and output-folder safety for the WAGF prototype.

Nothing here talks to the model through the bounded model transport. The local
model reader makes its own short HTTP calls (10 s timeout) to the Ollama server.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import urllib.request
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit, urlunsplit

IDENTITY_FILE = "run_identity.json"
SCHEMA = "fe-walter-wagf-run-identity.v1"
LOCAL_PROVIDERS = ("ollama",)
READ_TIMEOUT_SECONDS = 10
_DIGEST = re.compile(r"[0-9a-f]{64}")
# Fields that may legitimately differ between a run and its resume.
_UNSTABLE = {("model", "captured_at"), ("model", "digest_at_end"), ("model", "digest_at_end_error"),
             ("model", "model_changed_during_run"), ("observed_provider_models",),
             ("wagf", "git_commit"), ("wagf", "git_dirty")}


def is_local(provider: str) -> bool:
    return provider in LOCAL_PROVIDERS


def normalize_digest(value: Any) -> str:
    """Return a bare lowercase 64-digit hex digest; accept an optional ``sha256:`` prefix."""
    text = str(value).strip().lower() if isinstance(value, str) else ""
    if text.startswith("sha256:"):
        text = text[len("sha256:"):]
    if not _DIGEST.fullmatch(text):
        raise ValueError("expected_model_digest must be a 64-digit SHA-256 hex string, with or without 'sha256:'")
    return text


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_url(url: str) -> str:
    """The base URL without user info or query, so a key can never ride along."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def broker_sha256(root: Path) -> str:
    """SHA-256 over the sorted code and YAML files of ``broker/``, without tests and ``__pycache__``."""
    base = Path(root) / "broker"
    digest = hashlib.sha256()
    files = []
    for path in base.rglob("*"):
        if path.suffix not in (".py", ".yaml", ".yml") or not path.is_file():
            continue
        parts = path.relative_to(base).parts
        if "__pycache__" in parts or "tests" in parts[:-1] or parts[-1].startswith("test_") or parts[-1] == "conftest.py":
            continue
        files.append(("/".join(parts), path))
    for name, path in sorted(files):
        digest.update(name.encode("utf-8") + b"\0" + file_sha256(path).encode("ascii") + b"\n")
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                              timeout=READ_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def wagf_code_identity() -> dict:
    """Git state (null when git is unavailable) and a content hash of the WAGF broker package."""
    root = Path(os.environ["WAGF_ROOT"]).resolve()
    commit = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain") if commit else None
    return {"git_commit": commit or None, "git_dirty": None if status is None else bool(status),
            "broker_sha256": broker_sha256(root)}


def _get_json(opener: Callable, url: str, body: dict | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="GET" if body is None else "POST",
                                     headers={"Content-Type": "application/json"})
    with opener(request, timeout=READ_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def read_local_model(model: Mapping[str, Any], *, opener: Callable = urllib.request.urlopen) -> dict:
    """Read digest, family, size, quantization and server version of a local Ollama model."""
    root = str(model["base_url"]).rstrip("/")
    name = model["model"]
    shown = _get_json(opener, root + "/api/show", {"model": name})
    details = shown.get("details") or {}
    digest = shown.get("digest")
    if not digest:
        tags = _get_json(opener, root + "/api/tags")
        # Ollama lists a model pulled without a tag as "<name>:latest".
        wanted = {name, name if ":" in name else f"{name}:latest"}
        for item in tags.get("models", []):
            if wanted & {item.get("name"), item.get("model")}:
                digest = item.get("digest")
                break
    version = _get_json(opener, root + "/api/version").get("version")
    return {"digest": digest, "family": details.get("family"), "parameter_size": details.get("parameter_size"),
            "quantization_level": details.get("quantization_level"), "version": version}


def write_json_atomic(path: Path, value: Any) -> None:
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _local_fields(model: Mapping[str, Any], reader: Callable, expected_digest: str | None) -> dict:
    """Read the local model record once and enforce the digest rules; the first request has not been sent."""
    try:
        info = dict(reader(model))
    except Exception as exc:
        raise RuntimeError(f"cannot read the version of local model {model['model']!r} from {safe_url(model['base_url'])}: "
                           f"{type(exc).__name__}: {exc}") from exc
    if not info.get("digest"):
        raise RuntimeError(f"the local server did not report a digest for model {model['model']!r}; "
                           "refusing to start without a model version record")
    info["digest"] = normalize_digest(info["digest"])
    if expected_digest is not None and info["digest"] != expected_digest:
        raise RuntimeError(f"local model {model['model']!r} has digest {info['digest']}, "
                           f"but expected_model_digest is {expected_digest}")
    return info


def read_current_digest(model: Mapping[str, Any], reader: Callable) -> str | None:
    info = reader(model)
    return normalize_digest(info["digest"]) if info.get("digest") else None


def build_identity(arm: str, seed: int, model: Mapping[str, Any], *, agent_types: Path, skill_registry: Path,
                   reader: Callable, expected_digest: str | None) -> dict:
    provider = model["provider"]
    record = {"provider": provider, "name": model["model"], "base_url": safe_url(model["base_url"])}
    identity = {"schema_version": SCHEMA, "arm": arm, "wagf_seed": seed, "wagf": wagf_code_identity(),
                "config": {"agent_types_sha256": file_sha256(agent_types),
                           "skill_registry_sha256": file_sha256(skill_registry)},
                "model": record}
    if is_local(provider):
        info = _local_fields(model, reader, expected_digest)
        record.update(info)
        record["captured_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        if expected_digest is not None:
            raise ValueError("expected_model_digest only applies to a local model; a cloud model has no digest")
        identity["observed_provider_models"] = {}
    return identity


def _flatten(value: Any, prefix: tuple = ()) -> dict:
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            out.update(_flatten(item, prefix + (key,)))
        return out
    return {prefix: value}


def differences(saved: Mapping[str, Any], current: Mapping[str, Any]) -> list[str]:
    """Names of the stable identity fields that differ (captured time and observed models are ignored)."""
    old, new = _flatten(saved), _flatten(current)
    names = []
    for key in sorted(set(old) | set(new)):
        if key in _UNSTABLE or key[:1] == ("observed_provider_models",) or key[:1] == ("schema_version",):
            continue
        if old.get(key) != new.get(key):
            names.append(".".join(key))
    return names


def prepare_output(output: Path, identity: Mapping[str, Any]) -> Path | None:
    """Keep earlier output safe before the new run writes anything.

    An empty or missing folder is used as is, and None says no earlier identity was compared. A
    folder with files and the same identity is moved, whole, to ``<name>.previous-<N>``. A different
    identity raises before anything is touched. A leftover temporary identity file does not count
    as output: it only means a crash happened before the first identity was saved.
    """
    output = Path(output)
    temporary = IDENTITY_FILE + ".tmp"
    if not output.exists() or not any(path.name != temporary for path in output.iterdir()):
        return None
    saved_path = output / IDENTITY_FILE
    try:
        saved = json.loads(saved_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{output} already holds files but has no readable {IDENTITY_FILE} "
                         f"({type(exc).__name__}); choose a new output folder") from exc
    changed = differences(saved, identity)
    if changed:
        raise ValueError(f"{output} holds output from a different run; these identity fields differ: "
                         f"{', '.join(changed)}. Choose a new output folder.")
    number = 1
    while output.with_name(f"{output.name}.previous-{number}").exists():
        number += 1
    target = output.with_name(f"{output.name}.previous-{number}")
    os.replace(output, target)
    return target
