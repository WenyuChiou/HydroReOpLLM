"""Causal, provider-independent decision information catalogs.

Role: Select available information at the decision time.

Connections and data: workflow declares sources and named profiles; information_runtime
supplies native simulation records. InformationCatalog builds detached fields with
values, units, valid times, availability times and provenance. Supplemental information
does not replace the physical inlet or storage ledger.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping


SCHEMA_VERSION = "decision-information.v1"
_SOURCE_TYPES = {"static", "csv", "simulation", "extension"}
_SIMULATION_QUANTITIES = {"inflow", "storage", "release", "flow"}
_CONVERSIONS = {
    ("m3/s", "cfs"): 35.31466672148859,
    ("cfs", "m3/s"): 1.0 / 35.31466672148859,
    ("m3", "acre-ft"): 1.0 / 1233.48183754752,
    ("acre-ft", "m3"): 1233.48183754752,
    ("m", "ft"): 3.280839895013123,
    ("ft", "m"): 1.0 / 3.280839895013123,
}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    if value != value.strip():
        raise ValueError(f"{label} must not contain surrounding whitespace")
    return value


def _json_copy(value: Any, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite JSON values") from exc


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _csv_number(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("value must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError("value must be finite")
    return result


def _parse_timestamp(value: Any, label: str, *, allow_legacy: bool = False) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif allow_legacy and isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{label} must be a timestamp")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{label} must be an ISO timestamp") from exc
    else:
        raise TypeError(f"{label} must be a datetime or ISO timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if not allow_legacy:
            raise ValueError(f"{label} must include a timezone")
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _allowed(spec: Mapping[str, Any], allowed: set[str], label: str) -> None:
    extras = set(spec).difference(allowed)
    if extras:
        raise ValueError(f"{label} has unsupported fields: {sorted(extras)}")


def _convert(value: Any, source_unit: str, output_unit: str) -> Any:
    if source_unit == output_unit:
        return deepcopy(value)
    factor = _CONVERSIONS.get((source_unit, output_unit))
    if factor is None:
        raise ValueError(f"unsupported unit conversion: {source_unit} -> {output_unit}")
    return _finite_number(value, "value") * factor


class InformationCatalog:
    """Validated information sources and named decision-time profiles."""

    def __init__(
        self,
        sources: Mapping[str, Any],
        profiles: Mapping[str, Any],
        *,
        base_path: Path,
        location_ids: Iterable[str],
        providers: Mapping[str, Callable[..., Iterable[Mapping[str, Any]]]] | None = None,
    ) -> None:
        if not isinstance(sources, Mapping):
            raise TypeError("sources must be a mapping")
        if not isinstance(profiles, Mapping):
            raise TypeError("profiles must be a mapping")
        self._base_path = Path(base_path).resolve()
        self._location_ids = {_text(item, "location_id") for item in location_ids}
        self._provider_versions: dict[str, str] = {}
        self._providers = self._validate_providers(providers or {})
        self._file_pins: dict[str, str] = {}
        self._records: dict[str, list[dict[str, Any]]] = {}
        self._sources = self._validate_sources(sources)
        self._profiles = self._validate_profiles(profiles)

    @property
    def file_pins(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self._file_pins))

    def export_configuration(self) -> dict[str, Any]:
        """Freeze source declarations and CSV samples for saved-file verification.

        Registered providers are never called here. Their selected records are
        captured at each decision; CSV bytes are pinned when the catalog loads.
        """
        sources = deepcopy(self._sources)
        for source in sources.values():
            source.update(self._provenance(source))
        records = {
            source_id: [{key: _iso(value) if isinstance(value, datetime) else deepcopy(value)
                         for key, value in record.items()} for record in series]
            for source_id, series in self._records.items()
        }
        return _json_copy({"sources": sources, "profiles": self._profiles,
                           "source_records": records}, "information configuration")

    def _validate_providers(
        self, providers: Mapping[str, Callable[..., Iterable[Mapping[str, Any]]]]
    ) -> dict[str, Callable[..., Iterable[Mapping[str, Any]]]]:
        if not isinstance(providers, Mapping):
            raise TypeError("providers must be a mapping")
        validated: dict[str, Callable[..., Iterable[Mapping[str, Any]]]] = {}
        for raw_name, provider in providers.items():
            name = _text(raw_name, "provider name")
            if name in validated:
                raise ValueError(f"duplicate provider name: {name}")
            if not callable(provider):
                raise TypeError(f"provider {name!r} must be callable")
            version = getattr(provider, "version", None)
            if not isinstance(version, str) or not version.strip():
                raise ValueError(f"provider {name!r} requires a non-empty version attribute")
            validated[name] = provider
            self._provider_versions[name] = version.strip()
        return validated

    def _validate_sources(self, sources: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        validated: dict[str, dict[str, Any]] = {}
        for raw_id, raw_spec in sources.items():
            source_id = _text(raw_id, "source_id")
            if source_id in validated:
                raise ValueError(f"duplicate source_id: {source_id}")
            if not isinstance(raw_spec, Mapping):
                raise TypeError(f"source {source_id!r} must be a mapping")
            spec = dict(raw_spec)
            source_type = _text(spec.get("type"), f"source {source_id!r} type")
            if source_type not in _SOURCE_TYPES:
                raise ValueError(f"source {source_id!r} has unsupported type {source_type!r}")
            common = {"type", "quantity", "unit", "location", "datum"}
            if source_type == "static":
                _allowed(spec, common | {"value"}, f"source {source_id!r}")
                if "value" not in spec:
                    raise ValueError(f"source {source_id!r} requires value")
            elif source_type == "csv":
                _allowed(spec, common | {"path", "kind"}, f"source {source_id!r}")
                if "path" not in spec:
                    raise ValueError(f"source {source_id!r} requires path")
                kind = _text(spec.get("kind"), f"source {source_id!r} kind")
                if kind not in {"observation", "forecast"}:
                    raise ValueError(f"source {source_id!r} kind must be observation or forecast")
                spec["kind"] = kind
            elif source_type == "simulation":
                _allowed(spec, common, f"source {source_id!r}")
            else:
                _allowed(spec, common | {"provider", "parameters", "kind"}, f"source {source_id!r}")
                kind = _text(spec.get("kind", "observation"), f"source {source_id!r} kind")
                if kind not in {"observation", "forecast"}:
                    raise ValueError(f"source {source_id!r} kind must be observation or forecast")
                spec["kind"] = kind
                provider_name = _text(spec.get("provider"), f"source {source_id!r} provider")
                if provider_name not in self._providers:
                    raise ValueError(f"source {source_id!r} names unregistered provider {provider_name!r}")
                parameters = spec.get("parameters", {})
                if not isinstance(parameters, Mapping):
                    raise TypeError(f"source {source_id!r} parameters must be a mapping")
                spec["provider"] = provider_name
                spec["parameters"] = _json_copy(dict(parameters), f"source {source_id!r} parameters")

            spec["type"] = source_type
            spec["quantity"] = _text(spec.get("quantity"), f"source {source_id!r} quantity")
            spec["unit"] = _text(spec.get("unit"), f"source {source_id!r} unit")
            spec["location"] = _text(spec.get("location"), f"source {source_id!r} location")
            if "datum" in spec:
                spec["datum"] = _json_copy(spec["datum"], f"source {source_id!r} datum")
            if source_type == "simulation":
                if spec["quantity"] not in _SIMULATION_QUANTITIES:
                    raise ValueError(f"source {source_id!r} has unsupported simulation quantity")
                if spec["location"] not in self._location_ids:
                    raise ValueError(f"source {source_id!r} has unknown simulation location")
            if source_type == "static":
                spec["value"] = _json_copy(spec["value"], f"source {source_id!r} value")
            if source_type == "csv":
                path = (self._base_path / _text(spec["path"], f"source {source_id!r} path")).resolve()
                payload = path.read_bytes()
                digest = hashlib.sha256(payload).hexdigest()
                absolute = str(path)
                previous = self._file_pins.get(absolute)
                if previous is not None and previous != digest:
                    raise ValueError(f"source file changed while catalog was constructed: {absolute}")
                self._file_pins[absolute] = digest
                spec["path"] = absolute
                spec["source_sha256"] = digest
                self._records[source_id] = self._read_csv(payload, spec, source_id)
            validated[source_id] = _json_copy(spec, f"source {source_id!r}")
        return validated

    def _read_csv(
        self, payload: bytes, spec: Mapping[str, Any], source_id: str
    ) -> list[dict[str, Any]]:
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(f"source {source_id!r} CSV must be UTF-8") from exc
        reader = csv.DictReader(text.splitlines())
        required = ["valid_time", "available_at", "value"]
        if spec["kind"] == "forecast":
            required.insert(0, "issued_at")
        if (
            set(reader.fieldnames or ()) != set(required)
            or len(reader.fieldnames or ()) != len(required)
        ):
            raise ValueError(f"source {source_id!r} CSV columns must be exactly {required}")
        rows = []
        for row in reader:
            row["value"] = _csv_number(row["value"])
            rows.append(
                self._normalise_record(
                    row, source_id, forecast=spec["kind"] == "forecast"
                )
            )
        self._reject_ambiguous(rows, source_id)
        return rows

    def _validate_profiles(self, profiles: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        validated: dict[str, dict[str, Any]] = {}
        for raw_id, raw_profile in profiles.items():
            profile_id = _text(raw_id, "profile_id")
            if profile_id in validated:
                raise ValueError(f"duplicate profile_id: {profile_id}")
            if not isinstance(raw_profile, Mapping):
                raise TypeError(f"profile {profile_id!r} must be a mapping")
            profile = dict(raw_profile)
            _allowed(profile, {"fields"}, f"profile {profile_id!r}")
            fields = profile.get("fields")
            if not isinstance(fields, Mapping):
                raise TypeError(f"profile {profile_id!r} fields must be a mapping")
            valid_fields: dict[str, dict[str, Any]] = {}
            for raw_alias, raw_field in fields.items():
                alias = _text(raw_alias, f"profile {profile_id!r} field alias")
                if alias in valid_fields:
                    raise ValueError(f"duplicate field alias: {alias}")
                if not isinstance(raw_field, Mapping):
                    raise TypeError(f"field {alias!r} must be a mapping")
                field = dict(raw_field)
                _allowed(field, {"source", "required", "unit", "max_age_seconds", "history"}, f"field {alias!r}")
                source_id = _text(field.get("source"), f"field {alias!r} source")
                if source_id not in self._sources:
                    raise ValueError(f"field {alias!r} names unknown source {source_id!r}")
                required = field.get("required", True)
                if not isinstance(required, bool):
                    raise TypeError(f"field {alias!r} required must be boolean")
                history = field.get("history", 1)
                if isinstance(history, bool) or not isinstance(history, int):
                    raise TypeError(f"field {alias!r} history must be an integer")
                if history <= 0:
                    raise ValueError(f"field {alias!r} history must be positive")
                item: dict[str, Any] = {"source": source_id, "required": required, "history": history}
                if "unit" in field:
                    item["unit"] = _text(field["unit"], f"field {alias!r} unit")
                if "max_age_seconds" in field:
                    age = _finite_number(field["max_age_seconds"], f"field {alias!r} max_age_seconds")
                    if age < 0:
                        raise ValueError(f"field {alias!r} max_age_seconds must be non-negative")
                    item["max_age_seconds"] = age
                valid_fields[alias] = item
            validated[profile_id] = {"fields": valid_fields}
        return _json_copy(validated, "profiles")

    def _normalise_record(
        self, raw_record: Mapping[str, Any], source_id: str, *, forecast: bool
    ) -> dict[str, Any]:
        if not isinstance(raw_record, Mapping):
            raise TypeError(f"source {source_id!r} records must be mappings")
        record = dict(raw_record)
        allowed = {"valid_time", "available_at", "value"}
        if forecast:
            allowed.add("issued_at")
        _allowed(record, allowed, f"source {source_id!r} record")
        required = allowed
        missing = required.difference(record)
        if missing:
            raise ValueError(f"source {source_id!r} record missing fields: {sorted(missing)}")
        valid = _parse_timestamp(record["valid_time"], "valid_time")
        available = _parse_timestamp(record["available_at"], "available_at")
        result: dict[str, Any] = {
            "valid_time": valid,
            "available_at": available,
            "value": _finite_number(record["value"], "value"),
        }
        if forecast:
            issued = _parse_timestamp(record["issued_at"], "issued_at")
            if issued > available:
                raise ValueError(f"source {source_id!r} forecast issued_at exceeds available_at")
            result["issued_at"] = issued
        return result

    @staticmethod
    def _reject_ambiguous(records: list[dict[str, Any]], source_id: str) -> None:
        seen: set[tuple[datetime, ...]] = set()
        for record in records:
            key = tuple(record[name] for name in ("issued_at", "valid_time", "available_at") if name in record)
            if key in seen:
                raise ValueError(f"source {source_id!r} has ambiguous duplicate timestamps")
            seen.add(key)

    def build(
        self,
        profile_id: str,
        *,
        decision_time: str | date | datetime,
        timestep: int,
        observation: Mapping[str, Any],
        simulation_reader: Callable[..., Iterable[Mapping[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        profile_name = _text(profile_id, "profile_id")
        if profile_name not in self._profiles:
            raise ValueError(f"unknown profile_id: {profile_name}")
        decision = _parse_timestamp(decision_time, "decision_time", allow_legacy=True)
        if isinstance(timestep, bool) or not isinstance(timestep, int):
            raise TypeError("timestep must be an integer")
        if timestep < 0:
            raise ValueError("timestep must be non-negative")
        if not isinstance(observation, Mapping):
            raise TypeError("observation must be a mapping")
        observation_copy = _json_copy(dict(observation), "observation")
        fields: dict[str, dict[str, Any]] = {}
        sampled_sources: dict[str, list[dict[str, Any]]] = {}
        for alias, field in self._profiles[profile_name]["fields"].items():
            source_id = field["source"]
            source = self._sources[source_id]
            # Multiple aliases/units see the same source snapshot in one decision.
            if source_id not in sampled_sources:
                sampled_sources[source_id] = self._records_for(
                    source_id, source, decision, timestep, observation_copy, simulation_reader,
                )
            records = sampled_sources[source_id]
            selected, history = self._select(records, source, decision, field["history"])
            reason: str | None = None
            if selected is None:
                reason = "no causally available record"
            elif "max_age_seconds" in field and source["type"] != "static":
                age_from = selected.get("issued_at", selected["valid_time"])
                if (decision - age_from).total_seconds() > field["max_age_seconds"]:
                    reason = "stale"
            if reason is not None:
                if field["required"]:
                    raise ValueError(f"required field {alias!r} is unavailable: {reason}")
                fields[alias] = self._missing_record(
                    source_id, source, field.get("unit", source["unit"]), reason
                )
                continue
            assert selected is not None
            output_unit = field.get("unit", source["unit"])
            fields[alias] = self._field_record(
                selected, history, source_id, source, output_unit
            )
        return _json_copy(
            {"schema_version": SCHEMA_VERSION, "decision_time": _iso(decision), "fields": fields},
            "decision information",
        )

    def _records_for(
        self,
        source_id: str,
        source: Mapping[str, Any],
        decision: datetime,
        timestep: int,
        observation: Mapping[str, Any],
        simulation_reader: Callable[..., Iterable[Mapping[str, Any]]] | None,
    ) -> list[dict[str, Any]]:
        source_type = source["type"]
        if source_type == "static":
            return [{"value": deepcopy(source["value"]), "valid_time": None, "available_at": None}]
        if source_type == "csv":
            return deepcopy(self._records[source_id])
        if source_type == "simulation":
            if simulation_reader is None:
                return []
            raw_records = simulation_reader(
                source_id, deepcopy(dict(source)), _iso(decision), timestep, deepcopy(dict(observation))
            )
            return self._runtime_records(raw_records, source_id)
        provider = self._providers[source["provider"]]
        raw_records = provider(
            decision_time=_iso(decision),
            timestep=timestep,
            observation=deepcopy(dict(observation)),
            source=deepcopy(dict(source)),
        )
        return self._runtime_records(raw_records, source_id)

    def _runtime_records(
        self, raw_records: Iterable[Mapping[str, Any]], source_id: str
    ) -> list[dict[str, Any]]:
        if isinstance(raw_records, (str, bytes, Mapping)):
            raise TypeError(f"source {source_id!r} provider must return an iterable of records")
        try:
            items = list(raw_records)
        except TypeError as exc:
            raise TypeError(f"source {source_id!r} provider must return an iterable") from exc
        forecast_flags = {"issued_at" in record for record in items if isinstance(record, Mapping)}
        if len(forecast_flags) > 1:
            raise ValueError(f"source {source_id!r} cannot mix forecast and non-forecast records")
        forecast = self._sources[source_id].get("kind") == "forecast"
        if items and forecast_flags != {forecast}:
            raise ValueError(f"source {source_id!r} records differ from declared forecast kind")
        records = [self._normalise_record(record, source_id, forecast=forecast) for record in items]
        self._reject_ambiguous(records, source_id)
        return records

    @staticmethod
    def _select(
        records: list[dict[str, Any]],
        source: Mapping[str, Any],
        decision: datetime,
        history_count: int,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        if source["type"] == "static":
            return (records[0], records[:1]) if records else (None, [])
        forecast = source.get("kind") == "forecast" or bool(records and "issued_at" in records[0])
        if forecast:
            eligible = [
                record
                for record in records
                if record["issued_at"] <= record["available_at"] <= decision
                and record["valid_time"] >= decision
            ]
            if not eligible:
                return None, []
            latest_issue = max(record["issued_at"] for record in eligible)
            cycle = [record for record in eligible if record["issued_at"] == latest_issue]
            revisions: dict[datetime, dict[str, Any]] = {}
            for record in cycle:
                previous = revisions.get(record["valid_time"])
                if previous is None or record["available_at"] > previous["available_at"]:
                    revisions[record["valid_time"]] = record
            chronology = sorted(revisions.values(), key=lambda record: record["valid_time"])
            return chronology[0], chronology[:history_count]
        eligible = [
            record
            for record in records
            if record["valid_time"] <= decision and record["available_at"] <= decision
        ]
        if not eligible:
            return None, []
        revisions: dict[datetime, dict[str, Any]] = {}
        for record in eligible:
            previous = revisions.get(record["valid_time"])
            if previous is None or record["available_at"] > previous["available_at"]:
                revisions[record["valid_time"]] = record
        chronology = sorted(revisions.values(), key=lambda record: record["valid_time"])
        return chronology[-1], chronology[-history_count:]

    def _provenance(self, source: Mapping[str, Any]) -> dict[str, Any]:
        if source["type"] == "csv":
            return {"source_sha256": source["source_sha256"]}
        if source["type"] == "extension":
            return {"provider_version": self._provider_versions[source["provider"]]}
        return {}

    def _sample_record(
        self,
        record: Mapping[str, Any],
        source_id: str,
        source: Mapping[str, Any],
        output_unit: str,
    ) -> dict[str, Any]:
        kind = source.get("kind", source["type"])
        sample: dict[str, Any] = {
            "value": _convert(record["value"], source["unit"], output_unit),
            "quantity": source["quantity"],
            "unit": output_unit,
            "location": source["location"],
            "kind": kind,
            "valid_time": _iso(record["valid_time"]) if record["valid_time"] is not None else None,
            "available_at": _iso(record["available_at"]) if record["available_at"] is not None else None,
            "source_id": source_id,
            **self._provenance(source),
        }
        if "issued_at" in record:
            sample["issued_at"] = _iso(record["issued_at"])
        if "datum" in source:
            sample["datum"] = deepcopy(source["datum"])
        return sample

    def _field_record(
        self,
        selected: Mapping[str, Any],
        history: list[dict[str, Any]],
        source_id: str,
        source: Mapping[str, Any],
        output_unit: str,
    ) -> dict[str, Any]:
        result = self._sample_record(selected, source_id, source, output_unit)
        result["status"] = "AVAILABLE"
        result["history"] = [
            self._sample_record(item, source_id, source, output_unit) for item in history
        ]
        return result

    def _missing_record(
        self, source_id: str, source: Mapping[str, Any], output_unit: str, reason: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": "MISSING",
            "reason": reason,
            "value": None,
            "quantity": source["quantity"],
            "unit": output_unit,
            "location": source["location"],
            "kind": source.get("kind", source["type"]),
            "valid_time": None,
            "available_at": None,
            "source_id": source_id,
            "history": [],
            **self._provenance(source),
        }
        if source.get("kind") == "forecast":
            result["issued_at"] = None
        if "datum" in source:
            result["datum"] = deepcopy(source["datum"])
        return result


__all__ = ["InformationCatalog", "SCHEMA_VERSION"]
