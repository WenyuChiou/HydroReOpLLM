"""HydroCNHS Dam adapter for one reservoir decision and physical transition.

Purpose and data flow
---------------------
The host supplies a verified routed inlet (m3/s) and operation clock.
The agent observes beginning storage (m3), requests a policy action, validates
it and applies the shared mass-balance kernel. Implemented controlled release
plus spill is returned as the downstream Dam boundary. Ending storage carries
forward once; repeated calls at a committed step return cached total outflow.

Dependencies and side effects
-----------------------------
Uses contracts, physics, deterministic policies and TimeAxis.
Construction creates operation/error fields on the host data collector. act
updates reservoir state and appends a record; policy/information callbacks may
have their own I/O. Rejected policy attempts are logged and re-raised.
"""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Any, Mapping

from .contracts import ReservoirObservation, parse_action, _json_mapping_copy
from .physics import PhysicalConfig, apply_transition
from .policies import ConstantPolicy, PassThroughPolicy
from .time_axis import TimeAxis


class LLMReservoirAgent:
    """Operate one reservoir through the native HydroCNHS Dam API.

    Parameters
    ----------
    **kwargs : object
        Native host arguments: name (output node), config (Inputs.Links and
        Attributes.Physical/Context/Policy), start_date and current_date (objects
        with ISO labels), data_length (positive step count), t (current zero-based
        step), dc (collector with Q_routed and add_field), and rn_gen (host random
        generator). Optional policy replaces Attributes.Policy and must expose
        decide(observation). Physical storage is in m3, rates in m3/s, dt in seconds.

    Raises
    ------
    TypeError
        A required host argument is absent or host/config/policy types are invalid.
    ValueError
        Identity, physical configuration, context, links or policy settings fail
        validation. Exactly one -1 inlet and one +1 output link are required.

    Notes
    -----
    Hosts must mark assigned inflow ready or verify native simulation order
    before operating. Numeric zero or a positive routed value does not establish
    readiness. ReservoirDamAgent is a compatibility alias for this class.
    """

    def __init__(self, **kwargs: Any) -> None:
        for required in (
            "name",
            "config",
            "start_date",
            "current_date",
            "data_length",
            "t",
            "dc",
            "rn_gen",
        ):
            if required not in kwargs:
                raise TypeError(f"missing required HydroCNHS argument: {required}")
            setattr(self, required, kwargs[required])
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if isinstance(self.data_length, bool) or not isinstance(self.data_length, int):
            raise TypeError("data_length must be an integer")
        if self.data_length <= 0:
            raise ValueError("data_length must be positive")
        if not isinstance(self.config, Mapping):
            raise TypeError("config must be a mapping")

        attributes = self.config.get("Attributes", {})
        if not isinstance(attributes, Mapping):
            raise TypeError("Attributes must be a mapping")
        self.context = _json_mapping_copy(attributes.get("Context", {}), "Attributes.Context")
        if set(self.context) & {"reservoir_id", "evaporation_m3", "seepage_m3", "decision_information"}:
            raise ValueError("Attributes.Context cannot override host identity or physical assumptions")
        physical = attributes.get("Physical")
        if not isinstance(physical, Mapping):
            raise ValueError("LLMReservoirAgent requires Attributes.Physical")
        self.physical = PhysicalConfig(**dict(physical))
        explicit_axis = kwargs.get("time_axis")
        if explicit_axis is not None and not isinstance(explicit_axis, TimeAxis):
            raise TypeError("time_axis must be a TimeAxis")
        self.time_axis = explicit_axis
        if self.time_axis is None:
            if self.physical.dt_seconds != 86400.0:
                raise ValueError("the HydroCNHS Dam interface requires a daily timestep")
        elif self.physical.dt_seconds != self.time_axis.dt_seconds:
            raise ValueError("physical dt_seconds must match time_axis.dt_seconds")
        elif self.start_date != self.time_axis.instant(0):
            raise ValueError(
                f"start_date {self.start_date!r} does not match time_axis start "
                f"{self.time_axis.instant(0).isoformat()}"
            )
        self.storage_m3 = self.physical.initial_storage_m3
        self.inflow_outlet, self.output_outlet = self._validate_links()
        injected_policy = kwargs.get("policy")
        self.policy = (
            injected_policy
            if injected_policy is not None
            else self._build_policy(attributes.get("Policy"))
        )
        if not callable(getattr(self.policy, "decide", None)):
            raise TypeError("policy must provide decide(observation)")
        self.policy_id = getattr(self.policy, "policy_id", type(self.policy).__name__)

        self.operations_log_field = f"{self.name}_OperationsLog"
        if not hasattr(self.dc, self.operations_log_field):
            self.dc.add_field(
                self.operations_log_field,
                [],
                desc="Committed reservoir operations.",
            )
        self.operations_log = getattr(self.dc, self.operations_log_field)
        if not isinstance(self.operations_log, list):
            raise TypeError("operations log field must be a list")
        error_field = f"{self.name}_OperationsErrors"
        if not hasattr(self.dc, error_field):
            self.dc.add_field(error_field, [], desc="Rejected policy attempts; no state transition.")
        self.policy_errors = getattr(self.dc, error_field)
        if not isinstance(self.policy_errors, list):
            raise TypeError("policy error field must be a list")
        # Readiness is explicit: a zero/positive inlet alone proves no ordering.
        self._ready_timesteps: set[int] = set()
        self._topology_verified = False
        # Cache the completed step so repeated Dam calls do not operate twice.
        self._last_committed_t: int | None = None
        self._cached_outflow_cms: float | None = None

    def _validate_links(self) -> tuple[str, str]:
        inputs = self.config.get("Inputs")
        links = inputs.get("Links") if isinstance(inputs, Mapping) else None
        if not isinstance(links, Mapping):
            raise ValueError("Inputs.Links must be a mapping")
        inflows: list[str] = []
        outputs: list[str] = []
        for outlet, factor in links.items():
            if not isinstance(outlet, str) or not outlet:
                raise ValueError("link outlet names must be non-empty strings")
            if isinstance(factor, bool) or not isinstance(factor, (int, float)):
                raise TypeError("link factors must be numeric -1 or +1")
            numeric = float(factor)
            if not math.isfinite(numeric) or numeric not in (-1.0, 1.0):
                raise ValueError("link factors must be exactly -1 or +1; scaling is unsupported")
            (inflows if numeric == -1.0 else outputs).append(outlet)
        if len(inflows) != 1 or len(outputs) != 1 or len(links) != 2:
            raise ValueError("Inputs.Links requires exactly one -1 inflow and one +1 output")
        if outputs[0] != self.name:
            raise ValueError("the positive Dam link must equal the agent name")
        return inflows[0], outputs[0]

    @staticmethod
    def _build_policy(config: Any) -> Any:
        if not isinstance(config, Mapping):
            raise ValueError("LLMReservoirAgent requires Attributes.Policy")
        provider = config.get("provider")
        if provider == "pass_through":
            extras = set(config).difference({"provider"})
            if extras:
                raise ValueError(f"unsupported pass_through policy fields: {sorted(extras)}")
            return PassThroughPolicy()
        if provider == "constant":
            extras = set(config).difference({"provider", "release_cms"})
            if extras:
                raise ValueError(f"unsupported constant policy fields: {sorted(extras)}")
            if "release_cms" not in config:
                raise ValueError("constant policy requires release_cms")
            return ConstantPolicy(config["release_cms"])
        raise ValueError("Attributes.Policy.provider must be 'pass_through' or 'constant'")

    def mark_inflow_ready(self, timestep: int) -> None:
        """Mark a host-assigned inlet value ready for one operation step.

        Parameters
        ----------
        timestep : int
            Zero-based step in [0, data_length); readiness is consumed on commit.

        Returns
        -------
        None
            Updates the internal readiness set without operating the reservoir.

        Raises
        ------
        TypeError
            timestep is not an integer or is boolean.
        ValueError
            timestep is outside the allocated run.
        """
        if isinstance(timestep, bool) or not isinstance(timestep, int):
            raise TypeError("timestep must be an integer")
        if not 0 <= timestep < self.data_length:
            raise ValueError("ready timestep is outside data_length")
        self._ready_timesteps.add(timestep)

    def verify_simulation_sequence(self, sequence) -> None:
        """Confirm the native host routes this inlet before calling the Dam.

        Parameters
        ----------
        sequence : iterable of str
            Host simulation order containing the inlet and output exactly once.

        Returns
        -------
        None
            Sets persistent topology readiness for subsequent operation steps.

        Raises
        ------
        ValueError
            Either Dam node is absent/duplicated or the inlet follows the output.
        """
        sequence = list(sequence)
        for outlet in (self.inflow_outlet, self.output_outlet):
            if sequence.count(outlet) != 1:
                raise ValueError("simulation sequence must contain each Dam node once")
        if sequence.index(self.inflow_outlet) >= sequence.index(self.output_outlet):
            raise ValueError("simulation sequence must route inflow before the Dam")
        self._topology_verified = True

    def _validate_clock(self) -> int:
        if isinstance(self.t, bool) or not isinstance(self.t, int):
            raise TypeError("t must be an integer")
        if not 0 <= self.t < self.data_length:
            raise IndexError("timestep is outside data_length")
        if self.time_axis is None:
            expected = self.start_date + timedelta(days=self.t)
        else:
            expected = self.time_axis.instant(self.t)
        expected_text = expected.isoformat() if hasattr(expected, "isoformat") else str(expected)
        current_text = (
            self.current_date.isoformat()
            if hasattr(self.current_date, "isoformat")
            else str(self.current_date)
        )
        if current_text != expected_text:
            raise ValueError(f"current_date {current_text} does not match timestep {self.t} ({expected_text})")
        if self._last_committed_t is None and self.t != 0:
            raise ValueError("reservoir operation must begin at timestep 0")
        if self._last_committed_t is not None and self.t not in (
            self._last_committed_t,
            self._last_committed_t + 1,
        ):
            raise ValueError("reservoir timesteps must be consecutive; backward or skipped steps are unsupported")
        return self.t

    def act(self, outlet: str) -> float:
        """Request, implement and record one causally ready reservoir interval.

        Parameters
        ----------
        outlet : str
            Positive Dam output link, which must equal the configured agent name.

        Returns
        -------
        float
            Implemented controlled release plus capacity spill in m3/s. Repeated
            calls for the latest committed step return the cached value.

        Raises
        ------
        TypeError
            Host step or routed inlet has an invalid type, or policy action is invalid.
        ValueError
            Clock/order, outlet, inlet, observation or action violates its contract.
        IndexError
            Host step is outside data_length.
        RuntimeError
            Inlet routing readiness has not been established.
        ArithmeticError
            The shared physical transition fails its finite/balance checks.

        Notes
        -----
        Policy/information exceptions are appended to the rejection log and
        propagate before a physical commit. Optional record_transition feedback occurs
        after storage/log/cache commit; its exceptions propagate without rollback.
        Evaporation and seepage are zero in the common physical observation.
        """
        timestep = self._validate_clock()
        if outlet != self.output_outlet:
            raise ValueError(f"act must be called for output link {self.output_outlet!r}")
        if timestep == self._last_committed_t:
            assert self._cached_outflow_cms is not None
            return self._cached_outflow_cms

        inflow = self.dc.Q_routed[self.inflow_outlet][timestep]
        if isinstance(inflow, bool) or not isinstance(inflow, (int, float)):
            raise TypeError("routed inflow must be numeric")
        inflow = float(inflow)
        if not math.isfinite(inflow) or inflow < 0.0:
            raise ValueError("routed inflow must be finite and non-negative")
        if not self._topology_verified and timestep not in self._ready_timesteps:
            raise RuntimeError(
                "routed inflow is not known ready; verify simulation sequence or mark_inflow_ready(t)"
            )

        timestamp = (
            self.time_axis.timestamp(timestep)
            if self.time_axis is not None
            else (
                self.current_date.isoformat()
                if hasattr(self.current_date, "isoformat")
                else str(self.current_date)
            )
        )
        # This observation uses beginning storage, before this interval's release/spill.
        observation = ReservoirObservation(
            timestep=timestep,
            timestamp=timestamp,
            inflow_cms=inflow,
            # Convert usable beginning storage to a mean rate, then add this inlet.
            release_upper_bound_cms=min(
                self.physical.maximum_release_cms,
                max(
                    0.0,
                    inflow
                    + (self.storage_m3 - self.physical.dead_storage_m3)
                    / self.physical.dt_seconds,
                ),
            ),
            state={
                "storage_m3": self.storage_m3,
                "capacity_m3": self.physical.capacity_m3,
                "dead_storage_m3": self.physical.dead_storage_m3,
                "minimum_release_cms": self.physical.minimum_release_cms,
                "maximum_release_cms": self.physical.maximum_release_cms,
                "dt_seconds": self.physical.dt_seconds,
            },
            context={
                **self.context,
                "reservoir_id": self.physical.reservoir_id,
                "evaporation_m3": 0.0,
                "seepage_m3": 0.0,
            },
        )
        try:
            information = getattr(self, "information_builder", None)
            if information is not None:
                # The provider receives a copy; it cannot alter physical inputs.
                snapshot = information(observation.to_dict())
                observation = ReservoirObservation(**dict(observation.to_dict(), context={
                    **observation.context, "decision_information": _json_mapping_copy(snapshot, "decision_information")}))
            candidate = self.policy.decide(observation.to_dict())
            action = parse_action(candidate)
        except Exception as exc:
            self.policy_errors.append({
                "observation": observation.to_dict(), "policy_id": str(self.policy_id),
                "error_class": type(exc).__name__, "error": str(exc),
            })
            raise
        transition = apply_transition(
            self.physical,
            self.storage_m3,
            inflow,
            action.release_cms,
        )
        record = {
            "observation": observation.to_dict(),
            "action": action.to_dict(),
            "transition": transition.to_dict(),
            "policy_id": str(self.policy_id),
        }
        self.operations_log.append(record)
        # Commit end-of-interval storage (m3) as the next interval's beginning state.
        self.storage_m3 = transition.storage_end_m3
        self._last_committed_t = timestep
        self._cached_outflow_cms = transition.total_outflow_cms
        self._ready_timesteps.discard(timestep)
        # Optional policy feedback follows the single committed transition.
        # Repeated act() returns above, so it never repeats feedback or I/O.
        callback = getattr(self.policy, "record_transition", None)
        if callable(callback):
            callback(record)
        return transition.total_outflow_cms


ReservoirDamAgent = LLMReservoirAgent
