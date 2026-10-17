"""A local retrieval example; replace build_context to connect your own index.

The simulator imports this package only when the YAML registers it. Validation
pins the local documents. Actual retrieval happens once per decision and returns
the text and its provenance through the general ContextValue contract.
"""
import hashlib
import json
from pathlib import Path

from llm_reservoir_agent.context import ContextValue


def rebase_context(spec, *, base_path):
    spec["config"]["documents"] = str((Path(base_path) / spec["config"]["documents"]).resolve())


def validate_context(config, *, base_path):
    if set(config) != {"documents"}:
        raise ValueError("local retrieval requires a documents JSON file")
    path = (Path(base_path) / config["documents"]).resolve()
    raw = path.read_bytes()
    documents = json.loads(raw)
    if not isinstance(documents, list) or not documents or any(
            set(row) != {"id", "text", "available_at"} for row in documents):
        raise ValueError("documents require id, text and available_at")
    return {"documents": str(path)}, {str(path): hashlib.sha256(raw).hexdigest()}


def build_context(config):
    path = Path(config["documents"])
    raw = path.read_bytes()
    documents = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()

    def retrieve(context):
        # The query is an example; a vector DB connector can use the same input.
        query = "inflow storage controlled release spill"
        words = set(query.split())
        ranked = sorted(documents, key=lambda row: (
            -len(words & set(row["text"].lower().split())), row["id"]))
        selected = ranked[:2]
        return ContextValue("\n".join(row["text"] for row in selected), provenance={
            "source": str(path), "source_sha256": digest, "query": query,
            "document_ids": [row["id"] for row in selected],
            "available_at": max(row["available_at"] for row in selected)})

    return retrieve
