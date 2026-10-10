"""Strict offline adapter for previously recorded Delaware LLM responses."""

from __future__ import annotations

import json
import math
from datetime import date, timedelta
from typing import Any, Mapping

from .case import CFS_TO_CMS
from .contracts import ReservoirAction, ReservoirObservation, finite_nonnegative


def _json_copy(value: Any, label: str) -> Any:
    """Return a JSON-only copy and reject non-finite or unsupported values."""

    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite JSON values") from exc


def normalize_delaware_response(payload: Mapping[str, Any]) -> ReservoirAction:
    """Convert the legacy ``release_cfs`` response into a versioned action."""

    if not isinstance(payload, Mapping):
        raise TypeError("Delaware response must be a mapping")
    response = dict(payload)
    extras = set(response).difference({"release_cfs", "reasoning"})
    if extras:
        raise ValueError(f"Delaware response has unsupported fields: {sorted(extras)}")
    if "release_cfs" not in response:
        raise ValueError("Delaware response requires release_cfs")
    if "reasoning" in response and not isinstance(response["reasoning"], str):
        raise TypeError("reasoning must be a string")

    release_cfs = finite_nonnegative(response["release_cfs"], "release_cfs")
    release_cms = release_cfs * CFS_TO_CMS
    if not math.isfinite(release_cms):
        raise ValueError("normalized release_cms must be finite")
    return ReservoirAction(release_cms=release_cms)


class RecordedResponsePolicy:
    """Replay validated legacy responses without provider or network access."""

    policy_id = "recorded_llm_response"
    network_calls = 0

    def __init__(self, records: list[Mapping[str, Any]]) -> None:
        if not isinstance(records, list):
            raise TypeError("records must be a list")

        validated: list[dict[str, Any]] = []
        previous_date: date | None = None
        for index, candidate in enumerate(records):
            if not isinstance(candidate, Mapping):
                raise TypeError(f"records[{index}] must be a mapping")
            record = dict(candidate)
            if set(record) != {"date", "response"}:
                raise ValueError(
                    f"records[{index}] must contain exactly date and response"
                )
            date_text = record["date"]
            if not isinstance(date_text, str):
                raise TypeError(f"records[{index}].date must be a string")
            try:
                parsed_date = date.fromisoformat(date_text)
            except ValueError as exc:
                raise ValueError(
                    f"records[{index}].date must use canonical YYYY-MM-DD format"
                ) from exc
            if parsed_date.isoformat() != date_text:
                raise ValueError(
                    f"records[{index}].date must use canonical YYYY-MM-DD format"
                )
            if previous_date is not None and parsed_date != previous_date + timedelta(days=1):
                raise ValueError("record dates must be unique, ordered, and consecutive")

            response = record["response"]
            if not isinstance(response, Mapping):
                raise TypeError(f"records[{index}].response must be a mapping")
            normalize_delaware_response(response)
            validated.append(
                _json_copy({"date": date_text, "response": dict(response)}, f"records[{index}]")
            )
            previous_date = parsed_date

        self._records = validated
        self.dates = tuple(record["date"] for record in validated)
        self._next_index = 0
        self._audit_records: list[dict[str, Any]] = []

    @property
    def records(self) -> list[dict[str, Any]]:
        """Return an isolated copy of the validated replay input."""

        return _json_copy(self._records, "records")

    @property
    def audit_records(self) -> list[dict[str, Any]]:
        """Return an isolated copy of decisions made so far."""

        return _json_copy(self._audit_records, "audit_records")

    def decide(
        self, observation: Mapping[str, Any] | ReservoirObservation
    ) -> ReservoirAction:
        if self._next_index >= len(self._records):
            raise IndexError("recorded responses are exhausted")
        if isinstance(observation, ReservoirObservation):
            timestep = observation.timestep
            timestamp = observation.timestamp
        elif isinstance(observation, Mapping):
            if "timestep" not in observation or "timestamp" not in observation:
                raise ValueError("observation requires timestep and timestamp")
            timestep = observation["timestep"]
            timestamp = observation["timestamp"]
        else:
            raise TypeError("observation must be a mapping or ReservoirObservation")

        if isinstance(timestep, bool) or not isinstance(timestep, int):
            raise TypeError("observation timestep must be an integer")
        if not isinstance(timestamp, str):
            raise TypeError("observation timestamp must be a string")

        expected = self._records[self._next_index]
        if timestep != self._next_index:
            raise ValueError(
                f"expected observation timestep {self._next_index}, got {timestep}"
            )
        if timestamp not in (expected["date"], expected["date"] + "T00:00:00"):
            raise ValueError(
                f"expected observation date {expected['date']}, got {timestamp}"
            )

        raw_response = expected["response"]
        action = normalize_delaware_response(raw_response)
        audit_record = {
            "date": expected["date"],
            "timestep": timestep,
            "raw_response": _json_copy(raw_response, "raw_response"),
            "reasoning": raw_response.get("reasoning"),
            "normalized_action": action.to_dict(),
        }
        self._audit_records.append(audit_record)
        self._next_index += 1
        return action
