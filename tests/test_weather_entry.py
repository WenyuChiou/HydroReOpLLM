"""Configured weather-to-operation entry: real native runoff/routing, fake LLM only."""
from copy import deepcopy
import csv
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]


def make_bundle(folder, *, llm=False):
    """Use arbitrary names; accepted native parameters supply a small test model."""
    native = yaml.safe_load((ROOT / "data/accepted/fe_walter_hydrology.yaml").read_text())
    unit = native["WaterSystem"]["Outlets"][0]
    aggregate = native["WaterSystem"]["Outlets"][-1]
    native["WaterSystem"].update(StartDate="2020/02/27", EndDate="2020/03/02",
                               DataLength=5, NumSubbasins=2, Outlets=["headwater", "inlet_sum"])
    native["RainfallRunoff"] = {"headwater": native["RainfallRunoff"][unit],
                               "inlet_sum": native["RainfallRunoff"][aggregate]}
    native["Routing"] = {"inlet_sum": {
        "headwater": native["Routing"][aggregate][unit],
        "inlet_sum": native["Routing"][aggregate][aggregate]}}
    (folder / "hydrology.yaml").write_text(yaml.safe_dump(native), encoding="utf-8")
    with (folder / "weather.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "subbasin_id", "precipitation_mm", "temperature_c", "pet_cm"])
        for step in range(5):
            writer.writerow([(date(2020, 2, 27)+timedelta(days=step)).isoformat(),
                             "headwater", 10+step, 10, 0.1])
    physical = dict(reservoir_id="lake-operator", capacity_m3=1000000.0,
                    dead_storage_m3=0.0, initial_storage_m3=500000.0,
                    minimum_release_cms=0.0, maximum_release_cms=20.0, dt_seconds=86400.0)
    network = dict(schema_version="llm-reservoir-network.v1", start_date="2020-02-28",
                   reservoirs={"lake": {"inflow_node": "arrival", "physical": physical}},
                   connections=[dict(source="lake", target="river", unit_hydrograph=[0.0, 1.0])],
                   outlet="river")
    (folder / "reservoirs.json").write_text(json.dumps({
        "schema_version": "reservoir-physical-case.v1", "data_kind": "synthetic_fixture",
        "network": network}), encoding="utf-8")
    (folder / "prompt.txt").write_text("Choose a release. $observation $previous_transition $knowledge",
                                       encoding="utf-8")
    data = dict(schema_version="hydroops-coupled-simulation.v1", run_id="weather-demo",
                output="output", case="reservoirs.json", start_date="2020-02-28",
                end_date="2020-03-02", max_calls=None if llm else 0,
                hydrology=dict(model="hydrology.yaml", forcing="weather.csv",
                               zero_flow_nodes=["inlet_sum"],
                               inflow_bindings={"arrival": {"routed": "inlet_sum"},
                                                "river": {"constant": 0}}))
    if llm:
        data["models"] = {"local": dict(provider="ollama", model="fixture-model",
                                         base_url="http://localhost:11434")}
        data["agents"] = {"operator": dict(reservoir="lake", strategy="configured", mode="llm",
                                            model="local", prompt="prompt.txt")}
    else:
        with (folder / "reference.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle); writer.writerow(["date", "reservoir", "flow"])
            for step in range(365):
                writer.writerow([(date(2019, 1, 1)+timedelta(days=step)).isoformat(), "lake-operator", 0.2])
        source = dict(path="reference.csv", sha256=hashlib.sha256((folder/"reference.csv").read_bytes()).hexdigest(),
                      date_column="date", flow_column="flow", flow_to_cms=1.0,
                      reservoir_column="reservoir", reservoir_value="lake-operator")
        stats = dict(schema_version="reservoir-benchmark-statistics.v1", reservoir_id="lake-operator",
                     reference_start="2019-01-01", reference_end="2019-12-31", source=source,
                     mean_inflow_cms=0.2, monthly_mean_inflow_cms={str(m): 0.2 for m in range(1, 13)},
                     reference_day_count=365)
        (folder / "statistics.json").write_text(json.dumps(stats), encoding="utf-8")
        data["agents"] = {"operator": dict(reservoir="lake", strategy="benchmark", mode="offline",
                                            benchmark={"statistics": "statistics.json"})}
    (folder / "simulation.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return data


class WeatherEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = make_bundle(self.root)

    def save(self):
        (self.root / "simulation.yaml").write_text(yaml.safe_dump(self.data), encoding="utf-8")

    def test_check_reads_all_configuration_without_simulation_or_output(self):
        from llm_reservoir_agent.coupled import load_coupled_settings
        with patch("hydrocnhs.Model", side_effect=AssertionError("check must not simulate")):
            settings = load_coupled_settings(self.root / "simulation.yaml")
        self.assertEqual(settings.report["days"], 4)
        self.assertEqual(settings.report["hydrology_days"], 5)
        self.assertEqual(settings.report["planned_llm_calls"], 0)
        self.assertFalse((self.root / "output").exists())

    def test_real_weather_rule_and_delayed_downstream_close_water_balance(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
        from llm_reservoir_agent.verification import verify_run
        _, summary = run_coupled(load_coupled_settings(self.root / "simulation.yaml"))
        verified = verify_run(self.root / "output/operation", require_offline=True)
        self.assertEqual(verified["days"], 4)
        self.assertEqual(verified["observed_network_calls"], 0)
        self.assertLess(verified["max_system_balance_residual_m3"], 1e-6)
        self.assertEqual(summary["status"], "COMPLETED")
        with (self.root / "output/inflows.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([r["date"] for r in rows if r["node"] == "arrival"],
                         ["2020-02-28", "2020-02-29", "2020-03-01", "2020-03-02"])
        self.assertTrue(any(float(r["local_inflow_cms"]) > 0 for r in rows if r["node"] == "arrival"))
        with (self.root / "output/operation/network_flows.csv").open(newline="") as handle:
            flows = [r for r in csv.DictReader(handle) if r["node"] == "river"]
        self.assertEqual(float(flows[0]["routed_flow_cms"]), 0.0)
        self.assertGreater(float(flows[1]["routed_flow_cms"]), 0.0)

    def test_real_weather_to_llm_uses_existing_operation_and_committed_history(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
        from llm_reservoir_agent.verification import verify_run
        self.data = make_bundle(self.root, llm=True)
        sent = []
        def transport(url, payload, headers, timeout):
            sent.append(deepcopy(payload))
            return {"done": True, "done_reason": "stop", "message": {"content": json.dumps({
                "schema_version": "reservoir-action.v1", "release_cms": 0.1})}}
        run_coupled(load_coupled_settings(self.root / "simulation.yaml"),
                    allow_network=True, transport=transport)
        self.assertEqual(len(sent), 4)
        self.assertIn('"storage_end_m3"', sent[1]["messages"][-1]["content"])
        self.assertEqual(verify_run(self.root / "output/operation")["observed_network_calls"], 4)

    def test_missing_weather_day_is_rejected_before_simulation(self):
        from llm_reservoir_agent.coupled import load_coupled_settings
        p = self.root / "weather.csv"; p.write_text("\n".join(p.read_text().splitlines()[:-1])+"\n")
        with self.assertRaisesRegex(ValueError, "weather|forcing|day"):
            load_coupled_settings(self.root / "simulation.yaml")
        self.assertFalse((self.root / "output").exists())

    def test_overlapping_routed_and_local_inflow_is_rejected(self):
        from llm_reservoir_agent.coupled import load_coupled_settings
        self.data["hydrology"]["inflow_bindings"]["river"] = {"runoff": "headwater"}; self.save()
        with self.assertRaisesRegex(ValueError, "overlap|twice|duplicate"):
            load_coupled_settings(self.root / "simulation.yaml")

    def test_changed_weather_refuses_reusing_prepared_hydrology(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, prepare_coupled, run_coupled
        prepare_coupled(load_coupled_settings(self.root / "simulation.yaml"))
        p = self.root / "weather.csv"; p.write_text(p.read_text().replace(",10,10,", ",11,10,"))
        with self.assertRaisesRegex(ValueError, "changed|differ|match"):
            run_coupled(load_coupled_settings(self.root / "simulation.yaml"))
        self.assertFalse((self.root / "output/operation").exists())

    def test_native_abcd_uses_the_same_generic_entry(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
        from llm_reservoir_agent.verification import verify_run
        path = self.root / "hydrology.yaml"
        native = yaml.safe_load(path.read_text())
        native["WaterSystem"]["RainfallRunoff"] = "ABCD"
        for spec in native["RainfallRunoff"].values():
            spec["Inputs"] = dict(Area=100.0, Latitude=41.0, XL=10.0, SnowS=0.0)
            spec["Pars"] = dict(a=0.95, b=100.0, c=0.5, d=0.5, Df=0.2)
        path.write_text(yaml.safe_dump(native))
        run_coupled(load_coupled_settings(self.root / "simulation.yaml"))
        self.assertEqual(verify_run(self.root / "output/operation", require_offline=True)["days"], 4)

    def test_cli_check_prepare_run_and_verify_share_one_configuration(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from llm_reservoir_agent.workflow import main
        config = str(self.root / "simulation.yaml")
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["check", config]), 0)
            self.assertEqual(main(["prepare", config]), 0)
            before = (self.root / "output/inflows.csv").read_bytes()
            self.assertEqual(main(["run", config]), 0)
            self.assertEqual(main(["verify", str(self.root / "output/operation"), "--require-offline"]), 0)
        self.assertEqual((self.root / "output/inflows.csv").read_bytes(), before)

    def test_cli_resume_restores_saved_llm_prefix_without_rerunning_weather(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
        from llm_reservoir_agent.workflow import main
        from llm_reservoir_agent.verification import verify_run
        self.data = make_bundle(self.root, llm=True)
        sent = []
        def reply():
            return {"done": True, "done_reason": "stop", "message": {"content": json.dumps({
                "schema_version": "reservoir-action.v1", "release_cms": 0.1})}}
        def interrupted(*args):
            sent.append(args)
            if len(sent) == 2:
                raise TimeoutError("fixture interruption")
            return reply()
        with self.assertRaises(TimeoutError):
            run_coupled(load_coupled_settings(self.root/"simulation.yaml"),
                        allow_network=True, transport=interrupted)
        continued = []
        def transport(*args):
            continued.append(args); return reply()
        with patch("llm_reservoir_agent.configured_backend.http_json_transport", transport), \
                patch("llm_reservoir_agent.coupled.simulate_weather", side_effect=AssertionError("weather rerun")), \
                redirect_stdout(StringIO()):
            main(["resume", str(self.root/"simulation.yaml"), "--from-run", str(self.root/"output/operation"),
                  "--output", str(self.root/"continued"), "--run-id", "continued", "--allow-network"])
        self.assertEqual(len(continued), 3)
        self.assertEqual(verify_run(self.root/"continued")["days"], 4)

    def test_no_network_permission_stops_before_weather_preparation(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
        self.data = make_bundle(self.root, llm=True)
        with patch("llm_reservoir_agent.coupled.simulate_weather", side_effect=AssertionError("weather ran")):
            with self.assertRaisesRegex(ValueError, "allow-network"):
                run_coupled(load_coupled_settings(self.root/"simulation.yaml"))
        self.assertFalse((self.root/"output").exists())

    def test_generated_method_cannot_change_by_refreshing_its_file_hash(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, prepare_coupled, run_coupled
        settings = load_coupled_settings(self.root/"simulation.yaml")
        prepare_coupled(settings)
        path = self.root/"output/experiment.yaml"
        data = yaml.safe_load(path.read_text()); data["agents"]["operator"]["benchmark"]["alpha"] = 0.9
        path.write_text(yaml.safe_dump(data))
        manifest = self.root/"output/preparation.json"; value = json.loads(manifest.read_text())
        value["generated_files"]["experiment.yaml"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "settings differ"):
            run_coupled(settings)

    def test_negative_or_nonfinite_weather_never_reaches_the_model(self):
        from llm_reservoir_agent.coupled import load_coupled_settings
        path = self.root/"weather.csv"; original = path.read_text()
        for bad in ("-1", "nan"):
            with self.subTest(bad=bad):
                path.write_text(original.replace(",10,10,", ","+bad+",10,"))
                with self.assertRaisesRegex(ValueError, "finite|nonnegative"):
                    load_coupled_settings(self.root/"simulation.yaml")

    def test_changing_only_the_operator_reuses_verified_inflow_without_hydrology(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, prepare_coupled, run_coupled
        from llm_reservoir_agent.verification import verify_run
        prepare_coupled(load_coupled_settings(self.root/"simulation.yaml"))
        original = (self.root/"output/inflows.csv").read_bytes()
        self.data["output"] = "another-method"; self.data["run_id"] = "another-method"
        self.data["hydrology"]["prepared_from"] = "output"
        self.data["agents"]["operator"]["benchmark"]["alpha"] = 0.9
        self.save()
        with patch("llm_reservoir_agent.coupled.simulate_weather", side_effect=AssertionError("hydrology rerun")):
            run_coupled(load_coupled_settings(self.root/"simulation.yaml"))
        self.assertEqual((self.root/"another-method/inflows.csv").read_bytes(), original)
        self.assertEqual(verify_run(self.root/"another-method/operation", require_offline=True)["days"], 4)


    def test_generated_physics_cannot_change_by_refreshing_its_file_hash(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, prepare_coupled, run_coupled
        settings = load_coupled_settings(self.root/"simulation.yaml")
        prepare_coupled(settings)
        path = self.root/"output/case.json"
        value = json.loads(path.read_text())
        value["network"]["reservoirs"]["lake"]["physical"]["initial_storage_m3"] = 400000.0
        path.write_text(json.dumps(value))
        manifest = self.root/"output/preparation.json"; value = json.loads(manifest.read_text())
        value["generated_files"]["case.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "physical case differs"):
            run_coupled(settings)

    def test_existing_preparation_directory_never_reruns_hydrology(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, prepare_coupled
        (self.root/"output").mkdir()
        with patch("llm_reservoir_agent.coupled.simulate_weather", side_effect=AssertionError("weather rerun")):
            with self.assertRaises(FileExistsError):
                prepare_coupled(load_coupled_settings(self.root/"simulation.yaml"))


    def test_logical_audit_paths_and_opaque_context_are_not_file_resources(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
        from llm_reservoir_agent.verification import verify_run
        self.data = make_bundle(self.root, llm=True)
        self.data["auditors"] = {"storage": {"type": "field_range", "version": "1",
            "path": "observation.state.storage_m3", "minimum": 0, "maximum": 1000000}}
        self.data["agents"]["operator"].update(auditors=["storage"], context={"path": "logical/not-a-file"})
        self.data["information_sources"] = {"note": {"type": "static", "quantity": "note",
            "unit": "text", "location": "lake", "value": {"path": "logical/static-value"}}}
        self.save()
        def transport(*args):
            return {"done": True, "done_reason": "stop", "message": {"content": json.dumps({
                "schema_version": "reservoir-action.v1", "release_cms": 0.1})}}
        run_coupled(load_coupled_settings(self.root/"simulation.yaml"), allow_network=True, transport=transport)
        compiled = yaml.safe_load((self.root/"output/experiment.yaml").read_text())
        self.assertEqual(compiled["auditors"]["storage"]["path"], "observation.state.storage_m3")
        self.assertEqual(compiled["agents"]["operator"]["context"]["path"], "logical/not-a-file")
        self.assertEqual(compiled["information_sources"]["note"]["value"]["path"], "logical/static-value")
        self.assertEqual(verify_run(self.root/"output/operation")["audit_counts"], {"PASS": 4})


    def test_optional_auditor_profile_file_is_rebased_but_reference_profile_id_is_not(self):
        from llm_reservoir_agent.coupled import load_coupled_settings, _operation_document
        settings = load_coupled_settings(self.root/"simulation.yaml")
        settings.data["auditors"] = {"strategy": {"type": "dkp_strategy", "profile": "profile.json",
                                                  "version": "1", "knowledge_id": "operations"}}
        settings.data["agents"]["operator"] = {"reference": {"profile": "custom-reservoir",
                                                "profile_file": "native-profile.json"}}
        compiled = _operation_document(settings, self.root/"generated")
        self.assertEqual(compiled["auditors"]["strategy"]["profile"], str(self.root/"profile.json"))
        self.assertEqual(compiled["agents"]["operator"]["reference"]["profile"], "custom-reservoir")
        self.assertEqual(compiled["agents"]["operator"]["reference"]["profile_file"], str(self.root/"native-profile.json"))


if __name__ == "__main__":
    unittest.main()
