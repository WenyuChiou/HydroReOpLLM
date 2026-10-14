from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from llm_reservoir_agent.information import InformationCatalog


def _csv(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return path.name


def _source(path: str, *, kind: str = "observation", unit: str = "m3/s") -> dict:
    return {
        "type": "csv",
        "path": path,
        "quantity": "flow",
        "unit": unit,
        "location": "gauge-external",
        "kind": kind,
    }


def _profile(*, required: bool = True, **field: object) -> dict:
    return {
        "p": {
            "fields": {
                "flow": {"source": "flow-source", "required": required, **field}
            }
        }
    }


def _build(catalog: InformationCatalog, **kwargs: object) -> dict:
    return catalog.build(
        "p",
        decision_time=kwargs.pop("decision_time", "2020-01-02T00:00:00Z"),
        timestep=0,
        observation={},
        **kwargs,
    )


def test_observation_blocks_future_valid_and_future_availability(tmp_path: Path) -> None:
    path = _csv(
        tmp_path / "flow.csv",
        "valid_time,available_at,value\n"
        "2020-01-01T00:00:00Z,2020-01-01T01:00:00Z,1\n"
        "2020-01-01T12:00:00Z,2020-01-03T00:00:00Z,2\n"
        "2020-01-03T00:00:00Z,2020-01-01T00:00:00Z,3\n",
    )
    catalog = InformationCatalog(
        {"flow-source": _source(path)}, _profile(history=3), base_path=tmp_path, location_ids=[]
    )

    result = _build(catalog)

    field = result["fields"]["flow"]
    assert field["value"] == 1.0
    assert [sample["value"] for sample in field["history"]] == [1.0]
    assert result["decision_time"] == "2020-01-02T00:00:00Z"
    assert catalog.file_pins[str((tmp_path / path).resolve())]


def test_forecast_uses_latest_available_cycle_and_complete_chronology(tmp_path: Path) -> None:
    path = _csv(
        tmp_path / "forecast.csv",
        "issued_at,valid_time,available_at,value\n"
        "2020-01-01T00:00:00Z,2020-01-02T00:00:00Z,2020-01-01T01:00:00Z,1\n"
        "2020-01-01T00:00:00Z,2020-01-03T00:00:00Z,2020-01-01T01:00:00Z,2\n"
        "2020-01-01T12:00:00Z,2020-01-03T00:00:00Z,2020-01-01T13:00:00Z,4\n"
        "2020-01-01T12:00:00Z,2020-01-02T00:00:00Z,2020-01-01T13:00:00Z,3\n"
        "2020-01-01T12:00:00Z,2020-01-02T00:00:00Z,2020-01-01T15:00:00Z,3.5\n"
        "2020-01-02T00:00:00Z,2020-01-04T00:00:00Z,2020-01-02T01:00:00Z,9\n",
    )
    catalog = InformationCatalog(
        {"flow-source": _source(path, kind="forecast")},
        _profile(history=8),
        base_path=tmp_path,
        location_ids=[],
    )

    field = _build(catalog, decision_time="2020-01-01T20:00:00Z")["fields"]["flow"]

    assert field["value"] == 3.5
    assert field["issued_at"] == "2020-01-01T12:00:00Z"
    assert [sample["value"] for sample in field["history"]] == [3.5, 4.0]
    assert [sample["valid_time"] for sample in field["history"]] == [
        "2020-01-02T00:00:00Z",
        "2020-01-03T00:00:00Z",
    ]


def test_required_missing_and_stale_stop_but_optional_is_explicit(tmp_path: Path) -> None:
    path = _csv(
        tmp_path / "flow.csv",
        "valid_time,available_at,value\n"
        "2020-01-01T00:00:00Z,2020-01-01T00:00:00Z,1\n",
    )
    source = {"flow-source": _source(path)}
    required = InformationCatalog(
        source, _profile(max_age_seconds=60), base_path=tmp_path, location_ids=[]
    )
    optional = InformationCatalog(
        source,
        _profile(required=False, max_age_seconds=60),
        base_path=tmp_path,
        location_ids=[],
    )

    with pytest.raises(ValueError, match="required field.*stale"):
        _build(required)
    missing = _build(optional)["fields"]["flow"]

    assert missing["status"] == "MISSING"
    assert missing["reason"] == "stale"
    assert missing["value"] is None
    assert missing["history"] == []


def test_forecast_staleness_is_measured_from_issue_time(tmp_path: Path) -> None:
    path = _csv(
        tmp_path / "forecast.csv",
        "issued_at,valid_time,available_at,value\n"
        "2020-01-01T00:00:00Z,2020-01-10T00:00:00Z,2020-01-01T00:00:00Z,1\n",
    )
    catalog = InformationCatalog(
        {"flow-source": _source(path, kind="forecast")},
        _profile(required=False, max_age_seconds=3600),
        base_path=tmp_path,
        location_ids=[],
    )

    field = _build(catalog, decision_time="2020-01-02T00:00:00Z")["fields"]["flow"]

    assert field["status"] == "MISSING"
    assert field["reason"] == "stale"


def test_unit_conversions_and_unsupported_conversion(tmp_path: Path) -> None:
    sources = {
        "flow-source": {
            "type": "static",
            "value": 1,
            "quantity": "flow",
            "unit": "m3/s",
            "location": "x",
        }
    }
    converted = InformationCatalog(
        sources, _profile(unit="cfs"), base_path=tmp_path, location_ids=[]
    )
    invalid = InformationCatalog(
        sources, _profile(unit="acre-ft"), base_path=tmp_path, location_ids=[]
    )

    assert _build(converted)["fields"]["flow"]["value"] == pytest.approx(35.31466672148859)
    with pytest.raises(ValueError, match="unsupported unit conversion"):
        _build(invalid)


@pytest.mark.parametrize(
    "contents,match",
    [
        (
            "valid_time,available_at,value,extra\n"
            "2020-01-01T00:00:00Z,2020-01-01T00:00:00Z,1,x\n",
            "columns must be exactly",
        ),
        (
            "valid_time,available_at,value\n"
            "2020-01-01T00:00:00Z,2020-01-01T00:00:00Z,nan\n",
            "value must be finite",
        ),
        (
            "valid_time,available_at,value\n"
            "2020-01-01,2020-01-01T00:00:00Z,1\n",
            "must include a timezone",
        ),
    ],
)
def test_csv_rejects_bad_columns_nonfinite_and_naive_timestamps(
    tmp_path: Path, contents: str, match: str
) -> None:
    path = _csv(tmp_path / "bad.csv", contents)

    with pytest.raises(ValueError, match=match):
        InformationCatalog(
            {"flow-source": _source(path)}, _profile(), base_path=tmp_path, location_ids=[]
        )


def test_observation_history_is_latest_subset_in_chronological_order(tmp_path: Path) -> None:
    path = _csv(
        tmp_path / "flow.csv",
        "valid_time,available_at,value\n"
        "2020-01-01T00:00:00Z,2020-01-01T00:00:00Z,1\n"
        "2020-01-02T00:00:00Z,2020-01-02T00:00:00Z,2\n"
        "2020-01-03T00:00:00Z,2020-01-03T00:00:00Z,3\n",
    )
    catalog = InformationCatalog(
        {"flow-source": _source(path)}, _profile(history=2), base_path=tmp_path, location_ids=[]
    )

    field = _build(catalog, decision_time="2020-01-04")["fields"]["flow"]

    assert field["value"] == 3.0
    assert [sample["value"] for sample in field["history"]] == [2.0, 3.0]


def test_ambiguous_equal_timestamp_duplicates_are_rejected(tmp_path: Path) -> None:
    path = _csv(
        tmp_path / "duplicate.csv",
        "valid_time,available_at,value\n"
        "2020-01-01T00:00:00Z,2020-01-01T01:00:00Z,1\n"
        "2020-01-01T00:00:00Z,2020-01-01T01:00:00Z,2\n",
    )

    with pytest.raises(ValueError, match="ambiguous duplicate timestamps"):
        InformationCatalog(
            {"flow-source": _source(path)}, _profile(), base_path=tmp_path, location_ids=[]
        )


def test_profiles_and_builds_are_isolated_json_copies(tmp_path: Path) -> None:
    shared = {"nested": [1, {"x": 2}]}
    sources = {
        "flow-source": {
            "type": "static",
            "value": shared,
            "quantity": "policy-context",
            "unit": "json",
            "location": "system",
            "datum": {"label": "v1"},
        }
    }
    profiles = {
        "p": {"fields": {"flow": {"source": "flow-source"}}},
        "other": {"fields": {"copy": {"source": "flow-source"}}},
    }
    catalog = InformationCatalog(sources, profiles, base_path=tmp_path, location_ids=[])
    shared["nested"][1]["x"] = 99

    first = _build(catalog)
    first["fields"]["flow"]["value"]["nested"][1]["x"] = -1
    second = _build(catalog)
    other = catalog.build(
        "other", decision_time=date(2020, 1, 2), timestep=0, observation={}
    )

    assert second["fields"]["flow"]["value"] == {"nested": [1, {"x": 2}]}
    assert other["fields"]["copy"]["value"] == {"nested": [1, {"x": 2}]}
    assert json.dumps(other)
    with pytest.raises(TypeError):
        catalog.file_pins["new"] = "digest"  # type: ignore[index]


def test_extension_requires_registration_and_stable_version(tmp_path: Path) -> None:
    extension = {
        "flow-source": {
            "type": "extension",
            "provider": "gauge",
            "parameters": {"station": "A"},
            "quantity": "flow",
            "unit": "m3/s",
            "location": "external-A",
        }
    }

    with pytest.raises(ValueError, match="unregistered provider"):
        InformationCatalog(extension, _profile(), base_path=tmp_path, location_ids=[])

    def unstable(**_: object) -> list[dict]:
        return []

    with pytest.raises(ValueError, match="version attribute"):
        InformationCatalog(
            extension, _profile(), base_path=tmp_path, location_ids=[], providers={"gauge": unstable}
        )

    def provider(**kwargs: object) -> list[dict]:
        assert kwargs["source"]["parameters"] == {"station": "A"}  # type: ignore[index]
        return [
            {
                "valid_time": "2020-01-01T00:00:00Z",
                "available_at": "2020-01-01T01:00:00Z",
                "value": 8,
            }
        ]

    provider.version = "gauge-api-2"  # type: ignore[attr-defined]
    catalog = InformationCatalog(
        extension, _profile(), base_path=tmp_path, location_ids=[], providers={"gauge": provider}
    )
    provider.version = "mutated-after-registration"  # type: ignore[attr-defined]

    field = _build(catalog)["fields"]["flow"]
    assert field["value"] == 8.0
    assert field["provider_version"] == "gauge-api-2"


def test_simulation_location_is_validated_without_host_access(tmp_path: Path) -> None:
    sources = {
        "flow-source": {
            "type": "simulation",
            "quantity": "storage",
            "unit": "m3",
            "location": "reservoir-a",
        }
    }
    with pytest.raises(ValueError, match="unknown simulation location"):
        InformationCatalog(sources, _profile(), base_path=tmp_path, location_ids=["reservoir-b"])

    catalog = InformationCatalog(
        sources, _profile(required=False), base_path=tmp_path, location_ids=["reservoir-a"]
    )
    assert _build(catalog)["fields"]["flow"]["status"] == "MISSING"

    def reader(
        source_id: str,
        source: dict,
        decision_time: str,
        timestep: int,
        observation: dict,
    ) -> list[dict]:
        assert (source_id, source["location"], decision_time, timestep, observation) == (
            "flow-source",
            "reservoir-a",
            "2020-01-02T00:00:00Z",
            0,
            {},
        )
        return [
            {
                "valid_time": "2020-01-01T00:00:00Z",
                "available_at": "2020-01-01T00:00:00Z",
                "value": 10,
            },
            {
                "valid_time": "2020-01-02T00:00:00Z",
                "available_at": "2020-01-03T00:00:00Z",
                "value": 99,
            },
        ]

    available = _build(catalog, simulation_reader=reader)["fields"]["flow"]
    assert available["status"] == "AVAILABLE"
    assert available["value"] == 10.0


def test_forecast_excludes_expired_horizons(tmp_path: Path) -> None:
    path = _csv(tmp_path / "horizons.csv", "issued_at,valid_time,available_at,value\n"
                "2020-01-01T00:00:00Z,2020-01-01T12:00:00Z,2020-01-01T00:00:00Z,99\n"
                "2020-01-01T00:00:00Z,2020-01-03T00:00:00Z,2020-01-01T00:00:00Z,7\n")
    catalog = InformationCatalog({"flow-source": _source(path, kind="forecast")},
                                 _profile(history=2), base_path=tmp_path, location_ids=[])
    field = _build(catalog)["fields"]["flow"]
    assert field["value"] == 7
    assert [x["value"] for x in field["history"]] == [7]
    with pytest.raises(ValueError, match="required field.*unavailable"):
        _build(catalog, decision_time="2020-01-04")


def test_observation_history_keeps_one_revision_per_valid_time(tmp_path: Path) -> None:
    path = _csv(tmp_path / "revisions.csv", "valid_time,available_at,value\n"
                "2020-01-01T00:00:00Z,2020-01-01T01:00:00Z,1\n"
                "2020-01-01T00:00:00Z,2020-01-01T02:00:00Z,2\n"
                "2020-01-01T12:00:00Z,2020-01-01T13:00:00Z,3\n")
    catalog = InformationCatalog({"flow-source": _source(path)}, _profile(history=3),
                                 base_path=tmp_path, location_ids=[])
    assert [x["value"] for x in _build(catalog)["fields"]["flow"]["history"]] == [2, 3]


def test_extension_forecast_kind_is_declared_and_preserved(tmp_path: Path) -> None:
    def provider(**_):
        return [dict(issued_at="2020-01-01T00:00:00Z", valid_time="2020-01-03T00:00:00Z",
                     available_at="2020-01-01T01:00:00Z", value=4)]
    provider.version = "forecast-fixture-v1"
    sources = {"flow-source": dict(type="extension", provider="predictor", kind="forecast",
                                    quantity="flow", unit="m3/s", location="external")}
    catalog = InformationCatalog(sources, _profile(), base_path=tmp_path, location_ids=[],
                                 providers={"predictor": provider})
    assert _build(catalog)["fields"]["flow"]["kind"] == "forecast"


def test_aliases_share_one_provider_snapshot(tmp_path: Path) -> None:
    calls = []
    def provider(**_):
        calls.append(1)
        return [dict(valid_time="2020-01-01T00:00:00Z", available_at="2020-01-01T01:00:00Z", value=len(calls))]
    provider.version = "fixture-v1"
    sources = {"s":dict(type="extension",provider="p",quantity="flow",unit="m3/s",location="external")}
    profiles = {"p":dict(fields={"a":dict(source="s"),"b":dict(source="s",unit="cfs")})}
    catalog = InformationCatalog(sources, profiles, base_path=tmp_path, location_ids=[], providers={"p":provider})
    fields = _build(catalog)["fields"]
    assert len(calls) == 1
    assert fields["b"]["value"] == pytest.approx(fields["a"]["value"] * 35.31466672148859)


def test_saved_static_and_csv_information_is_reconstructed(tmp_path: Path) -> None:
    from copy import deepcopy
    from llm_reservoir_agent.information_verification import verify_information
    path = _csv(tmp_path/"data.csv", "valid_time,available_at,value\n2020-01-01T00:00:00Z,2020-01-01T01:00:00Z,3\n")
    for source in (_source(path), dict(type="static",value=5,quantity="required_flow",unit="m3/s",location="use")):
        catalog = InformationCatalog({"flow-source":source}, _profile(), base_path=tmp_path, location_ids=[])
        configuration=catalog.export_configuration();snapshot=_build(catalog);observation=dict(timestamp="2020-01-02")
        verify_information(snapshot,observation,configuration["profiles"]["p"],configuration["sources"],
                           source_records=configuration["source_records"])
        corrupt=deepcopy(snapshot);corrupt["fields"]["flow"]["value"]=999;corrupt["fields"]["flow"]["history"][-1]["value"]=999
        with pytest.raises(ValueError, match="frozen or simulated source"):
            verify_information(corrupt,observation,configuration["profiles"]["p"],configuration["sources"],
                               source_records=configuration["source_records"])


@pytest.mark.parametrize("field", ["source_id", "profile_id", "alias", "unit", "location"])
def test_metadata_whitespace_stops_before_information_runtime(tmp_path, field):
    # Silent normalization can collapse IDs or discard a declared native history.
    source_id = " source " if field == "source_id" else "source"
    profile_id = " profile " if field == "profile_id" else "profile"
    alias = " inflow " if field == "alias" else "inflow"
    sources = {source_id: {"type": "simulation", "quantity": "inflow",
                           "unit": " m3/s " if field == "unit" else "m3/s",
                           "location": " R1 " if field == "location" else "R1"}}
    profiles = {profile_id: {"fields": {alias: {"source": source_id, "history": 2}}}}
    with pytest.raises(ValueError, match="surrounding whitespace"):
        InformationCatalog(sources, profiles, base_path=tmp_path, location_ids=["R1"])
