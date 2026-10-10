"""Optional DKP V3.7 composition preserving original decisions and audits."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .contracts import _json_mapping_copy
from .prompt import validate_provenance


class DKPPolicyAdapter:
    """Adapt a supplied DKP policy; construction imports the frozen legacy bridge.

    The existing DKP policy emits its full audited decision through ``_log``.
    During decide(), an observational hook retains that exact emitted record
    and forwards the original logging call once. It never reruns an auditor.
    Legacy cfs/cms conversion, consult scheduling, bounds, and history stay in
    the frozen bridge. Use LLMPolicyAdapter for strict commit/reentry handling.
    """

    policy_id = "dkp_v3_7"

    def __init__(self, cfg: Any, policy: Any, *, consult_every_day: bool = True,
                 on_commit: Callable[[Mapping[str, Any]], None] | None = None) -> None:
        from delaware_operations.anik_adapter import AnikPolicyAdapter

        self._policy = policy
        self._latest_audit: dict[str, Any] | None = None
        self._adapter = AnikPolicyAdapter(
            cfg, policy, consult_every_day=consult_every_day, on_commit=on_commit,
        )

    @property
    def state_owner(self) -> Any:
        """The supplied policy owns consult history and must be reservoir-local."""
        return self._policy

    @property
    def latest_audit(self) -> dict[str, Any] | None:
        """Return a detached original audited record, or None when none emitted."""

        return None if self._latest_audit is None else _json_mapping_copy(self._latest_audit, "DKP audit")

    @property
    def network_calls(self) -> int | None:
        return self._adapter.network_calls

    def describe(self) -> dict[str, Any] | None:
        value = getattr(self._policy, "provenance", None)
        return None if value is None else validate_provenance(value)

    def decide(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        self._latest_audit = None
        original = getattr(self._policy, "_log", None)
        if not callable(original):
            result = self._adapter.decide(observation)
            emitted = getattr(self._policy, "latest_audit", None)
            if emitted is not None:
                self._latest_audit = _json_mapping_copy(emitted, "DKP audit")
            return result

        # Restore the precise instance attribute state even when decide/logging
        # fails; a bound method inherited from the class must not become an
        # accidental permanent instance override.
        namespace = vars(self._policy)
        had_override = "_log" in namespace
        previous_override = namespace.get("_log")

        def retain(record: Mapping[str, Any]) -> Any:
            copied = _json_mapping_copy(record, "DKP emitted record") if "audit_status" in record else None
            self._latest_audit = copied
            return original(record)

        self._policy._log = retain
        try:
            return self._adapter.decide(observation)
        finally:
            if had_override:
                self._policy._log = previous_override
            else:
                del self._policy._log

    def record_transition(self, record: Mapping[str, Any]) -> None:
        self._adapter.record_transition(record)
