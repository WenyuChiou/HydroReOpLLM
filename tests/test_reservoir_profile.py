"""Explicit reservoir-profile contracts against the unchanged pinned model."""
from copy import deepcopy
from dataclasses import asdict, make_dataclass
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from examples.fe_walter.extensions.anik_v3_7 import load_anik
from examples.fe_walter.extensions import reservoir_profile


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def model():
    return load_anik(ROOT)


@pytest.fixture
def document():
    return {
        "schema_version": reservoir_profile.SCHEMA_VERSION,
        "profile_id": "custom_a",
        "source_notes": "Synthetic profile for local contract tests.",
        "reservoir_config": {
            "name": "Custom A Reservoir",
            "inflow_csv": "custom_a_inflow.csv",
            "capacity_af": 5000.0,
            "initial_storage_af": 2000.0,
            "purpose": "other",
            "river": "Custom A River",
            "inflow_reservoir_key": "custom_a",
            "public_profile": ["Custom A public fact"],
            "public_capacity_af": 5200.0,
            "min_release_cfs": 12.0,
            "max_release_cfs": 600.0,
        },
    }


def save(tmp_path, document, name="profile.json"):
    path = tmp_path / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_builtin_ids_and_identity_match_all_pinned_native_configs(model):
    expected = ("prompton", "fe_walter", "beltzville", "wallenpaupack")
    assert reservoir_profile.builtin_profile_ids(ROOT) == expected
    assert tuple(cfg.inflow_reservoir_key for cfg in model.RESERVOIRS) == expected
    for original in model.RESERVOIRS:
        config, provenance = reservoir_profile.load_profile_config(
            model, original.inflow_reservoir_key
        )
        assert config is original
        assert provenance == {
            "profile_id": original.inflow_reservoir_key,
            "profile_source": "pinned_builtin",
            "native_model_sha256": hashlib.sha256(
                (ROOT / "third_party/anik_v3_7/reservoir_model.py").read_bytes()
            ).hexdigest(),
            "reservoir_config": json.loads(json.dumps(asdict(original), allow_nan=False)),
        }
        assert json.loads(json.dumps(provenance, allow_nan=False)) == provenance


def test_builtin_lookup_rejects_unknown_and_ambiguous_ids(model):
    with pytest.raises(ValueError, match="unknown or ambiguous"):
        reservoir_profile.load_profile_config(model, "absent")
    duplicate = SimpleNamespace(RESERVOIRS=[model.RESERVOIRS[0]] * 2)
    with pytest.raises(ValueError, match="unknown or ambiguous"):
        reservoir_profile.load_profile_config(duplicate, "prompton")


@pytest.mark.parametrize("profile_id", ["prompton", "fe_walter", "beltzville", "wallenpaupack"])
def test_custom_file_cannot_override_any_builtin(tmp_path, document, model, profile_id):
    document["profile_id"] = profile_id
    document["reservoir_config"]["inflow_reservoir_key"] = profile_id
    path = save(tmp_path, document)
    with pytest.raises(ValueError, match="must not override a built-in"):
        reservoir_profile.validate_profile_document(path, profile_id)
    with pytest.raises(ValueError, match="must not override a built-in"):
        reservoir_profile.load_profile_config(model, profile_id, path)


def test_custom_profile_has_explicit_facts_without_fe_walter_inheritance(tmp_path, document, model):
    before = [asdict(cfg) for cfg in model.RESERVOIRS]
    path = save(tmp_path, document)
    config, provenance = reservoir_profile.load_profile_config(model, "custom_a", path)
    assert isinstance(config, model.ReservoirConfig)
    for key, expected in document["reservoir_config"].items():
        actual = getattr(config, key)
        assert actual == (tuple(expected) if key == "public_profile" else expected)
    assert config.normal_pool_af is None
    assert config.monthly_target_af is None
    assert config.elevation_storage_curve is None
    assert config.seasonal_target_curve is None
    assert config.flood_pool_bottom_ft is None
    assert config.flood_pool_top_ft is None
    assert config.operation_target_description == ""
    assert config.operation_scope == ""
    assert config.runtime_missing_inputs == ()
    assert config.observed_release_csv is None
    assert config.dkp_path is None
    assert config.dead_storage_af == 0.0
    assert config.inflow_scale == 1.0
    assert provenance["profile_source"] == "explicit_json"
    assert provenance["profile_file"] == str(path.resolve())
    assert provenance["profile_file_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert provenance["source_notes"] == document["source_notes"]
    assert provenance["reservoir_config"] == json.loads(json.dumps(asdict(config), allow_nan=False))
    assert json.loads(json.dumps(provenance, allow_nan=False)) == provenance
    assert "F.E. Walter" not in json.dumps(provenance)
    assert [asdict(cfg) for cfg in model.RESERVOIRS] == before


def test_valid_monthlies_curves_and_text_lists_normalize_for_native_config(tmp_path, document, model):
    values = document["reservoir_config"]
    values.update(
        monthly_target_af={str(month): 1000.0 + month for month in range(1, 13)},
        elevation_storage_curve=[[-10.0, 0.0], [0.0, 2000.0], [20.0, 5000.0]],
        seasonal_target_curve=[["01-01", -5.0], ["05-01", 10.0], ["12-31", -5.0]],
        flood_pool_bottom_ft=-5.0,
        flood_pool_top_ft=20.0,
        runtime_missing_inputs=["Custom downstream stage"],
        config_confirmed=False,
    )
    path = save(tmp_path, document)
    normalized = reservoir_profile.validate_profile_document(path, "custom_a")["reservoir_config"]
    assert normalized["monthly_target_af"] == {month: 1000.0 + month for month in range(1, 13)}
    assert normalized["elevation_storage_curve"] == ((-10.0, 0.0), (0.0, 2000.0), (20.0, 5000.0))
    assert normalized["seasonal_target_curve"] == (("01-01", -5.0), ("05-01", 10.0), ("12-31", -5.0))
    config, provenance = reservoir_profile.load_profile_config(model, "custom_a", path)
    assert config.monthly_target_af == normalized["monthly_target_af"]
    assert config.runtime_missing_inputs == ("Custom downstream stage",)
    assert config.config_confirmed is False
    assert provenance["reservoir_config"]["monthly_target_af"]["1"] == 1001.0
    assert provenance["reservoir_config"]["elevation_storage_curve"] == [[-10.0, 0.0], [0.0, 2000.0], [20.0, 5000.0]]
    assert json.loads(json.dumps(provenance, allow_nan=False)) == provenance


@pytest.mark.parametrize("field", [
    "name", "inflow_csv", "capacity_af", "initial_storage_af", "purpose", "river",
    "inflow_reservoir_key", "public_profile", "public_capacity_af", "min_release_cfs", "max_release_cfs",
])
def test_all_required_native_and_public_fields_must_be_declared(tmp_path, document, field):
    del document["reservoir_config"][field]
    with pytest.raises(ValueError, match="missing fields"):
        reservoir_profile.validate_profile_document(save(tmp_path, document), "custom_a")


@pytest.mark.parametrize("change,error", [
    ({"unexpected": True}, "unknown fields"),
    ({"inflow_reservoir_key": "custom_b"}, "must match profile_id"),
    ({"purpose": "unknown"}, "unknown reservoir purpose"),
    ({"name": " "}, "non-empty text"),
    ({"public_profile": []}, "explicit text values"),
    ({"public_profile": [12]}, "non-empty text"),
    ({"runtime_missing_inputs": "stage"}, "explicit text values"),
    ({"config_confirmed": "false"}, "must be boolean"),
    ({"capacity_af": 0.0}, "positive"),
    ({"capacity_af": True}, "numeric"),
    ({"public_capacity_af": -1.0}, "positive"),
    ({"initial_storage_af": 5001.0}, "must not exceed capacity_af"),
    ({"initial_storage_af": 5.0, "dead_storage_af": 10.0}, "below dead_storage_af"),
    ({"normal_pool_af": 5001.0}, "must not exceed capacity_af"),
    ({"min_release_cfs": -1.0}, "non-negative"),
    ({"min_release_cfs": 700.0}, "must not exceed max_release_cfs"),
    ({"inflow_scale": 0.0}, "positive"),
    ({"alpha": 1.1}, "must not exceed 1"),
])
def test_invalid_config_values_are_rejected(tmp_path, document, change, error):
    document["reservoir_config"].update(change)
    with pytest.raises((ValueError, TypeError), match=error):
        reservoir_profile.validate_profile_document(save(tmp_path, document), "custom_a")


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_nonfinite_json_values_are_rejected(tmp_path, document, constant):
    raw = json.dumps(document).replace('"capacity_af": 5000.0', '"capacity_af": ' + constant)
    path = tmp_path / "profile.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite|finite"):
        reservoir_profile.validate_profile_document(path, "custom_a")


@pytest.mark.parametrize("field,value", [
    ("profile_id", '"custom_a"'),
    ("name", '"other name"'),
    ("1", "1000.0"),
])
def test_duplicate_json_fields_are_rejected_at_every_nesting_level(tmp_path, document, field, value):
    document["reservoir_config"]["monthly_target_af"] = {str(m): 1000.0 for m in range(1, 13)}
    raw = json.dumps(document)
    marker = json.dumps(field) + ": "
    raw = raw.replace(marker, marker + value + ", " + marker, 1)
    path = tmp_path / "profile.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON field: " + field):
        reservoir_profile.validate_profile_document(path, "custom_a")


@pytest.mark.parametrize("change,error", [
    ({"monthly_target_af": {"1": 1000.0}}, "all 12 calendar months"),
    ({"monthly_target_af": {str(m): 5001.0 for m in range(1, 13)}}, "must not exceed capacity_af"),
    ({"monthly_target_af": {str(m): -1.0 for m in range(1, 13)}}, "non-negative"),
    ({"elevation_storage_curve": [[0.0, 0.0]]}, "ordered list of pairs"),
    ({"elevation_storage_curve": [[0.0, 0.0], [10.0]]}, "requires pairs"),
    ({"elevation_storage_curve": [[0.0, 0.0], [0.0, 1000.0]]}, "strictly increasing"),
    ({"elevation_storage_curve": [[0.0, 1000.0], [10.0, 900.0]]}, "strictly increasing"),
    ({"seasonal_target_curve": [["1-01", 5.0]]}, "MM-DD"),
    ({"seasonal_target_curve": [["02-29", 5.0]]}, "every calendar year"),
    ({"seasonal_target_curve": [["05-01", 5.0], ["01-01", 5.0]]}, "strictly ordered"),
    ({"seasonal_target_curve": [["01-01", 5.0], ["01-01", 6.0]]}, "strictly ordered"),
    ({"seasonal_target_curve": [["01-01", 5.0]]}, "explicit elevation_storage_curve"),
    ({"flood_pool_bottom_ft": 5.0}, "bottom and top levels"),
    ({"flood_pool_bottom_ft": 20.0, "flood_pool_top_ft": 10.0}, "in increasing order"),
    ({"elevation_storage_curve": [[0.0, 0.0], [10.0, 5000.0]],
      "seasonal_target_curve": [["01-01", 11.0]]}, "must lie within"),
    ({"elevation_storage_curve": [[0.0, 0.0], [10.0, 5000.0]],
      "flood_pool_bottom_ft": -1.0, "flood_pool_top_ft": 5.0}, "must lie within"),
])
def test_invalid_monthly_and_level_targets_are_rejected(tmp_path, document, change, error):
    document["reservoir_config"].update(change)
    with pytest.raises(ValueError, match=error):
        reservoir_profile.validate_profile_document(save(tmp_path, document), "custom_a")


@pytest.mark.parametrize("change,error", [
    ({"schema_version": "future"}, "unsupported"),
    ({"profile_id": "custom_b"}, "does not match"),
    ({"unknown": "field"}, "known schema fields"),
    ({"reservoir_config": None}, "JSON object"),
])
def test_invalid_document_schema_is_rejected(tmp_path, document, change, error):
    document.update(change)
    with pytest.raises((ValueError, TypeError), match=error):
        reservoir_profile.validate_profile_document(save(tmp_path, document), "custom_a")


def test_two_custom_reservoirs_and_reloads_have_independent_mutable_values(tmp_path, document, model):
    document["reservoir_config"]["monthly_target_af"] = {str(m): 1000.0 for m in range(1, 13)}
    first_path = save(tmp_path, document, "a.json")
    other = deepcopy(document)
    other["profile_id"] = "custom_b"
    other["reservoir_config"].update(
        name="Custom B Reservoir", river="Custom B River", inflow_reservoir_key="custom_b",
        public_profile=["Custom B public fact"], initial_storage_af=3000.0,
        monthly_target_af={str(m): 3000.0 for m in range(1, 13)},
    )
    second_path = save(tmp_path, other, "b.json")
    first, first_provenance = reservoir_profile.load_profile_config(model, "custom_a", first_path)
    second, _ = reservoir_profile.load_profile_config(model, "custom_b", second_path)
    reloaded, _ = reservoir_profile.load_profile_config(model, "custom_a", first_path)
    first.monthly_target_af[1] = 123.0
    first_provenance["reservoir_config"]["monthly_target_af"]["2"] = 456.0
    assert first.monthly_target_af[2] == 1000.0
    assert second.monthly_target_af[1] == 3000.0
    assert reloaded.monthly_target_af[1] == 1000.0
    assert first.public_profile == ("Custom A public fact",)
    assert second.public_profile == ("Custom B public fact",)
    assert first is not second and first is not reloaded


def test_pinned_schema_checksum_is_enforced(tmp_path):
    source = tmp_path / "third_party/anik_v3_7/reservoir_model.py"
    source.parent.mkdir(parents=True)
    source.write_bytes((ROOT / "third_party/anik_v3_7/reservoir_model.py").read_bytes() + b"\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        reservoir_profile.builtin_profile_ids(tmp_path)


def test_model_dataclass_schema_drift_is_rejected(tmp_path, document):
    changed_model = SimpleNamespace(RESERVOIRS=[], ReservoirConfig=make_dataclass("ChangedConfig", [("name", str)]))
    with pytest.raises(ValueError, match="fields differ from pinned profile schema"):
        reservoir_profile.load_profile_config(changed_model, "custom_a", save(tmp_path, document))


def test_profile_file_change_during_validation_is_rejected(tmp_path, document, model, monkeypatch):
    path = save(tmp_path, document)
    validate = reservoir_profile.validate_profile_document

    def validate_then_change(profile_path, profile_id):
        result = validate(profile_path, profile_id)
        profile_path.write_bytes(profile_path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(reservoir_profile, "validate_profile_document", validate_then_change)
    with pytest.raises(ValueError, match="changed during validation"):
        reservoir_profile.load_profile_config(model, "custom_a", path)
