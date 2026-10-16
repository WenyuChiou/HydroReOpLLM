"""Versioned prompt artifacts, independent of providers, parsing, and auditing.

Backends may inject any PromptStrategy, ResponseParser, and Auditor independently.
These contracts never call a model, choose a release, or manufacture an audit.

Role: Define replaceable prompt, parser and auditor contracts.

Connections and data: configured_backend and custom backends use
PromptSpec/PromptRequest to retain template, rendered messages and provenance.
PromptStrategy builds a request; ResponseParser returns an action; Auditor returns
diagnostic findings. Defining these contracts performs no inference or physical
operation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from .contracts import ReservoirAction, _json_mapping_copy
from .audit import validate_audit_provenance


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be a lowercase SHA256 hex digest")
    return value


def _hash(value: Any) -> str:
    content = json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate supplied metadata; omitted fields retain their unknown meaning."""

    result = _json_mapping_copy(value, "provenance")
    for name in ("prompt_strategy_id", "prompt_version", "response_parser_id", "auditor_id"):
        if name in result:
            _text(result[name], name)
    for name in ("prompt_sha256", "prompt_content_sha256", "request_sha256"):
        if name in result:
            _sha256(result[name], name)
    if "knowledge_package_ids" in result or "knowledge_package_sha256" in result:
        ids = result.get("knowledge_package_ids")
        hashes = result.get("knowledge_package_sha256")
        if not isinstance(ids, list) or not isinstance(hashes, dict):
            raise ValueError("knowledge_package_ids and knowledge_package_sha256 must be supplied together")
        for identifier in ids:
            _text(identifier, "knowledge package ID")
        if len(ids) != len(set(ids)) or set(ids) != set(hashes):
            raise ValueError("knowledge package IDs and hash keys must match without duplicates")
        for identifier, digest in hashes.items():
            _sha256(digest, f"knowledge_package_sha256.{identifier}")
    validate_audit_provenance(result)
    return result


@dataclass(frozen=True)
class PromptSpec:
    """Fixed template identity plus explicit optional knowledge IDs/hashes.

    The version identifies a chosen template revision; the hashes identify its
    exact text and declared knowledge. No retrieval or generation happens here.
    """

    strategy_id: str
    version: str
    template: str
    knowledge_package_ids: Sequence[str] = ()
    knowledge_package_sha256: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.strategy_id, "strategy_id")
        _text(self.version, "version")
        _text(self.template, "template")
        if isinstance(self.knowledge_package_ids, (str, bytes)) or not isinstance(self.knowledge_package_ids, Sequence):
            raise TypeError("knowledge_package_ids must be a sequence of IDs")
        metadata = validate_provenance({
            "knowledge_package_ids": list(self.knowledge_package_ids),
            "knowledge_package_sha256": self.knowledge_package_sha256,
        })
        object.__setattr__(self, "knowledge_package_ids", tuple(metadata["knowledge_package_ids"]))
        object.__setattr__(self, "knowledge_package_sha256", metadata["knowledge_package_sha256"])

    @property
    def template_sha256(self) -> str:
        return hashlib.sha256(self.template.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id, "version": self.version, "template": self.template,
            "knowledge_package_ids": list(self.knowledge_package_ids),
            "knowledge_package_sha256": dict(self.knowledge_package_sha256),
        }

    @property
    def content_sha256(self) -> str:
        return _hash(self.to_dict())

    def provenance(self, *, response_parser_id: str, auditor_id: str) -> dict[str, Any]:
        return validate_provenance({
            "prompt_strategy_id": self.strategy_id, "prompt_version": self.version,
            "prompt_sha256": self.template_sha256, "prompt_content_sha256": self.content_sha256,
            "knowledge_package_ids": list(self.knowledge_package_ids),
            "knowledge_package_sha256": dict(self.knowledge_package_sha256),
            "response_parser_id": response_parser_id, "auditor_id": auditor_id,
        })


@dataclass(frozen=True)
class PromptRequest:
    """Rendered role/content messages for one decision, with provenance.

    messages contain the actual request text; metadata identifies its sources.
    This request is separate from both the raw reply and the parsed action.
    """

    messages: Sequence[Mapping[str, Any]]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.messages, (str, bytes)) or not isinstance(self.messages, Sequence) or not self.messages:
            raise ValueError("messages must be a non-empty sequence")
        messages = []
        for message in self.messages:
            copied = _json_mapping_copy(message, "message")
            _text(copied.get("role"), "message.role")
            _text(copied.get("content"), "message.content")
            messages.append(copied)
        object.__setattr__(self, "messages", tuple(messages))
        object.__setattr__(self, "metadata", validate_provenance(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {"messages": [_json_mapping_copy(item, "message") for item in self.messages],
                "metadata": validate_provenance(self.metadata)}

    @property
    def content_sha256(self) -> str:
        return _hash(self.to_dict())


class PromptStrategy(Protocol):
    spec: PromptSpec

    def build(self, observation: Mapping[str, Any]) -> PromptRequest: ...


class ResponseParser(Protocol):
    parser_id: str

    def parse(self, response: Any) -> Mapping[str, Any] | ReservoirAction: ...


class Auditor(Protocol):
    auditor_id: str

    def audit(self, decision: Mapping[str, Any], request: PromptRequest) -> Mapping[str, Any] | None: ...
