"""Provider-specific DKP V3.7 layer behind the generic reservoir interface."""

from __future__ import annotations

from typing import Any, Callable, Mapping


class DKPPolicyAdapter:
    """Compose the frozen DKP adapter without changing its release semantics.

    Importing this module creates no backend and invokes no policy. Construction
    adapts an already supplied configuration and target-release policy. The
    legacy layer preserves cfs/cms conversion, bounded DKP decisions, scheduler
    state, prompts, and postphysics ``record_outcome`` with controlled flow plus
    spill. Wrap this instance in ``LLMPolicyAdapter`` for the generic boundary.
    """

    policy_id = "dkp_v3_7"

    def __init__(
        self,
        cfg: Any,
        policy: Any,
        *,
        consult_every_day: bool = True,
        on_commit: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        from .anik_adapter import AnikPolicyAdapter

        self._adapter = AnikPolicyAdapter(
            cfg, policy, consult_every_day=consult_every_day, on_commit=on_commit,
        )

    @property
    def network_calls(self) -> int | None:
        """Expose the existing provider's observed counter without inference."""

        return self._adapter.network_calls

    def decide(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        return self._adapter.decide(observation)

    def record_transition(self, record: Mapping[str, Any]) -> None:
        self._adapter.record_transition(record)
