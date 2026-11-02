"""Represent prompt templates, rendered requests and replaceable backend contracts.

``configured_backend`` and custom backends retain ``PromptSpec`` template
identity, ``PromptRequest`` messages and declared source provenance. A prompt
strategy builds messages, a response parser returns a requested action, and an
auditor returns findings; these responsibilities remain independently injectable.
Template version labels a revision. template_sha256 hashes user-template text;
content_sha256 also identifies system text, metadata and declared knowledge.
Rendered request hashes identify the actual message content and provenance.
Physical values keep their observation units (native m3/s, m3 and seconds).
Validation uses finite JSON and explicit metadata without retrieval, model
inference, file I/O, release selection or hydrologic state updates.
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
    """Require a nonempty metadata/message string rather than silently coercing unknown values."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _sha256(value: Any, label: str) -> str:
    """Validate lowercase 64-character SHA256 syntax; content existence and integrity are checked by the owning source loader."""

    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be a lowercase SHA256 hex digest")
    return value


def _hash(value: Any) -> str:
    """Hash finite, sorted, compact UTF-8 JSON to distinguish content changes independently of platform line endings."""

    content = json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and detach metadata that the backend actually declares.

    Parameters
    ----------
    value : Mapping[str, Any]
        Optional prompt/parser/auditor IDs and hashes; knowledge IDs and digest mapping must be declared together.

    Returns
    -------
    dict[str, Any]
        Detached finite JSON retaining omitted metadata as unknown rather than inventing identities.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

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
    """Identify one chosen prompt revision and its declared knowledge inputs.

    Construction validates declarations but does not read or retrieve knowledge. Hashes identify text/content; a human-readable revision alone does not pin exact bytes.

    Parameters
    ----------
    strategy_id : str
        Nonempty prompt-strategy identity.
    version : str
        Nonempty caller-selected template revision, separate from a schema or package version.
    template : str
        Nonempty user prompt template; its UTF-8 bytes define template_sha256.
    knowledge_package_ids : Sequence[str], optional
        Unique IDs of explicitly selected knowledge packages.
    knowledge_package_sha256 : Mapping[str, str], optional
        Lowercase content digests with exactly the same keys as knowledge_package_ids.
    system_template : str, optional
        System prompt text, possibly empty; included in content_sha256.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    strategy_id: str
    # Human-selected template revision; exact text/content identity is carried by hashes.
    version: str
    template: str
    knowledge_package_ids: Sequence[str] = ()
    knowledge_package_sha256: Mapping[str, str] = field(default_factory=dict)
    system_template: str = ""

    def __post_init__(self) -> None:
        """Validate prompt identity/text and matching unique knowledge IDs/hashes, detaching declared metadata without retrieving content."""

        _text(self.strategy_id, "strategy_id")
        _text(self.version, "version")
        _text(self.template, "template")
        if not isinstance(self.system_template, str):
            raise TypeError("system_template must be a string")
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
        """Hash the user-template UTF-8 text only.

        Returns
        -------
        str
            Lowercase SHA256 of template; system text and knowledge metadata are covered separately by content_sha256.
        """

        return hashlib.sha256(self.template.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize template text and declared knowledge identities.

        Returns
        -------
        dict[str, Any]
            New mapping with user/system templates, strategy/version and copied knowledge IDs/hashes.
        """

        return {
            "strategy_id": self.strategy_id, "version": self.version, "template": self.template,
            "system_template": self.system_template,
            "knowledge_package_ids": list(self.knowledge_package_ids),
            "knowledge_package_sha256": dict(self.knowledge_package_sha256),
        }

    @property
    def content_sha256(self) -> str:
        """Hash the complete serialized prompt specification.

        Returns
        -------
        str
            Canonical digest including user/system templates, strategy/version and knowledge declarations.
        """

        return _hash(self.to_dict())

    def provenance(self, *, response_parser_id: str, auditor_id: str) -> dict[str, Any]:
        """Bind prompt identity to explicit parser and auditor identities.

        Parameters
        ----------
        response_parser_id : str
            Nonempty identity of the selected response parser.
        auditor_id : str
            Nonempty identity of the selected auditor.

        Returns
        -------
        dict[str, Any]
            Validated metadata with template/content hashes and matching knowledge declarations.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        return validate_provenance({
            "prompt_strategy_id": self.strategy_id, "prompt_version": self.version,
            "prompt_sha256": self.template_sha256, "prompt_content_sha256": self.content_sha256,
            "knowledge_package_ids": list(self.knowledge_package_ids),
            "knowledge_package_sha256": dict(self.knowledge_package_sha256),
            "response_parser_id": response_parser_id, "auditor_id": auditor_id,
        })


@dataclass(frozen=True)
class PromptRequest:
    """Retain actual rendered messages for one decision with source metadata.

    Messages are the actual request content, separate from the provider's raw reply and parsed release. Construction itself sends no request.

    Parameters
    ----------
    messages : Sequence[Mapping[str, Any]]
        Nonempty role/content message mappings containing nonempty text; copied to detached finite JSON.
    metadata : Mapping[str, Any], optional
        Declared prompt/parser/auditor/source provenance, validated without adding unknown identities.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    messages: Sequence[Mapping[str, Any]]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Require nonempty role/content messages, detach each mapping and validate provenance before rendering a provider payload."""

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
        """Export detached rendered messages and validated provenance.

        Returns
        -------
        dict[str, Any]
            messages and metadata copies suitable for JSON serialization and evidence capture.

        Raises
        ------
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """

        return {"messages": [_json_mapping_copy(item, "message") for item in self.messages],
                "metadata": validate_provenance(self.metadata)}

    @property
    def content_sha256(self) -> str:
        """Identify actual rendered message content and provenance together.

        Returns
        -------
        str
            Canonical SHA256 of the complete serialized request, distinct from template-only hashes.
        """

        return _hash(self.to_dict())


@dataclass(frozen=True)
class RenderedPromptContext:
    """Pass detached inputs to an optional custom message builder.

    Construction copies data but does not independently validate causal availability of every supplied variable or execute the message builder.

    Parameters
    ----------
    observation : Mapping[str, Any]
        Current decision snapshot, with native physical units retained.
    knowledge : Mapping[str, str]
        Explicitly selected knowledge text keyed by source ID.
    previous_transition : Mapping[str, Any] or None
        Already completed prior physical record; None before the first transition.
    variables : Mapping[str, Any]
        Finite JSON prompt bindings after caller-controlled selection.
    rendered_user : str
        User text after fixed template substitution.
    rendered_system : str, optional
        System text after substitution, possibly empty.

    Raises
    ------
    TypeError
        A value has the wrong type or is not finite JSON.
    ValueError
        A required field, version, numeric bound or digest is invalid.
    """

    observation: Mapping[str, Any]
    knowledge: Mapping[str, str]
    # Completed prior feedback only; this cannot contain the current physical result.
    previous_transition: Mapping[str, Any] | None
    variables: Mapping[str, Any]
    rendered_user: str
    rendered_system: str = ""

    def __post_init__(self) -> None:
        """Detach observation/knowledge/completed-transition/variable inputs and require rendered user/system text to remain strings."""

        copied = _json_mapping_copy({
            "observation": self.observation,
            "knowledge": self.knowledge,
            "previous_transition": self.previous_transition,
            "variables": self.variables,
        }, "rendered prompt context")
        object.__setattr__(self, "observation", copied["observation"])
        object.__setattr__(self, "knowledge", copied["knowledge"])
        object.__setattr__(self, "previous_transition", copied["previous_transition"])
        object.__setattr__(self, "variables", copied["variables"])
        if not isinstance(self.rendered_user, str) or not isinstance(self.rendered_system, str):
            raise TypeError("rendered prompt text must be strings")


class PromptStrategy(Protocol):
    """Structural contract for replacing prompt construction while retaining an explicit PromptSpec.

    The backend remains responsible for observation availability and provider execution.
    """

    spec: PromptSpec

    def build(self, observation: Mapping[str, Any]) -> PromptRequest:
        """Build the request for a single observed decision boundary.

        Concrete builders declare and propagate their own rendering/validation errors; this protocol performs no execution.

        Parameters
        ----------
        observation : Mapping[str, Any]
            Current detached observation; input physical values retain native units.

        Returns
        -------
        PromptRequest
            Actual rendered role/content messages and declared provenance.
        """
        ...


class ResponseParser(Protocol):
    """Structural contract for translating one provider reply into the shared requested-action vocabulary.

    Parsing does not implement physical release, spill or storage changes.
    """

    parser_id: str

    def parse(self, response: Any) -> Mapping[str, Any] | ReservoirAction:
        """Parse a response into a requested controlled-release action.

        Concrete parsers must expose parser_id and propagate invalid-response errors; the protocol does not supply a fallback release.

        Parameters
        ----------
        response : object
            Captured provider reply in the concrete parser's documented format.

        Returns
        -------
        Mapping[str, Any] or ReservoirAction
            Requested release in m3/s, subsequently validated by parse_action and host physics.
        """
        ...


class Auditor(Protocol):
    """Structural contract for an independently replaceable response/decision auditor with an explicit auditor_id."""

    auditor_id: str

    def audit(self, decision: Mapping[str, Any], request: PromptRequest) -> Mapping[str, Any] | None:
        """Report diagnostic findings using the parsed decision and actual prompt.

        A concrete auditor defines its errors. The returned diagnostic does not replace the action or advance physical state.

        Parameters
        ----------
        decision : Mapping[str, Any]
            Decision payload to inspect; any requested controlled release uses m3/s.
        request : PromptRequest
            Actual rendered messages and provenance used for this decision.

        Returns
        -------
        Mapping[str, Any] or None
            Explicit reported findings/status, or None when no audit evidence is available.
        """
        ...
