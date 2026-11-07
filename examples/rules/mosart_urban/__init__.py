"""MOSART-Urban flood-control rule for the shared reservoir operator interface.

This independent implementation follows reservoir_operation.py and the annual
snapshot in solver.py at the pinned upstream commit. Inputs are interval-mean
flow (m3/s) and beginning storage (m3). The output is a requested release
(m3/s); the common host still implements the water balance and routing.

The upstream rule has no outlet-flow ceiling. This extension checks the common
host's physical transition before returning an action, so conflicting outlet or
protected-storage limits fail explicitly instead of silently changing the rule.
Upstream source is an external verification dependency, recorded by commit and
file hash; it is not bundled with this extension.
"""

from datetime import datetime, timedelta
import math
from pathlib import Path

from llm_reservoir_agent.audit import json_snapshot
from llm_reservoir_agent.benchmark_config import load_benchmark
from llm_reservoir_agent.contracts import ReservoirAction, ReservoirObservation, finite_nonnegative
from llm_reservoir_agent.physics import PhysicalConfig, apply_transition


UPSTREAM_REPOSITORY = "https://github.com/RiverAI-Project/MOSART-Urban"
UPSTREAM_COMMIT = "7883c5cac62e8c0c585fbafbb1045118cad2dd42"
UPSTREAM_SOURCE_SHA256 = "ef0ea6ce834910417cc84d5f0ca8883988a1f620cb883dac476d538b4dfde510"
SECONDS_PER_YEAR = 365.0 * 24.0 * 3600.0
FLOAT_EPSILON = 2.220446049250313e-16


def flood_control_step(inflow, storage, year_storage, capacity, mean_inflow, alpha, dt):
    """Calculate one MOSART-Urban flood-control release and water balance.

    Parameters
    ----------
    inflow, mean_inflow : float
        Current and historical mean inlet rates, m3/s.
    storage, year_storage, capacity : float
        Beginning, model-year-start, and maximum storage, m3.
    alpha : float
        Fraction used in both the release coefficient and operating ceiling.
    dt : float
        Interval duration, seconds. The regulation degree uses 365 days.

    Returns
    -------
    tuple of float
        Release in m3/s, ending storage in m3, and storage-change rate in m3/s.

    Notes
    -----
    Numerical inputs are validated by the backend. The order of the high,
    negative, and low-storage branches follows the pinned upstream algorithm.
    """
    if capacity < FLOAT_EPSILON:
        return inflow, 0.0, 0.0
    release = inflow
    if mean_inflow > FLOAT_EPSILON:
        degree = capacity / (mean_inflow * SECONDS_PER_YEAR)
        coefficient = year_storage / (alpha * capacity)
        release = coefficient * mean_inflow
        if degree < 0.5:
            weight = (degree * 2.0) ** 2
            release = weight * coefficient * mean_inflow + (1.0 - weight) * inflow
        release = max(release, 0.1 * mean_inflow)
    change = inflow - release
    end_storage = storage + change * dt
    if end_storage > alpha * capacity:
        release = release + (end_storage - alpha * capacity) / dt
        end_storage = alpha * capacity
        change = (end_storage - storage) / dt
    elif end_storage < 0.0:
        release = inflow + storage / dt
        end_storage = 0.0
        change = -storage / dt
    elif end_storage < 0.1 * capacity:
        available = storage + inflow * dt
        release = max((available - 0.1 * capacity) / dt, 0.0)
        change = inflow - release
        end_storage = storage + change * dt
    return release, end_storage, change


class MosartUrbanBackend:
    """Maintain one Daily reservoir's model-year snapshot and source parity.

    Parameters
    ----------
    physical : dict
        Common PhysicalConfig fields, with m3 storage and m3/s flow limits.
    mean_inflow_cms : float
        Nonnegative historical mean inflow, m3/s.
    alpha : float, optional
        Coefficient/operating-storage fraction, default 0.85.
    source : dict, optional
        Reference-statistics provenance included in saved method metadata.

    Raises
    ------
    ValueError
        Alpha, Daily duration, or numerical settings are invalid.
    """

    policy_id = "mosart_urban_hanasaki"
    network_calls = 0

    def __init__(self, physical, mean_inflow_cms, alpha=0.85, source=None):
        self.physical = PhysicalConfig(**physical)
        self.mean = finite_nonnegative(mean_inflow_cms, "mean_inflow_cms")
        self.alpha = finite_nonnegative(alpha, "alpha")
        if not 0.0 < self.alpha <= 1.0:
            raise ValueError("MOSART-Urban alpha must be in (0, 1]")
        if self.physical.dt_seconds != 86400.0:
            raise ValueError("MOSART-Urban example requires Daily dt_seconds=86400")
        self.source = json_snapshot(source or {}, label="MOSART-Urban reference")
        self._next_step = 0
        self._previous_time = None
        self._year_storage = None
        self._snapshot_date = None
        self._latest_trace = None

    def describe(self):
        """Return JSON-safe algorithm, source-version and units provenance."""
        return {
            "policy_id": self.policy_id, "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": UPSTREAM_COMMIT, "purpose": "flood_control",
            "upstream_source_sha256": UPSTREAM_SOURCE_SHA256,
            "alpha": self.alpha, "minimum_storage_fraction": 0.1,
            "environmental_flow_fraction": 0.1, "mean_inflow_cms": self.mean,
            "annual_snapshot": "beginning storage at the first step of each calendar year",
            "initial_snapshot": "configured beginning storage at the first operation step",
            "physical_conflict": "raise before advancing controller state",
            "source": self.source,
        }

    @property
    def latest_trace(self):
        """Return a detached snapshot of the last successful rule decision."""
        return None if self._latest_trace is None else dict(self._latest_trace)

    def decide(self, observation):
        """Return a source-equivalent release if the common host can implement it.

        Parameters
        ----------
        observation : mapping or ReservoirObservation
            Current inlet (m3/s), beginning storage (m3), Daily time and step.

        Returns
        -------
        ReservoirAction
            Source-equivalent requested release, m3/s.

        Raises
        ------
        ValueError
            Chronology or reservoir identity differs, or host constraints would
            change the upstream release/storage. Failed decisions preserve state.
        """
        obs = ReservoirObservation(**(
            observation.to_dict() if isinstance(observation, ReservoirObservation) else dict(observation)
        ))
        when = datetime.fromisoformat(obs.timestamp)
        if obs.timestep != self._next_step:
            raise ValueError(f"MOSART-Urban expected timestep {self._next_step}")
        if self._previous_time is not None and when != self._previous_time + timedelta(days=1):
            raise ValueError("MOSART-Urban observations must advance by one day")
        identity = obs.context.get("reservoir_id", self.physical.reservoir_id)
        if identity != self.physical.reservoir_id:
            raise ValueError("MOSART-Urban observation belongs to another reservoir")
        storage = finite_nonnegative(obs.state["storage_m3"], "state.storage_m3")
        if obs.state.get("dt_seconds", self.physical.dt_seconds) != self.physical.dt_seconds:
            raise ValueError("MOSART-Urban observation duration differs from physical settings")
        capacity = self.physical.capacity_m3
        if not math.isclose(obs.state.get("capacity_m3", capacity), capacity, rel_tol=1e-12):
            raise ValueError("MOSART-Urban observation capacity differs from physical settings")
        refreshed = self._year_storage is None or when.year != self._previous_time.year
        snapshot = storage if refreshed else self._year_storage
        release, expected_storage, change = flood_control_step(
            obs.inflow_cms, storage, snapshot, capacity, self.mean, self.alpha,
            self.physical.dt_seconds,
        )
        transition = apply_transition(self.physical, storage, obs.inflow_cms, release)
        if (not math.isclose(transition.controlled_release_cms, release, rel_tol=1e-12, abs_tol=1e-12)
                or not math.isclose(transition.storage_end_m3, expected_storage, rel_tol=1e-12, abs_tol=1e-6)
                or transition.spill_cms > 1e-12
                or release > obs.release_upper_bound_cms + 1e-12):
            raise ValueError(
                "MOSART-Urban parity conflict with host release/protected-storage bounds: "
                f"required release={release} m3/s, host release={transition.controlled_release_cms} m3/s, "
                f"source storage={expected_storage} m3, host storage={transition.storage_end_m3} m3. "
                "Use source-compatible physical limits or a separately identified constrained experiment."
            )
        # Commit the annual snapshot and chronology only after the host agrees.
        self._year_storage = snapshot
        if refreshed:
            self._snapshot_date = when.date().isoformat()
        self._latest_trace = {
            "timestamp": obs.timestamp, "timestep": obs.timestep, "model_used": False,
            "storage_start_m3": storage, "inflow_cms": obs.inflow_cms,
            "coefficient_refreshed": refreshed, "coefficient_storage_start_m3": snapshot,
            "coefficient_date": self._snapshot_date, "k_rls": snapshot / (self.alpha * capacity),
            "target_release_cms": release, "source_storage_end_m3": expected_storage,
            "source_storage_change_cms": change, "operating_storage_ceiling_m3": self.alpha * capacity,
        }
        self._previous_time = when
        self._next_step += 1
        return ReservoirAction(release)


def validate_backend(spec, *, base_path, physical, simulation_start, mode, **kwargs):
    """Validate explicit statistics or a teaching mean, and pin file dependencies."""
    allowed = {"reservoir", "mode", "strategy", "rule_parameters", "auditors"}
    parameters = spec.get("rule_parameters")
    fields = {"inflow_statistics_file", "mean_inflow_cms", "alpha", "purpose", "reference_mode"}
    if mode != "offline" or set(spec) - allowed or not isinstance(parameters, dict) or set(parameters) - fields:
        raise ValueError("MOSART-Urban requires offline rule_parameters")
    if parameters.get("purpose", "flood_control") != "flood_control":
        raise ValueError("MOSART-Urban extension supports flood_control")
    has_file = "inflow_statistics_file" in parameters
    if has_file == ("mean_inflow_cms" in parameters):
        raise ValueError("MOSART-Urban requires exactly one inflow_statistics_file or mean_inflow_cms")
    pins = {}
    if has_file:
        benchmark = {key: value for key, value in parameters.items() if key != "inflow_statistics_file"}
        benchmark["statistics"] = parameters["inflow_statistics_file"]
        loaded, pins = load_benchmark(benchmark, base_path, physical, simulation_start)
        settings = {key: loaded[key] for key in ("mean_inflow_cms", "alpha", "source")}
    else:
        if "reference_mode" in parameters:
            raise ValueError("reference_mode requires inflow_statistics_file")
        settings = {"mean_inflow_cms": parameters["mean_inflow_cms"],
                    "alpha": parameters.get("alpha", 0.85),
                    "source": {"kind": "explicit_mean", "mean_inflow_cms": parameters["mean_inflow_cms"]}}
    MosartUrbanBackend(physical, **settings)
    return {"rule_parameters": settings}, pins


def build_backend(settings, *, physical, **kwargs):
    """Construct an independent controller for each reservoir."""
    return MosartUrbanBackend(physical, **settings["rule_parameters"])


def rebase_agent(spec, *, base_path):
    """Resolve the optional statistics file relative to the declaring YAML."""
    parameters = spec.get("rule_parameters", {})
    if "inflow_statistics_file" in parameters:
        parameters["inflow_statistics_file"] = str(
            (Path(base_path) / parameters["inflow_statistics_file"]).resolve()
        )
