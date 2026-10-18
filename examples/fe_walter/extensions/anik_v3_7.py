"""Adapter for the frozen Anik V3.7 reservoir-policy implementation.

Example/compatibility connections: Bridges common SI observations to the pinned Anik
policy and back to SI requested actions. anik_experiment and the generic reference
adapter use it; completed physical records update the native history. Native cfs and
acre-feet conversions are explicit at this boundary.
"""

from __future__ import annotations

import hashlib
import importlib
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping

from llm_reservoir_agent.contracts import ACTION_SCHEMA_VERSION, OBSERVATION_SCHEMA_VERSION


_ANIK_SHA256 = {
    "benchmark_release.py": "f47500e3ccad55929d4069a6800ee24cb50e7605641c9ec8f03c4767d2cafc0a",
    "dkp_llm_release.py": "0045f524f55cc39551ae4eec26b69d64d8758fcbe470016ad36e6e7ed8a54203",
    "reservoir_model.py": "eb159daa1437bdad5d093873fa97eedfc7daa7e482f023b6a5070c1d67ea01c8",
    "zeroshot_llm_release.py": "e17ce6310b20902c0f6f4e11bce877e90a1ddd9bf128a7ecc0e50b5d18481dff",
}


def resolve_anik_source_dir(project_root: Path | str) -> Path:
    """Resolve the explicitly configured optional Anik source directory."""
    root = Path(project_root).resolve()
    configured = os.environ.get("HYDROOPS_ANIK_SOURCE_DIR")
    if configured is None or not configured.strip():
        raise RuntimeError(
            "optional legacy Anik reference is unavailable; set "
            "HYDROOPS_ANIK_SOURCE_DIR to the external Anik V3.7 source directory"
        )
    vendor = Path(configured).expanduser().resolve()
    if not vendor.is_dir():
        raise FileNotFoundError(
            f"HYDROOPS_ANIK_SOURCE_DIR is not an existing directory: {vendor}"
        )
    try:
        vendor.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("HYDROOPS_ANIK_SOURCE_DIR must point outside the project repository")
    return vendor


def load_anik(project_root: Path | str):
    """Verify and import the optional external Anik ``reservoir_model``."""

    vendor = resolve_anik_source_dir(project_root)
    for filename, expected in _ANIK_SHA256.items():
        path = vendor / filename
        if not path.is_file():
            raise FileNotFoundError(f"missing Anik V3.7 source: {path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Anik V3.7 source checksum mismatch: {filename}")

    module_names = tuple(Path(filename).stem for filename in _ANIK_SHA256)
    for name in module_names:
        loaded = sys.modules.get(name)
        if loaded is None:
            continue
        loaded_file = getattr(loaded, "__file__", None)
        expected_file = vendor / f"{name}.py"
        if loaded_file is None or Path(loaded_file).resolve() != expected_file:
            raise RuntimeError(
                f"stale sibling module {name!r} is loaded from {loaded_file!r}"
            )

    vendor_text = str(vendor)
    sys.path.insert(0, vendor_text)
    try:
        # Load the sibling set while its directory is explicitly first. This
        # also lets reservoir_model.build_policy import the already-verified
        # policy modules after this temporary sys.path entry is removed.
        for name in ("benchmark_release", "zeroshot_llm_release", "dkp_llm_release"):
            importlib.import_module(name)
        return importlib.import_module("reservoir_model")
    finally:
        try:
            sys.path.remove(vendor_text)
        except ValueError:
            pass


def _number(value: Any, label: str, *, nonnegative: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    if nonnegative and result < 0.0:
        raise ValueError(f"{label} must be non-negative")
    return result


def _same(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-6):
        raise ValueError(f"observation {label} does not match the Anik configuration")


class AnikPolicyAdapter:
    """Expose an Anik V3.7 policy through the reservoir-action.v1 contract."""

    policy_id = "anik_v3_7_dkp"

    def __init__(
        self,
        cfg: Any,
        policy: Any,
        *,
        consult_every_day: bool = True,
        on_commit: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        if not callable(getattr(policy, "target_release", None)):
            raise TypeError("policy must provide target_release")
        if not isinstance(consult_every_day, bool):
            raise TypeError("consult_every_day must be a boolean")
        if on_commit is not None and not callable(on_commit):
            raise TypeError("on_commit must be callable")
        self.cfg = cfg
        self.policy = policy
        self.consult_every_day = consult_every_day
        self.on_commit = on_commit
        module = sys.modules.get(type(cfg).__module__)
        if module is None or not all(
            hasattr(module, name)
            for name in ("CF_PER_ACREFT", "M3_PER_CF", "build_runtime_state")
        ):
            raise TypeError("cfg must come from the loaded Anik reservoir_model module")
        self._anik = module
        self._next_timestep = 0
        self._previous_date: date | None = None
        self._previous_inflow_cms: float | None = None
        self._previous_decision_cms: float | None = None
        self._previous_seasonal_target_ft: float | None = None
        self._pending: dict[str, Any] | None = None
        self._terminal_error: BaseException | None = None

    @property
    def network_calls(self) -> int | None:
        """Return only a counter observed by the backend/vendor policy."""

        backend = getattr(self.policy, "backend", None)
        observed = getattr(backend, "network_calls", None)
        if isinstance(observed, int) and not isinstance(observed, bool) and observed >= 0:
            return observed
        observed = getattr(self.policy, "total_backend_attempts", None)
        if isinstance(observed, int) and not isinstance(observed, bool) and observed >= 0:
            return observed
        return None

    def _fail(self, exc: BaseException) -> None:
        self._terminal_error = exc
        raise exc

    def decide(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        if self._terminal_error is not None:
            raise RuntimeError("adapter is stopped after a rejected policy decision") from self._terminal_error
        if self._pending is not None:
            raise RuntimeError("the previous decision must be committed before deciding again")
        if not isinstance(observation, Mapping):
            raise TypeError("observation must be a mapping")
        if observation.get("schema_version") != OBSERVATION_SCHEMA_VERSION:
            raise ValueError("unsupported observation schema_version")

        timestep = observation.get("timestep")
        if isinstance(timestep, bool) or not isinstance(timestep, int):
            raise TypeError("observation timestep must be an integer")
        if timestep != self._next_timestep:
            raise ValueError(f"expected observation timestep {self._next_timestep}, got {timestep}")
        timestamp = observation.get("timestamp")
        if not isinstance(timestamp, str):
            raise TypeError("observation timestamp must be a string")
        date_text = timestamp[:-9] if timestamp.endswith("T00:00:00") else timestamp
        try:
            today = date.fromisoformat(date_text)
        except ValueError as exc:
            raise ValueError("timestamp must be YYYY-MM-DD or midnight ISO format") from exc
        if date_text != today.isoformat() or timestamp not in (date_text, date_text + "T00:00:00"):
            raise ValueError("timestamp must be YYYY-MM-DD or midnight ISO format")
        if self._previous_date is not None and today != self._previous_date + timedelta(days=1):
            raise ValueError("observation dates must be consecutive")

        inflow_cms = _number(observation.get("inflow_cms"), "inflow_cms")
        upper_bound = _number(
            observation.get("release_upper_bound_cms"), "release_upper_bound_cms"
        )
        state = observation.get("state")
        if not isinstance(state, Mapping):
            raise TypeError("observation state must be a mapping")
        required = (
            "storage_m3", "dt_seconds", "capacity_m3", "dead_storage_m3",
            "minimum_release_cms", "maximum_release_cms",
        )
        missing = [name for name in required if name not in state]
        if missing:
            raise ValueError(f"observation state is missing: {missing}")
        values = {name: _number(state[name], f"state.{name}") for name in required}
        if values["dt_seconds"] != 86400.0:
            raise ValueError("AnikPolicyAdapter requires a daily 86400-second timestep")

        volume_factor = self._anik.CF_PER_ACREFT * self._anik.M3_PER_CF
        expected = {
            "capacity_m3": self.cfg.capacity_af * volume_factor,
            "dead_storage_m3": self.cfg.dead_storage_af * volume_factor,
            "minimum_release_cms": self.cfg.min_release_cfs * self._anik.CFS_TO_CMS,
            "maximum_release_cms": self.cfg.max_release_cfs * self._anik.CFS_TO_CMS,
        }
        for name, expected_value in expected.items():
            _same(values[name], expected_value, name)
        storage_m3 = values["storage_m3"]
        if storage_m3 < expected["dead_storage_m3"] or storage_m3 > expected["capacity_m3"]:
            raise ValueError("state.storage_m3 is outside configured storage bounds")
        available_cms = max(
            0.0,
            inflow_cms + (storage_m3 - expected["dead_storage_m3"]) / 86400.0,
        )
        _same(upper_bound, min(expected["maximum_release_cms"], available_cms), "release_upper_bound_cms")

        timestamp_pd = self._anik.pd.Timestamp(today)
        storage_af = storage_m3 / volume_factor
        runtime_state = self._anik.build_runtime_state(
            self.cfg, timestamp_pd, storage_af, "daily"
        )
        runtime_state["step_days"] = 1
        runtime_state["storage_af_for_elevation"] = (
            lambda elevation, _cfg=self.cfg: self._anik.elevation_to_storage_af(
                _cfg, elevation
            )
        )
        runtime_state["physically_available_release_cfs"] = (
            available_cms / self._anik.CFS_TO_CMS
        )
        current_target = runtime_state.get("seasonal_target_ft")
        target_changed = (
            current_target is not None
            and self._previous_seasonal_target_ft is not None
            and abs(current_target - self._previous_seasonal_target_ft) > 0.01
        )
        consult = (
            self.consult_every_day
            or self._previous_decision_cms is None
            or bool(getattr(self.policy, "last_decision_failed", False))
            or target_changed
            or self._anik.needs_llm_consultation(
                inflow_cms, self._previous_inflow_cms
            )
        )

        try:
            if consult:
                request_cms = self.policy.target_release(
                    timestamp_pd,
                    inflow_cms,
                    storage_m3,
                    runtime_state=runtime_state,
                )
                if bool(getattr(self.policy, "last_decision_failed", False)):
                    raise RuntimeError(
                        f"Anik backend failed on {today.isoformat()}; physics was not applied"
                    )
            else:
                request_cms = self._previous_decision_cms
                recorder = getattr(self.policy, "record_reuse", None)
                if callable(recorder):
                    recorder(
                        timestamp_pd,
                        inflow_cms,
                        storage_m3,
                        request_cms,
                        runtime_state=runtime_state,
                    )
            request_cms = _number(request_cms, "Anik policy release")
        except Exception as exc:
            self._fail(exc)

        bounded_cfs = min(
            max(request_cms / self._anik.CFS_TO_CMS, self.cfg.min_release_cfs),
            self.cfg.max_release_cfs,
        )
        decision_cms = bounded_cfs * self._anik.CFS_TO_CMS
        self._pending = {
            "date": timestamp_pd,
            "date_text": today.isoformat(),
            "timestep": timestep,
            "inflow_cms": inflow_cms,
            "storage_start_m3": storage_m3,
            "decision_release_cms": decision_cms,
            "seasonal_target_ft": current_target,
        }
        return {
            "schema_version": ACTION_SCHEMA_VERSION,
            "release_cms": decision_cms,
        }

    def record_transition(self, record: Mapping[str, Any]) -> None:
        """Commit one completed physics transition to the original policy."""

        if self._pending is None:
            raise RuntimeError("no policy decision is pending")
        if not isinstance(record, Mapping):
            raise TypeError("transition record must be a mapping")
        observation = record.get("observation")
        action = record.get("action")
        transition = record.get("transition")
        if not all(isinstance(item, Mapping) for item in (observation, action, transition)):
            raise ValueError("transition record requires observation, action, and transition mappings")
        pending = self._pending
        if observation.get("timestep") != pending["timestep"]:
            raise ValueError("transition timestep does not match the pending decision")
        if observation.get("timestamp") not in (
            pending["date_text"], pending["date_text"] + "T00:00:00"
        ):
            raise ValueError("transition timestamp does not match the pending decision")
        action_release = _number(action.get("release_cms"), "action.release_cms")
        _same(action_release, pending["decision_release_cms"], "action.release_cms")
        storage_end = _number(transition.get("storage_end_m3"), "transition.storage_end_m3")
        if "storage_start_m3" in transition:
            _same(
                _number(transition["storage_start_m3"], "transition.storage_start_m3"),
                pending["storage_start_m3"],
                "transition.storage_start_m3",
            )
        controlled = _number(
            transition.get("controlled_release_cms"),
            "transition.controlled_release_cms",
        )
        spill = _number(transition.get("spill_cms"), "transition.spill_cms")
        total = _number(transition.get("total_outflow_cms"), "transition.total_outflow_cms")
        _same(total, controlled + spill, "transition.total_outflow_cms")
        if "inflow_cms" in transition:
            _same(
                _number(transition["inflow_cms"], "transition.inflow_cms"),
                pending["inflow_cms"],
                "transition.inflow_cms",
            )
        if "target_release_cms" in transition:
            _same(
                _number(transition["target_release_cms"], "transition.target_release_cms"),
                pending["decision_release_cms"],
                "transition.target_release_cms",
            )

        recorder = getattr(self.policy, "record_outcome", None)
        if callable(recorder):
            recorder(
                date=pending["date"],
                decision_release_cms=pending["decision_release_cms"],
                storage_end_m3=storage_end,
                inflow_cms=pending["inflow_cms"],
                implemented_release_cms=total,
            )
        self._previous_date = pending["date"].date()
        self._previous_inflow_cms = pending["inflow_cms"]
        self._previous_decision_cms = pending["decision_release_cms"]
        self._previous_seasonal_target_ft = pending["seasonal_target_ft"]
        self._next_timestep += 1
        self._pending = None
        if self.on_commit is not None:
            self.on_commit(record)
