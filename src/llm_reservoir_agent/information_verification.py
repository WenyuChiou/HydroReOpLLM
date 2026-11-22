"""Independently verify saved information against frozen or completed sources.

``verification`` supplies a saved snapshot, observation, profile, pinned source
declarations/CSV records and an independent completed-simulation reader. This
module reconstructs static/CSV/native selection and unit conversion, verifies
UTC availability and issue/horizon rules, and checks retained values/history
and provenance. Registered extension information is checked for internal timing
and metadata consistency; its external values are not re-fetched or independently
reconstructed. Successful validation returns None and inconsistencies raise.
No files, providers or physical state are modified; a supplied simulation reader
is expected to be read-only. Source and requested output units remain explicit.
"""
from copy import deepcopy
import math

from .information import _convert, _parse_timestamp


def _select_reference(source, records, clock, count):
    """Reconstruct causal selection independently from saved records, selecting latest available revisions and the latest eligible forecast cycle.

    Observation history trails the decision; forecast history advances from the nearest nonexpired horizon. The runtime catalog cache is never consulted.
    """
    if source["type"] == "static":
        return [{"value": source["value"], "valid_time": None, "available_at": None}]
    forecast = source.get("kind") == "forecast"
    eligible = []
    for raw in records:
        valid = _parse_timestamp(raw["valid_time"], "source valid_time")
        available = _parse_timestamp(raw["available_at"], "source available_at")
        issued = _parse_timestamp(raw["issued_at"], "source issued_at") if forecast else None
        if forecast:
            if issued <= available <= clock and valid >= clock:
                eligible.append((valid, available, issued, deepcopy(raw)))
        elif valid <= clock and available <= clock:
            eligible.append((valid, available, None, deepcopy(raw)))
    if forecast and eligible:
        latest = max(row[2] for row in eligible)
        eligible = [row for row in eligible if row[2] == latest]
    revisions = {}
    for valid, available, _, record in eligible:
        if valid not in revisions or available > revisions[valid][0]:
            revisions[valid] = (available, record)
    chronology = [revisions[key][1] for key in sorted(revisions)]
    return chronology[:count] if forecast else chronology[-count:]


def verify_information(snapshot, observation, profile, sources, *, source_records=None,
                       simulation_reader=None):
    """Validate one saved decision-information snapshot against independent evidence.

    Static/CSV/native sources are reconstructed. Extension-reader samples are checked internally without calling the external reader; passing does not establish external source truth.

    Parameters
    ----------
    snapshot : dict
        Saved decision-information.v1 fields with selected value, history, unit and source metadata.
    observation : Mapping
        Corresponding current decision observation; timestamp establishes the causal cutoff.
    profile : Mapping
        Frozen selected-field declarations, including required/history/max_age_seconds controls.
    sources : Mapping
        Frozen source declarations with hashes or declared reader versions and original units.
    source_records : Mapping or None, optional
        Frozen normalized CSV samples keyed by source ID.
    simulation_reader : callable or None, optional
        Independent callback(source, observation) yielding only available native samples.

    Returns
    -------
    None
        All requested consistency checks pass; no audit status or physical state is changed.

    Raises
    ------
    ValueError
        Schema, coverage, units, metadata, timing, availability, history or reconstructed values disagree.
    TypeError
        A source timestamp or value has an invalid type.
    """

    clock = _parse_timestamp(observation["timestamp"], "decision clock", allow_legacy=True)
    if snapshot.get("schema_version") != "decision-information.v1":
        raise ValueError("unsupported decision information schema")
    if _parse_timestamp(snapshot.get("decision_time"), "decision time") != clock:
        raise ValueError("information decision time differs from observation")
    fields = snapshot.get("fields")
    if not isinstance(fields, dict) or set(fields) != set(profile["fields"]):
        raise ValueError("selected information field coverage differs from profile")
    for alias, spec in profile["fields"].items():
        field, source = fields[alias], sources[spec["source"]]
        metadata = {"source_id": spec["source"], "quantity": source["quantity"],
                    "location": source["location"], "unit": spec.get("unit", source["unit"]),
                    "kind": source.get("kind", source["type"])}
        for key in ("source_sha256", "provider_version", "datum"):
            if key in source:
                metadata[key] = source[key]
        if any(field.get(key) != value for key, value in metadata.items()):
            raise ValueError("information metadata differs from configured source")
        reconstructed = source["type"] != "extension"
        reference = []
        if reconstructed:
            if source["type"] == "csv":
                if source_records is None or spec["source"] not in source_records:
                    raise ValueError("missing frozen information source records")
                candidates = source_records[spec["source"]]
            elif source["type"] == "simulation":
                if simulation_reader is None:
                    raise ValueError("missing independent simulation information reader")
                candidates = simulation_reader(source, observation)
            else:
                candidates = []
            reference = _select_reference(source, candidates, clock, spec.get("history", 1))
            if reference and source["type"] != "static":
                selected = reference[0] if source.get("kind") == "forecast" else reference[-1]
                age_from = selected.get("issued_at", selected["valid_time"])
                if (clock-_parse_timestamp(age_from, "source age")).total_seconds() > spec.get("max_age_seconds", float("inf")):
                    reference = []
        if field.get("status") == "MISSING":
            if (spec.get("required", True) or field.get("value") is not None
                    or field.get("history") != [] or not field.get("reason") or reference):
                raise ValueError("invalid missing information record")
            continue
        if field.get("status") != "AVAILABLE":
            raise ValueError("invalid information availability status")
        history = field.get("history")
        if not isinstance(history, list) or not 1 <= len(history) <= spec.get("history", 1):
            raise ValueError("information history coverage mismatch")
        chosen = history[0] if source.get("kind") == "forecast" else history[-1]
        if {key: value for key, value in field.items() if key not in ("status", "history")} != chosen:
            raise ValueError("selected information differs from its history")
        for sample in history:
            if any(sample.get(key) != value for key, value in metadata.items()):
                raise ValueError("information history source mismatch")
            if source["type"] == "static":
                if sample.get("valid_time") is not None or sample.get("available_at") is not None:
                    raise ValueError("static information has a fabricated timestamp")
                continue
            valid = _parse_timestamp(sample.get("valid_time"), "information valid_time")
            available = _parse_timestamp(sample.get("available_at"), "information available_at")
            if available > clock:
                raise ValueError("information was unavailable at decision time")
            value = sample.get("value")
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError("invalid information value")
            if source.get("kind") == "forecast":
                issued = _parse_timestamp(sample.get("issued_at"), "forecast issued_at")
                if issued > available or valid < clock:
                    raise ValueError("forecast was unavailable or its horizon expired")
                age = (clock-issued).total_seconds()
            else:
                if "issued_at" in sample or valid > clock:
                    raise ValueError("future observation leaked into information")
                age = (clock-valid).total_seconds()
            if sample is chosen and age > spec.get("max_age_seconds", float("inf")):
                raise ValueError("stale selected information")
        if reconstructed:
            expected = []
            for raw in reference:
                converted = {**metadata, "value": _convert(raw["value"], source["unit"], metadata["unit"]),
                             "valid_time": raw["valid_time"], "available_at": raw["available_at"]}
                if "issued_at" in raw:
                    converted["issued_at"] = raw["issued_at"]
                expected.append(converted)
            if history != expected:
                raise ValueError("selected information differs from frozen or simulated source")
