"""Pure FE Walter prompt, retrieval, response, and diagnostic helpers.

The formatter and retriever are attributed ports of the corresponding Anik V3.7
pure functions.  They intentionally contain no provider, driver, simulation, or
vendor-module imports.  The original vendor implementation remains a test oracle.
"""

from __future__ import annotations

from bisect import bisect_left
import csv
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping

from llm_reservoir_agent.audit import json_snapshot
from llm_reservoir_agent.context import ContextValue, DecisionContext


CFS_TO_CMS = 0.028316847
ACREFT_TO_M3 = 1233.4818
PHYSICAL_ACREFT_TO_M3 = 43_560.0 * CFS_TO_CMS
ACTION_SCHEMA = "reservoir-action.v1"

NEUTRAL_PROPERTIES = {
    "applicable_target_ft": {"type": "number", "description":
        "Operation-target water level (ft NGVD29) that applies to this interval, read from the operation target"},
    "pool_position": {"type": "string", "enum": ["below_target", "at_target", "above_target"],
        "description": "Beginning water level compared with applicable_target_ft"},
    "intended_storage_direction": {"type": "string", "enum": ["increase", "hold", "decrease"],
        "description": "How you intend storage to change over this interval"},
    "release_relation_to_inflow": {"type": "string", "enum": ["below_inflow", "equal_to_inflow", "above_inflow"],
        "description": "How your release will compare with this interval's inflow"},
}
NEUTRAL_FIELDS = list(NEUTRAL_PROPERTIES)
ZERO_SCHEMA = {
    "type": "object",
    "properties": {
        **NEUTRAL_PROPERTIES,
        "reasoning": {"type": "string", "description":
            "One or two sentences: the storage change your release will cause, and why it moves toward the target"},
        "release_cfs": {"type": "number", "description":
            "Target mean release for the interval in cubic feet per second"},
    },
    "required": NEUTRAL_FIELDS + ["reasoning", "release_cfs"],
    "additionalProperties": False,
}
DKP_MODES = [
    "pass_inflow", "store_toward_target", "draw_toward_target",
    "minimum_release", "flood_control", "post_flood_drawdown",
    "recreation_plan", "missing_information_fallback",
]


def dkp_schema(include_missing_inputs: bool) -> dict[str, Any]:
    properties = {
        **NEUTRAL_PROPERTIES,
        "operating_mode": {"type": "string", "enum": list(DKP_MODES)},
        "rules_applied": {"type": "array", "items": {"type": "string"},
                          "description": "Exact retrieved DKP section headings used"},
        "missing_inputs": {"type": "array", "items": {"type": "string"},
                           "description": "Unavailable inputs that limit full WCM operation"},
        "reasoning": {"type": "string", "description":
            "Brief rule citation and water-balance explanation: the storage change the release will cause"},
        "release_cfs": {"type": "number", "description": "Target mean release for the interval in cfs"},
    }
    required = NEUTRAL_FIELDS + ["operating_mode", "rules_applied", "missing_inputs", "reasoning", "release_cfs"]
    if not include_missing_inputs:
        del properties["missing_inputs"]
        properties["operating_mode"]["enum"].remove("missing_information_fallback")
        required.remove("missing_inputs")
    return {"type": "object", "properties": properties, "required": required,
            "additionalProperties": False}


def _number(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    if nonnegative and result < 0:
        raise ValueError(f"{label} must be non-negative")
    return result


def _strict_schema(value: Any, schema: Mapping[str, Any], label: str = "native response") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    properties = schema["properties"]
    if set(value) != set(schema["required"]):
        raise ValueError(f"{label} fields do not match the declared schema")
    for key, item in value.items():
        rule = properties[key]
        kind = rule["type"]
        if kind == "number":
            _number(item, key)
        elif kind == "string":
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{key} must be non-empty text")
        elif kind == "array":
            if not isinstance(item, list) or any(not isinstance(x, str) for x in item):
                raise ValueError(f"{key} must be a list of strings")
        else:
            raise ValueError("unsupported native schema")
        if "enum" in rule and item not in rule["enum"]:
            raise ValueError(f"{key} has an invalid enum value")
    return json_snapshot(value)


@dataclass(frozen=True)
class CaseProfile:
    path: Path
    data: Mapping[str, Any]
    curve: tuple[tuple[float, float], ...]
    source_hashes: Mapping[str, str]

    @property
    def profile_id(self) -> str:
        return self.data["profile_id"]

    def storage_to_elevation(self, storage_af: float) -> float | None:
        storages = [row[1] for row in self.curve]
        if storage_af < storages[0] or storage_af > storages[-1]:
            return None
        index = bisect_left(storages, storage_af)
        if storages[index] == storage_af:
            return self.curve[index][0]
        e0, s0 = self.curve[index - 1]
        e1, s1 = self.curve[index]
        return e0 + (storage_af - s0) * (e1 - e0) / (s1 - s0)

    def elevation_to_storage(self, elevation_ft: float) -> float | None:
        elevations = [row[0] for row in self.curve]
        if elevation_ft < elevations[0] or elevation_ft > elevations[-1]:
            return None
        index = bisect_left(elevations, elevation_ft)
        if elevations[index] == elevation_ft:
            return self.curve[index][1]
        e0, s0 = self.curve[index - 1]
        e1, s1 = self.curve[index]
        return s0 + (elevation_ft - e0) * (s1 - s0) / (e1 - e0)

    def target_period(self, day: date) -> Mapping[str, Any]:
        key = day.strftime("%m-%d")
        for period in self.data["target_periods"]:
            start, end = period["start"], period["end"]
            if (start <= end and start <= key <= end) or (start > end and (key >= start or key <= end)):
                return period
        raise ValueError("target periods do not cover the calendar")


def case_profile_path() -> Path:
    return (Path(__file__).resolve().parents[1] / "profiles" / "anik_v3_7.json").resolve()


def load_case_profile(runtime_root: Path | str) -> CaseProfile:
    path = case_profile_path()
    blob = path.read_bytes()
    data = json.loads(blob.decode("utf-8"))
    if data.get("schema_version") != "anik-case-profile.v1" or data.get("profile_id") != "fe_walter":
        raise ValueError("invalid FE Walter case profile")
    curve_path = (path.parent / data["elevation_storage_csv"]).resolve()
    curve_blob = curve_path.read_bytes()
    curve_hash = hashlib.sha256(curve_blob).hexdigest()
    if curve_hash != data["elevation_storage_sha256"]:
        raise ValueError("FE Walter elevation-storage curve checksum mismatch")
    with curve_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["elevation_ft_ngvd29", "storage_acft"]:
            raise ValueError("FE Walter curve has an invalid header")
        curve = tuple((float(row["elevation_ft_ngvd29"]), float(row["storage_acft"])) for row in reader)
    if len(curve) < 2 or any(b[0] <= a[0] or b[1] < a[1] for a, b in zip(curve, curve[1:])):
        raise ValueError("FE Walter curve must be monotone")
    return CaseProfile(path, data, curve, {
        "case_profile": hashlib.sha256(blob).hexdigest(),
        "elevation_storage_curve": curve_hash,
    })


def read_system_prompt(profile: CaseProfile, method: str, settings: Mapping[str, Any]) -> tuple[str, str, str]:
    original = profile.data["default_system_prompts"][method]
    original_path = (profile.path.parent / original["path"]).resolve()
    original_blob = original_path.read_bytes()
    if hashlib.sha256(original_blob).hexdigest() != original["sha256"]:
        raise ValueError("serialized default system prompt checksum mismatch")
    original_text = original_blob.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    if "system_prompt" not in settings:
        return original_text, original["sha256"], "serialized_profile"
    source = Path(settings["system_prompt"])
    blob = source.read_bytes()
    source_hash = hashlib.sha256(blob).hexdigest()
    if source_hash != settings["system_prompt_sha256"]:
        raise ValueError("system_prompt file changed after validation")
    text = blob.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    if settings.get("system_prompt_mode", "original") == "original" and text != original_text:
        raise ValueError("system_prompt differs from original builder; use system_prompt_mode: custom for a variant")
    return text, original["sha256"], "file"


def _date(value: str) -> date:
    text = value[:10]
    result = date.fromisoformat(text)
    if value not in (text, text + "T00:00:00", text + "T00:00:00Z"):
        raise ValueError("reference timestamp must be a midnight ISO date")
    return result


def _volume_text(cfs: float, days: int) -> str:
    return (f"{cfs * 86400 * days:,.0f} cubic feet "
            f"(= {cfs * days * 1.98347:,.0f} acre-feet) over {days} days")


def _state_core(profile: CaseProfile, settings: Mapping[str, Any], day: date,
                inflow_cfs: float, storage_af: float, runtime: Mapping[str, Any],
                history: list[dict[str, Any]]) -> list[str]:
    days = int(runtime.get("step_days") or 1)
    lines = [
        f"Date: {day:%Y-%m-%d} ({day:%B}, day {day.timetuple().tm_yday} of the year)",
        f"1. Today's inflow: {inflow_cfs:,.1f} cfs (= {_volume_text(inflow_cfs, days)})",
    ]
    pool = runtime.get("pool_elevation_ft")
    lines.append(f"2. Water level at beginning of interval: {pool:.2f} ft NGVD29" if pool is not None
                 else "2. Water level at beginning of interval: unavailable")
    lines.append("3. Previous simulated release decisions (and what was actually released):")
    if history:
        for item in history:
            decided = item["decision_release_cfs"]
            implemented = item.get("implemented_release_cfs", decided)
            line = (f"   {item['date']}: decided {decided:,.1f} cfs; actually released "
                    f"{implemented:,.1f} cfs (= {_volume_text(implemented, 1)})")
            if implemented < decided - 0.5:
                line += " - limited by the water available"
            elif implemented > decided + 0.5:
                line += " - includes uncontrolled spill"
            lines.append(line)
    else:
        lines.append("   None (first simulated step).")
    lines.append(f"4. Number of days in this decision interval: {days}")
    if settings["prompt_storage"]:
        lines.append(f"5. Storage at beginning of interval: {storage_af * 43560:,.0f} cubic feet "
                     f"(= {storage_af:,.0f} acre-feet)")
        available = runtime.get("physically_available_release_cfs")
        if available is not None and not settings["hide_availability_line"]:
            lines.append(f"6. Maximum release given the water available this interval: {available:,.1f} cfs "
                         f"(= this interval's inflow plus storage above the inactive pool, spread over {days} days). "
                         "This is a hard ceiling, not a target: requesting more will be reduced by the water balance regardless of the reason.")
    return lines


_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*")
_DIGIT_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(_DIGIT_COMMA_RE.sub("", text.lower()))


class DKPRetriever:
    """Attributed pure port of the Anik V3.7 heading/TF-IDF retriever."""

    def __init__(self, path: Path):
        self.path = path
        self.sections = self._split_sections(path.read_text(encoding="utf-8"), 80)
        self.layout = "sections"
        if (not any(h == "Core Rule Priority and Release Constraints" for h, _ in self.sections)
                and any(h.startswith("§2.3 Decision Rules") for h, _ in self.sections)):
            self.sections = self._split_v12_rules(self.sections)
            self.layout = "v1.2-rules"

    @staticmethod
    def _split_sections(text: str, min_chars: int) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        heading, buffer, in_fence = "Preamble", [], False
        for line in text.splitlines():
            if line.strip().startswith("```"):
                in_fence = not in_fence
                buffer.append(line)
            elif not in_fence and re.match(r"^#{1,6}\s+", line):
                sections.append((heading, "\n".join(buffer).strip()))
                heading, buffer = line.strip("# ").strip(), []
            else:
                buffer.append(line)
        sections.append((heading, "\n".join(buffer).strip()))
        merged: list[tuple[str, str]] = []
        for heading, body in sections:
            if merged and len(merged[-1][1]) < min_chars:
                old_heading, old_body = merged.pop()
                heading, body = f"{old_heading} / {heading}", f"{old_body}\n{body}".strip()
            merged.append((heading, body))
        return [(heading, body) for heading, body in merged if body]

    @staticmethod
    def _split_v12_rules(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
        result = []
        for heading, body in sections:
            if not heading.startswith("§2.3 Decision Rules"):
                result.append((heading, body))
                continue
            lines = body.splitlines()
            starts = [i for i, line in enumerate(lines) if line.strip().startswith("**R-")]
            if starts and starts[0] > 0 and "\n".join(lines[:starts[0]]).strip():
                result.append((heading, "\n".join(lines[:starts[0]]).strip()))
            for position, start in enumerate(starts):
                stop = starts[position + 1] if position + 1 < len(starts) else len(lines)
                title = re.sub(r"\*\*", "", lines[start].strip()).strip()
                result.append((title, "\n".join(lines[start + 1:stop]).strip()))
        return result

    def operational(self, day: date, runtime: Mapping[str, Any], include_missing: bool) -> list[tuple[str, str]]:
        excluded = ("Fallback Policy", "R-DOWNSTREAM", "§2.4.4 Downstream Station Ratings", "§2.4.6 Time of Travel Schedule")
        def find(prefix: str):
            return next(((h, b) for h, b in self.sections if h.startswith(prefix)
                         and not h.startswith(excluded)), None)
        selected = [item for item in (find(p) for p in ("R-RELEASE", "R-MINNORM", "R-ATSITE", "R-ZONE")) if item]
        if include_missing:
            selected += [(h, b) for h, b in self.sections if h == "Fallback Policy"]
        pool, target = runtime.get("pool_elevation_ft"), runtime.get("seasonal_target_start_ft")
        flood = (float(runtime.get("flood_storage_percent") or 0) > 0 and pool is not None
                 and target is not None and pool > target + 0.5)
        if flood:
            item = find("R-PLAN")
            if item:
                selected.append(item)
        if 4 <= day.month <= 10 and not flood:
            item = find("R-RECREATION")
            if item:
                selected.append(item)
        return selected


class NativePromptFormatter:
    """Build one exact native user message as a ConfiguredBackend prompt callback."""

    def __init__(self, profile: CaseProfile, settings: Mapping[str, Any], dkp_path: Path | None):
        self.profile, self.settings = profile, settings
        self.history: list[dict[str, Any]] = []
        self.retriever = None if dkp_path is None else DKPRetriever(dkp_path)
        self.last_runtime: dict[str, Any] | None = None
        self.last_variables: dict[str, Any] | None = None
        self.last_headings: list[str] = []

    def runtime(self, observation: Mapping[str, Any]) -> tuple[date, float, float, dict[str, Any]]:
        day = _date(observation["timestamp"])
        state = observation["state"]
        inflow_cfs = _number(observation["inflow_cms"], "inflow_cms", nonnegative=True) / CFS_TO_CMS
        storage_af = _number(state["storage_m3"], "state.storage_m3", nonnegative=True) / ACREFT_TO_M3
        period = self.profile.target_period(day)
        target = float(period["target_ft"])
        pool = self.profile.storage_to_elevation(storage_af)
        target_storage = self.profile.elevation_to_storage(target)
        bottom = self.profile.elevation_to_storage(self.profile.data["flood_pool_bottom_ft"])
        top = self.profile.elevation_to_storage(self.profile.data["flood_pool_top_ft"])
        runtime = {
            "timestep": "daily", "step_days": 1, "pool_elevation_ft": pool,
            "seasonal_target_start_ft": target, "seasonal_target_mean_ft": target,
            "seasonal_target_ft": target, "seasonal_target_storage_af": target_storage,
            "target_period": period["id"],
            "flood_storage_percent": 100 * min(max((storage_af - bottom) / (top - bottom), 0), 1),
            "runtime_missing_inputs": list(self.profile.data["runtime_missing_inputs"]),
            "physically_available_release_cfs": max(
                0.0,
                observation["inflow_cms"]
                + (state["storage_m3"] - state["dead_storage_m3"]) / state["dt_seconds"],
            ) / CFS_TO_CMS,
        }
        return day, inflow_cfs, storage_af, runtime

    def __call__(self, context: DecisionContext) -> ContextValue:
        observation = dict(context.observation)
        day, inflow_cfs, storage_af, runtime = self.runtime(observation)
        lines = _state_core(self.profile, self.settings, day, inflow_cfs, storage_af, runtime, self.history)
        if self.settings["method"] == "dkp":
            item = ((7 if not self.settings["hide_availability_line"] else 6)
                    if self.settings["prompt_storage"] else 5)
            minimum, maximum = self.profile.data["minimum_release_cfs"], self.profile.data["maximum_release_cfs"]
            lines.append(f"{item}. Release limits for this interval (water control manual): {minimum:,.0f}-{maximum:,.0f} cfs "
                         f"(= {minimum * 86400:,.0f}-{maximum * 86400:,.0f} cubic feet over 1 days)")
            assert self.retriever is not None
            excerpts = self.retriever.operational(day, runtime, not self.settings["dkp_no_missing_inputs"])
            self.last_headings = [heading for heading, _ in excerpts]
            lines += ["", "Retrieved DKP sections relevant to current conditions:"]
            for index, (heading, body) in enumerate(excerpts, 1):
                lines += [f"\n--- DKP excerpt {index}: {heading} ---", body]
            lines += ["", f"The simulated year is {day.year}. Check the year of every dated DKP instruction before applying it.",
                      "Apply these DKP rules to decide the mean release for this interval (cfs)."]
        else:
            self.last_headings = []
            lines += ["", "Decide the mean release for this interval (cfs)."]
        prompt = "\n".join(lines)
        self.last_runtime = runtime
        self.last_variables = {
            "schema_version": "reservoir-daily-inputs.v1", "reservoir_profile": self.profile.profile_id,
            "date": day.isoformat(), "timestep": observation["timestep"],
            "inflow_cms": observation["inflow_cms"], "inflow_cfs": inflow_cfs,
            "storage_start_m3": observation["state"]["storage_m3"], "storage_start_af": storage_af,
            "pool_elevation_start_ft": runtime["pool_elevation_ft"],
            "native_history": json_snapshot(self.history),
            "history_semantics": "prior requested and implemented outflows; appended after physical commit",
            "target_period": runtime["target_period"],
        }
        return ContextValue(prompt, {"source": "fe_walter.native_prompt", "date": day.isoformat()})

    def commit(self, record: Mapping[str, Any]) -> None:
        observation, action, transition = record["observation"], record["action"], record["transition"]
        self.history.append({
            "date": observation["timestamp"][:10],
            "inflow_cfs": observation["inflow_cms"] / CFS_TO_CMS,
            "decision_release_cfs": action["release_cms"] / CFS_TO_CMS,
            "implemented_release_cfs": transition["total_outflow_cms"] / CFS_TO_CMS,
            "storage_end_af": transition["storage_end_m3"] / ACREFT_TO_M3,
        })
        self.history[:] = self.history[-2:]


class NativeResponseParser:
    parser_id = "original-v3.7-cfs"

    def __init__(self, method: str, include_missing: bool, minimum_cms: float, maximum_cms: float):
        self.method, self.include_missing = method, include_missing
        self.minimum_cms, self.maximum_cms = minimum_cms, maximum_cms
        self.schema = ZERO_SCHEMA if method == "zeroshot" else dkp_schema(include_missing)

    def __call__(self, candidate: Any) -> dict[str, Any]:
        decision = _strict_schema(candidate, self.schema)
        release = decision["release_cfs"] * CFS_TO_CMS
        release = min(max(release, self.minimum_cms), self.maximum_cms)
        return {"schema_version": ACTION_SCHEMA, "release_cms": release}


def _flow_relation(release: float, inflow: float) -> tuple[str, str, float]:
    tolerance = max(1.0, 1e-9 * max(abs(inflow), 1.0))
    if release < inflow - tolerance:
        return "below_inflow", "increase", tolerance
    if release > inflow + tolerance:
        return "above_inflow", "decrease", tolerance
    return "equal_to_inflow", "hold", tolerance


def _physics_audit(decision: Mapping[str, Any], *, inflow_cfs: float, release_cfs: float,
                   pool_ft: float | None, target_ft: float | None,
                   min_release_cfs: float, max_release_cfs: float,
                   prompt_storage: bool, target_error_start_af: float | None,
                   target_error_end_af: float | None, target_tolerance_ft: float,
                   requested_release_cfs: float,
                   physically_available_cfs: float | None) -> dict[str, list[str]]:
    """CASE-local port of Anik V3.7's shared, record-only physics audit."""
    hard: list[str] = []
    hard_unattributed: list[str] = []
    policy: list[str] = []
    warnings: list[str] = []
    if (requested_release_cfs < min_release_cfs - 0.1
            or requested_release_cfs > max_release_cfs + 0.1):
        hard.append(
            f"requested release {requested_release_cfs:,.1f} cfs outside configured bounds "
            f"[{min_release_cfs:,.0f}, {max_release_cfs:,.0f}] cfs"
        )
    if (physically_available_cfs is not None
            and requested_release_cfs > physically_available_cfs + 0.1):
        message = (
            f"requested release {requested_release_cfs:,.1f} cfs exceeds physically "
            f"available {physically_available_cfs:,.1f} cfs"
        )
        if prompt_storage:
            hard.append(message)
        else:
            hard_unattributed.append(message + " (not attributed: storage not in prompt)")

    result = {
        "hard_physics": hard,
        "hard_physics_unattributed": hard_unattributed,
        "policy": policy,
        "warnings": warnings,
    }
    relation, direction, tolerance = _flow_relation(release_cfs, inflow_cfs)
    if pool_ft is None or target_ft is None:
        warnings.append("physics audit skipped: pool or target unavailable")
        return result
    if pool_ft < target_ft - target_tolerance_ft:
        position = "below_target"
    elif pool_ft > target_ft + target_tolerance_ft:
        position = "above_target"
    else:
        position = "at_target"

    try:
        stated_target = float(decision.get("applicable_target_ft"))
    except (TypeError, ValueError):
        policy.append("applicable_target_ft missing or not numeric")
        stated_target = None
    if stated_target is not None and abs(stated_target - target_ft) > target_tolerance_ft:
        policy.append(
            f"stated applicable_target_ft {stated_target:.1f} differs from the operation "
            f"target {target_ft:.1f} for this date"
        )
    if decision.get("pool_position") != position:
        policy.append(
            f"pool_position '{decision.get('pool_position')}' contradicts the water level "
            f"({pool_ft:.2f} ft vs target {target_ft:.1f} ft)"
        )
    if decision.get("release_relation_to_inflow") != relation:
        policy.append(
            f"release_relation_to_inflow '{decision.get('release_relation_to_inflow')}' "
            f"contradicts release {release_cfs:,.1f} vs inflow {inflow_cfs:,.1f} cfs"
        )
    if decision.get("intended_storage_direction") != direction:
        policy.append(
            f"intended_storage_direction '{decision.get('intended_storage_direction')}' "
            f"contradicts the water balance (storage will {direction})"
        )
    if (position == "below_target" and inflow_cfs > min_release_cfs + tolerance
            and direction != "increase"):
        policy.append(
            "pool below target but release does not retain inflow, so storage cannot move "
            "toward the target"
        )
    if (position == "above_target" and inflow_cfs < max_release_cfs - tolerance
            and direction != "decrease"):
        policy.append("pool above target but release does not draw storage down")
    if (prompt_storage and position != "at_target"
            and target_error_start_af is not None and target_error_end_af is not None
            and target_error_end_af >= target_error_start_af - 0.5):
        policy.append("release does not reduce the target-storage error")
    return result


def _dkp_rule_audit(decision: Mapping[str, Any], *, day: date, requested_release_cfs: float,
                    release_cfs: float, inflow_cfs: float, storage_af: float,
                    pool_ft: float | None, target_ft: float | None,
                    target_storage_af: float | None, step_days: int,
                    min_release_cfs: float, max_release_cfs: float,
                    prompt_storage: bool, include_missing_inputs: bool,
                    expected_missing: list[str], headings: list[str],
                    target_tolerance_ft: float = 0.5) -> tuple[list[str], list[str], dict[str, float | None]]:
    """Port the DKP-only Anik diagnostics without importing the vendored oracle."""
    failures: list[str] = []
    warnings: list[str] = []
    mode = str(decision.get("operating_mode", ""))
    rules = decision.get("rules_applied")
    missing = decision.get("missing_inputs")
    reasoning = str(decision.get("reasoning", ""))
    if not mode:
        failures.append("missing operating_mode")
    def cites_retrieved_rule(rule: Any) -> bool:
        cited = str(rule).strip()
        for heading in headings:
            if cited == heading:
                return True
            prefix = heading.split(" (")[0].strip()
            if cited == prefix or cited in [name.strip() for name in prefix.split(",")]:
                return True
        return False
    if not isinstance(rules, list) or not rules:
        failures.append("rules_applied must contain at least one DKP section heading")
    elif any(not cites_retrieved_rule(rule) for rule in rules):
        failures.append("every rules_applied entry must be an exact retrieved DKP section heading")
    if include_missing_inputs and not isinstance(missing, list):
        failures.append("missing_inputs must be a JSON list")
    if requested_release_cfs < min_release_cfs or requested_release_cfs > max_release_cfs:
        failures.append("LLM release violated configured bounds and required clipping")

    storage_change_af = (
        (inflow_cfs - release_cfs) * CFS_TO_CMS * step_days * 86400.0 / ACREFT_TO_M3
    )
    projected_end_storage_af = storage_af + storage_change_af
    target_error_start_af = target_error_end_af = None
    if target_storage_af is not None:
        target_error_start_af = abs(target_storage_af - storage_af)
        target_error_end_af = abs(target_storage_af - projected_end_storage_af)

    if mode == "store_toward_target":
        if release_cfs >= inflow_cfs - 0.1:
            failures.append("store_toward_target mode does not retain inflow")
        if (prompt_storage and target_error_start_af is not None
                and target_error_end_af >= target_error_start_af - 0.5):
            failures.append("store_toward_target mode does not reduce target error")
        if (pool_ft is not None and target_ft is not None
                and pool_ft > target_ft + target_tolerance_ft):
            warnings.append("store_toward_target mode selected while pool is above target")
    elif mode in ("draw_toward_target", "post_flood_drawdown"):
        if release_cfs <= inflow_cfs + 0.1:
            failures.append(f"{mode} mode does not release more than inflow")
        if (prompt_storage and target_error_start_af is not None
                and target_error_end_af >= target_error_start_af - 0.5):
            failures.append(f"{mode} mode does not reduce target error")
        if (pool_ft is not None and target_ft is not None
                and pool_ft < target_ft - target_tolerance_ft):
            warnings.append(f"{mode} mode selected while pool is below target")
    elif mode == "pass_inflow":
        pass_tolerance = max(1.0, 1e-9 * max(abs(inflow_cfs), 1.0))
        if abs(release_cfs - inflow_cfs) > pass_tolerance:
            failures.append("pass_inflow mode release is not approximately equal to inflow")
        recreation_hold = (
            pool_ft is not None
            and 1365.0 - target_tolerance_ft <= pool_ft <= 1370.0
            and (day.month == 6 or (day.month == 5 and day.day >= 10))
        )
        if (pool_ft is not None and target_ft is not None
                and pool_ft < target_ft - target_tolerance_ft
                and inflow_cfs > min_release_cfs + pass_tolerance
                and not recreation_hold):
            failures.append("below-target pass_inflow cannot raise storage toward the target")

    trace = " ".join(str(item) for item in (rules or [])) + " " + reasoning
    missing_text = " ".join(str(item) for item in (missing or []))
    applicability_trace = trace + " " + missing_text
    if re.search(r"RESEARCH-TARGET-TRACKING|target[-_ ]tracking release", trace, re.IGNORECASE):
        failures.append("prohibited target-tracking controller cited")
    if day.year != 2014 and 4 <= day.month <= 10:
        calendar_context = re.search(
            r"(?:recreation|whitewater|boating|calendar|schedul|weekend|weekday|holiday|"
            r"memorial|labor\s+day|event\s+date)", trace, re.IGNORECASE,
        )
        applies_2014_calendar = calendar_context and re.search(
            r"(?:weekday|weekend|May\s+(?:9|10)|(?:225|250|750|1,?000)\s*cfs)",
            trace, re.IGNORECASE,
        )
        disclaims_2014_calendar = re.search(
            r"(?:not\s+applicable|not\s+appl(?:y|ied)|not\s+used|year[- ]specific|"
            r"2014\s+specific|calendar\s+(?:is\s+)?(?:unknown|unavailable|missing)|"
            r"outside\s+2014)", applicability_trace, re.IGNORECASE,
        )
        if applies_2014_calendar and not disclaims_2014_calendar:
            failures.append("2014-only recreation calendar applied outside 2014")
        if mode == "recreation_plan" and not re.search(
            r"(?:annual|year[- ]specific|2014).*(?:calendar|schedule)|"
            r"(?:calendar|schedule).*(?:unknown|unavailable|missing)",
            missing_text if include_missing_inputs else applicability_trace,
            re.IGNORECASE,
        ):
            warnings.append(
                "recreation_plan outside 2014 does not disclose the missing annual "
                "recreation calendar"
            )
    if include_missing_inputs and expected_missing and isinstance(missing, list) and not missing:
        warnings.append("known unavailable runtime inputs were not disclosed")
    metrics = {
        "storage_change_af": storage_change_af,
        "projected_end_storage_af": projected_end_storage_af,
        "target_error_start_af": target_error_start_af,
        "target_error_end_af": target_error_end_af,
    }
    return failures, warnings, metrics


def native_audit(method: str, decision: Mapping[str, Any], observation: Mapping[str, Any],
                 action: Mapping[str, Any], runtime: Mapping[str, Any], settings: Mapping[str, Any],
                 headings: list[str], profile: CaseProfile) -> dict[str, Any]:
    """Diagnostic port: preserve FAIL findings without revising the model answer."""
    inflow = observation["inflow_cms"] / CFS_TO_CMS
    requested = decision["release_cfs"]
    release = action["release_cms"] / CFS_TO_CMS
    pool, target = runtime.get("pool_elevation_ft"), runtime.get("seasonal_target_ft")
    day = date.fromisoformat(observation["timestamp"][:10])
    minimum, maximum = profile.data["minimum_release_cfs"], profile.data["maximum_release_cfs"]
    storage_af = observation["state"]["storage_m3"] / ACREFT_TO_M3
    step_days = int(runtime.get("step_days") or 1)
    storage_change_af = (
        (inflow - release) * step_days * 1.98347
        if method == "zeroshot"
        else (inflow - release) * CFS_TO_CMS * step_days * 86400.0 / ACREFT_TO_M3
    )
    target_storage = runtime.get("seasonal_target_storage_af")
    target_error_start = target_error_end = None
    if target_storage is not None:
        target_error_start = abs(target_storage - storage_af)
        target_error_end = abs(target_storage - (storage_af + storage_change_af))
    physics = _physics_audit(
        decision, inflow_cfs=inflow, release_cfs=release, pool_ft=pool, target_ft=target,
        min_release_cfs=minimum, max_release_cfs=maximum,
        prompt_storage=settings["prompt_storage"], target_error_start_af=target_error_start,
        target_error_end_af=target_error_end, target_tolerance_ft=0.5,
        requested_release_cfs=requested,
        physically_available_cfs=runtime.get("physically_available_release_cfs"),
    )
    hard = physics["hard_physics"]
    hard_unattributed = physics["hard_physics_unattributed"]
    policy = physics["policy"]
    warnings = list(physics["warnings"])
    physics_failures = hard + policy
    failures = list(physics_failures)
    rule_failures: list[str] = []
    metrics = {
        "storage_change_af": storage_change_af,
        "projected_end_storage_af": storage_af + storage_change_af,
        "target_error_start_af": target_error_start,
        "target_error_end_af": target_error_end,
    }
    if method == "dkp":
        rule_failures, rule_warnings, metrics = _dkp_rule_audit(
            decision, day=day, requested_release_cfs=requested, release_cfs=release,
            inflow_cfs=inflow, storage_af=storage_af, pool_ft=pool, target_ft=target,
            target_storage_af=target_storage, step_days=step_days,
            min_release_cfs=minimum, max_release_cfs=maximum,
            prompt_storage=settings["prompt_storage"],
            include_missing_inputs=not settings["dkp_no_missing_inputs"],
            expected_missing=list(runtime.get("runtime_missing_inputs") or []),
            headings=headings,
        )
        failures += [item for item in rule_failures if item not in physics_failures]
        warnings += rule_warnings
    else:
        metrics["target_error_start_af"] = (
            None if target_error_start is None else round(target_error_start, 1)
        )
        metrics["target_error_end_af"] = (
            None if target_error_end is None else round(target_error_end, 1)
        )
    status = "FAIL" if failures else "WARN" if warnings or hard_unattributed else "PASS"
    result = {
        "date": observation["timestamp"][:10], "outcome": "llm",
        "inflow_cfs": round(inflow, 1), "storage_start_af": round(observation["state"]["storage_m3"] / ACREFT_TO_M3, 1),
        "llm_release_cfs_raw": round(requested, 1), "decision_release_cfs": round(release, 1),
        **json_snapshot(decision), "audit_status": status, "audit_failures": failures,
        "audit_warnings": warnings, "hard_physics_failures": hard,
        "hard_physics_unattributed": hard_unattributed, "policy_failures": policy,
        "request_physically_feasible": not (hard or hard_unattributed),
        "audit_revision_count": 0,
        **metrics,
    }
    if method == "dkp":
        physics_status = (
            "FAIL" if physics_failures
            else "WARN" if physics["warnings"] or hard_unattributed
            else "PASS"
        )
        result.update(physics_audit_status=physics_status,
                      physics_audit_failures=physics_failures, dkp_rule_failures=rule_failures)
    return result
