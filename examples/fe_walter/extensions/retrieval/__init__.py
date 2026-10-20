"""Read saved passages through the same callback interface as a vector search.

This local example makes no external request. A user-owned vector database
adapter can implement build_context(config) and return a ContextValue in the
same form. Keep credentials in the adapter's environment, rather than its YAML.
"""
from hashlib import sha256
import json
from pathlib import Path

from llm_reservoir_agent.context import ContextValue


def _read(path):
    blob = Path(path).read_bytes()
    data = json.loads(blob.decode("utf-8"))
    if not isinstance(data, dict) or set(data) != {"available_at", "passages"}:
        raise ValueError("passage file requires available_at and passages")
    if not isinstance(data["available_at"], str):
        raise ValueError("passage availability must be an ISO timestamp")
    if not isinstance(data["passages"], list) or any(
        not isinstance(item, dict) or set(item) != {"document_id", "text"}
        or any(not isinstance(value, str) or not value.strip() for value in item.values())
        for item in data["passages"]
    ):
        raise ValueError("passages require nonempty document_id and text")
    return data, sha256(blob).hexdigest()


def validate_context(config, *, base_path):
    """Resolve and pin the passage file; configuration checks do not retrieve."""
    if not isinstance(config, dict) or set(config) != {"passages_file", "query"}:
        raise ValueError("retrieval config requires passages_file and query")
    if any(not isinstance(value, str) or not value.strip() for value in config.values()):
        raise ValueError("retrieval paths and query must be nonempty text")
    path = (Path(base_path) / config["passages_file"]).resolve()
    _, digest = _read(path)
    return {**config, "passages_file": str(path), "sha256": digest}, {str(path): digest}


def rebase_context(spec, *, base_path):
    """Keep a relative passage path anchored to its declaring agent file."""
    config = spec.get("config", {})
    if isinstance(config, dict) and isinstance(config.get("passages_file"), str):
        config["passages_file"] = str((Path(base_path) / config["passages_file"]).resolve())


def build_context(config):
    """Construct a per-agent callback only when a decision actually needs it."""
    def retrieve(context):
        data, digest = _read(config["passages_file"])
        if digest != config["sha256"]:
            raise ValueError("passage file changed after validation")
        return ContextValue(
            {"query": config["query"], "passages": data["passages"]},
            {"source": "saved_passages", "source_sha256": digest,
             "available_at": data["available_at"],
             "decision_time": context.observation["timestamp"]},
        )
    return retrieve
