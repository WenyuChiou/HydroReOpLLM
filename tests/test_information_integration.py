"""Causal input selection and outcome checks with no real model or network."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from string import Template
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

from llm_reservoir_agent.configured_backend import ConfiguredBackend
from llm_reservoir_agent.contracts import ReservoirObservation
from llm_reservoir_agent.prompt import PromptSpec
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings, verify_settings_output
from test_llm_network import network


class InformationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        (self.root/"prompt.txt").write_text("Operate using only these selected inputs: $information", encoding="utf-8")

    def configuration(self, count=1, days=3, live=False):
        config, rows = network(count=count, days=days)
        (self.root/"case.json").write_text(json.dumps(dict(schema_version="llm-reservoir-network-case.v1",
            data_kind="synthetic_fixture", network=config, inflow_records=rows)), encoding="utf-8")
        data = dict(schema_version="llm-reservoir-experiment.v1", case="case.json", run_id="information-test",
            output="run", max_calls=count*days if live else 0,
            information_sources={"gauge":dict(type="simulation", quantity="flow", unit="m3/s", location="Outlet"),
                                 "demand":dict(type="static", quantity="required_flow", unit="m3/s", location="use-point", value=10)},
            information_profiles={"operating":dict(fields={"downstream":dict(source="gauge", required=False, history=2),
                                                          "demand":dict(source="demand")})},
            agents={f"operator-{i}":dict(reservoir=name, mode="llm" if live else "offline", prompt="prompt.txt",
                information="operating", **({"model":"local"} if live else {"release_cms":5}))
                for i, name in enumerate(config["reservoirs"])})
        if live:
            data["models"] = {"local":dict(provider="ollama", model="test-fixture", base_url="http://localhost:11434", temperature=0.7)}
        return data

    def save(self, data):
        p=self.root/"experiment.yaml"
        p.write_text(yaml.safe_dump(data), encoding="utf-8")
        return load_settings(p)

    @staticmethod
    def reply(release=5):
        return dict(done=True, done_reason="stop", message={"content":json.dumps(dict(schema_version="reservoir-action.v1", release_cms=release))})

    def test_previous_completed_downstream_flow_and_history(self):
        settings=self.save(self.configuration())
        records, result=run_settings(settings)
        samples=[r["observation"]["context"]["decision_information"]["fields"]["downstream"] for r in records["R1"]]
        self.assertEqual(samples[0]["status"], "MISSING")
        self.assertEqual(samples[1]["value"], records["R1"][0]["transition"]["total_outflow_cms"])
        self.assertEqual(len(samples[2]["history"]),2)
        self.assertEqual(samples[1]["available_at"],"2020-01-02T00:00:00Z")
        self.assertLess(result["summary"]["max_system_balance_residual_m3"],1e-6)
        self.assertEqual(verify_run(settings.report["output"],require_offline=True)["days"],3)

    def test_downstream_information_changes_mock_decisions_causally(self):
        settings=self.save(self.configuration(live=True))
        payloads=[]
        def transport(url,payload,headers,timeout):
            info=json.loads(payload["messages"][1]["content"].split(": ",1)[1])
            payloads.append(info)
            gauge=info["fields"]["downstream"]
            return self.reply(2 if gauge["status"]=="AVAILABLE" and gauge["value"]>3 else 5)
        with patch("urllib.request.urlopen", side_effect=AssertionError("real network forbidden")):
            records, result=run_settings(settings,allow_network=True,transport=transport)
        self.assertEqual([r["action"]["release_cms"] for r in records["R1"]],[5,2,5])
        self.assertEqual(payloads[2]["fields"]["downstream"]["value"],2)
        self.assertEqual(result["summary"]["observed_network_calls"],3) # Mock attempts only.
        self.assertEqual(verify_run(settings.report["output"])["days"],3)

    def test_required_first_day_feedback_stops_before_transport_or_physics(self):
        data=self.configuration(live=True)
        data["information_profiles"]["operating"]["fields"]["downstream"]["required"]=True
        settings=self.save(data);transport=Mock(return_value=self.reply())
        with self.assertRaisesRegex(ValueError,"required field"):
            run_settings(settings,allow_network=True,transport=transport)
        transport.assert_not_called()
        self.assertEqual((self.root/"run/physics.jsonl").read_bytes(),b"")

    def test_profiles_are_reservoir_local_and_native_water_is_unchanged(self):
        data=self.configuration(count=3,days=31)
        data["information_sources"]["other_demand"]=dict(type="static",quantity="required_flow",unit="m3/s",location="other-user",value=20)
        data["information_profiles"]["other"]=dict(fields={"demand":dict(source="other_demand")})
        data["agents"]["operator-1"]["information"]="other"
        settings=self.save(data);records,result=run_settings(settings)
        self.assertEqual(records["R1"][0]["observation"]["context"]["decision_information"]["fields"]["demand"]["value"],10)
        self.assertEqual(records["R2"][0]["observation"]["context"]["decision_information"]["fields"]["demand"]["value"],20)
        self.assertEqual(result["summary"]["observed_network_calls"],0)
        self.assertLess(verify_run(settings.report["output"],require_offline=True)["max_system_balance_residual_m3"],1e-6)

    def test_outcome_failure_is_separate_from_original_request_audit(self):
        data=self.configuration()
        data["outcome_checks"]={"supply":dict(node="Outlet",minimum_information=dict(agent="operator-0",field="demand")),
                                "channel":dict(node="Outlet",maximum_cms=20)}
        settings=self.save(data);_,result=run_settings(settings)
        self.assertEqual(result["summary"]["outcome_audit_counts"],dict(FAIL=3,PASS=3))
        self.assertEqual(result["summary"]["audit_counts"],dict(UNKNOWN=3))
        self.assertIsNone(result["summary"]["operating_strategy_accepted"])
        verify_run(settings.report["output"],require_offline=True)

    def test_optional_unknown_outcome_bound_remains_unknown(self):
        data=self.configuration()
        data["outcome_checks"]={"monitor":dict(node="Outlet",maximum_information=dict(agent="operator-0",field="downstream"))}
        settings=self.save(data);_,result=run_settings(settings)
        self.assertEqual(result["summary"]["outcome_audit_counts"],dict(UNKNOWN=1,PASS=2))
        verify_run(settings.report["output"],require_offline=True)

    def test_invalid_bindings_units_and_incomplete_information_pair_rejected(self):
        base=self.configuration()
        variants=[]
        d=deepcopy(base);d["agents"]["operator-0"]["information"]="absent";variants.append(d)
        d=deepcopy(base);d["information_sources"]["gauge"]["unit"]="cfs";variants.append(d)
        d=deepcopy(base);d["information_sources"]["gauge"]["location"]="absent";variants.append(d)
        d=deepcopy(base);d["agents"]["operator-0"].pop("information");variants.append(d)
        d=deepcopy(base);d["outcome_checks"]={"bad":dict(node="absent",maximum_cms=2)};variants.append(d)
        d=deepcopy(base);d["information_sources"]["demand"]["unit"]="MW";d["outcome_checks"]={"bad":dict(node="Outlet",minimum_information=dict(agent="operator-0",field="demand"))};variants.append(d)
        for data in variants:
            with self.subTest(data=data),self.assertRaises((ValueError,TypeError)):
                self.save(data)

    def test_negative_dynamic_bound_stops_before_model(self):
        data=self.configuration(live=True);data["information_sources"]["demand"]["value"]=-1
        data["outcome_checks"]={"supply":dict(node="Outlet",minimum_information=dict(agent="operator-0",field="demand"))}
        settings=self.save(data);transport=Mock(return_value=self.reply())
        with self.assertRaises(ValueError):run_settings(settings,allow_network=True,transport=transport)
        transport.assert_not_called()

    def test_incomplete_reply_with_information_stops_before_physics(self):
        settings=self.save(self.configuration(live=True));reply=self.reply();reply["done"]=False
        with self.assertRaises(ValueError):run_settings(settings,allow_network=True,transport=Mock(return_value=reply))
        self.assertEqual((self.root/"run/physics.jsonl").read_bytes(),b"")

    def test_source_file_changed_after_check_is_rejected(self):
        data=self.configuration()
        csv=self.root/"gauge.csv";csv.write_text("valid_time,available_at,value\n2019-12-31T00:00:00Z,2020-01-01T00:00:00Z,3\n")
        data["information_sources"]["gauge"].update(type="csv",path="gauge.csv",kind="observation")
        settings=self.save(data);csv.write_text(csv.read_text().replace(",3\n",",4\n"))
        with self.assertRaisesRegex(ValueError,"changed after"):run_settings(settings)

    def test_rehashed_outcome_corruption_is_rejected(self):
        data=self.configuration();data["outcome_checks"]={"limit":dict(node="Outlet",maximum_cms=6)}
        settings=self.save(data);run_settings(settings)
        p=self.root/"run/outcome_audit.jsonl";events=[json.loads(line) for line in p.read_text().splitlines()]
        events[0]["routed_flow_cms"]=999;p.write_text("".join(json.dumps(e)+"\n" for e in events))
        for name in ("summary.json","index.json"):
            p2=self.root/"run"/name;value=json.loads(p2.read_bytes())
            value["summary"]["additional_output_files"]["outcome_audit.jsonl"]=hashlib.sha256(p.read_bytes()).hexdigest()
            p2.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,"outcome audit differs"):verify_run(self.root/"run")

    def test_old_prompt_rendering_has_no_automatic_new_fields(self):
        observation=ReservoirObservation(0,"2020-01-01",2,3,state={"storage_m3":100})
        template="$agent_id $observation $knowledge $previous_transition"
        backend=ConfiguredBackend(agent_id="op",mode="offline",prompt_spec=PromptSpec("test","1",template),knowledge_texts={})
        expected=Template(template).substitute(agent_id='"op"',knowledge="{}",previous_transition="null",
            observation=json.dumps(dict(observed_hydrology=observation.to_dict(),static_context={}),sort_keys=True,separators=(",",":")))
        self.assertEqual(backend._messages(observation)[1]["content"],expected)
        self.assertNotIn("decision_information",expected)

    def test_local_inflow_and_storage_histories_include_current_and_committed_steps(self):
        data=self.configuration()
        for quantity, unit in (("inflow", "m3/s"), ("storage", "m3")):
            data["information_sources"][quantity]=dict(type="simulation",quantity=quantity,unit=unit,location="R1")
            data["information_profiles"]["operating"]["fields"][quantity]=dict(source=quantity,history=3)
        settings=self.save(data);records,_=run_settings(settings)
        fields=records["R1"][2]["observation"]["context"]["decision_information"]["fields"]
        self.assertEqual([r["value"] for r in fields["storage"]["history"]],
                         [r["observation"]["state"]["storage_m3"] for r in records["R1"]])
        self.assertEqual([r["value"] for r in fields["inflow"]["history"]],
                         [r["observation"]["inflow_cms"] for r in records["R1"]])
        verify_run(self.root/"run",require_offline=True)

    def test_extension_forecasts_are_verified_without_contacting_provider(self):
        data=self.configuration();calls=[]
        data["information_sources"]["prediction"]=dict(type="extension",provider="forecast",kind="forecast",
                                                        quantity="flow",unit="m3/s",location="external-control")
        data["information_profiles"]["operating"]["fields"]["forecast"]=dict(source="prediction",history=2)
        def provider(**kwargs):
            calls.append(kwargs["decision_time"])
            return [dict(issued_at="2019-12-31T00:00:00Z",available_at="2019-12-31T01:00:00Z",
                         valid_time=f"2020-01-0{day}T00:00:00Z",value=day) for day in (1,2,3,4)]
        provider.version="synthetic-forecast-v1"
        registry={"forecast":provider}
        path=self.root/"experiment.yaml";path.write_text(yaml.safe_dump(data))
        settings=load_settings(path,information_providers=registry)
        run_settings(settings,information_providers=registry)
        verify_settings_output(settings,information_providers=registry)
        self.assertEqual(len(calls),3)

    def test_operating_purpose_changes_information_not_physical_configuration(self):
        # These are input-contract fixtures, not validated operating policies.
        for purpose, quantity, unit, value in (("flood_control","flood_stage","m",4.0),
                                              ("water_supply","water_demand","m3/s",10.0),
                                              ("hydropower","turbine_head","m",20.0)):
            with self.subTest(purpose=purpose):
                data=self.configuration()
                data["output"]=purpose
                data["information_sources"]["objective"]=dict(type="static",quantity=quantity,unit=unit,
                                                               location="purpose-control",value=value)
                data["information_profiles"]["operating"]["fields"]["objective"]=dict(source="objective")
                settings=self.save(data);records,result=run_settings(settings)
                self.assertEqual(records["R1"][0]["observation"]["context"]["decision_information"]["fields"]["objective"]["quantity"],quantity)
                self.assertEqual(result["summary"]["observed_network_calls"],0)
                self.assertLess(verify_run(self.root/purpose,require_offline=True)["max_system_balance_residual_m3"],1e-6)

    def test_provider_version_changed_after_check_stops_before_source_access(self):
        data=self.configuration();calls=[]
        data["information_sources"]["external"]=dict(type="extension",provider="station",quantity="flow",unit="m3/s",location="external-station")
        data["information_profiles"]["operating"]["fields"]["external"]=dict(source="external")
        def provider(**_):
            calls.append(1)
            return []
        provider.version="v1"
        path=self.root/"experiment.yaml";path.write_text(yaml.safe_dump(data))
        settings=load_settings(path,information_providers={"station":provider})
        provider.version="v2"
        with self.assertRaisesRegex(ValueError,"changed after"):
            run_settings(settings,information_providers={"station":provider})
        self.assertEqual(calls,[])


    @staticmethod
    def fixed_one_day(config, rows, policies, *, project_root, information_runtime):
        """Keep this corruption fixture independent of native simulation/model calls."""
        from llm_reservoir_agent.physics import PhysicalConfig, apply_transition
        from llm_reservoir_agent.network import validate_inflows
        from llm_reservoir_agent.balance import network_balance
        assert len(rows) == 1 and set(policies) == {"R1"}
        topology, local = validate_inflows(config, rows)
        physical = config["reservoirs"]["R1"]["physical"]
        storage, inflow = physical["initial_storage_m3"], local["I1"][0]
        state = {k: physical[k] for k in ("capacity_m3", "dead_storage_m3",
                 "minimum_release_cms", "maximum_release_cms", "dt_seconds")}
        state["storage_m3"] = storage
        observation = ReservoirObservation(
            0, rows[0]["date"], inflow,
            min(physical["maximum_release_cms"], inflow+(storage-physical["dead_storage_m3"])/86400),
            state=state, context=dict(reservoir_id=physical["reservoir_id"],
                evaporation_m3=0.0, seepage_m3=0.0)).to_dict()
        observation["context"]["decision_information"] = information_runtime.catalog.build(
            "operating", decision_time=rows[0]["date"], timestep=0, observation=observation)
        action = policies["R1"].decide(observation)
        transition = apply_transition(PhysicalConfig(**physical), storage, inflow, action["release_cms"]).to_dict()
        record = dict(observation=observation, action=action, transition=transition,
                      policy_id=policies["R1"].policy_id)
        policies["R1"].record_transition(record)
        records = {"R1": [record]}
        q = transition["total_outflow_cms"]
        flows = {"I1": [inflow], "R1": [q], "Outlet": [q]}
        ledger, reaches = network_balance(topology, local, flows, records, [rows[0]["date"]])
        return records, dict(days=1, reservoir_count=1, network_balance=ledger,
            reach_volume_trace=reaches, routed_flows_cms=flows,
            max_system_balance_residual_m3=0.0, final_channel_storage_m3=0.0)

    def test_optional_catalog_sections_initialize_without_native_or_model_calls(self):
        for missing in ("information_sources", "information_profiles"):
            with self.subTest(missing=missing):
                data = self.configuration(days=1)
                data.pop(missing)
                data.get("information_profiles", {}).clear()
                data["agents"]["operator-0"].pop("information")
                (self.root/"prompt.txt").write_text("$observation", encoding="utf-8")
                settings = self.save(data)
                transport = Mock(side_effect=AssertionError("network forbidden"))
                with patch("llm_reservoir_agent.experiment.run_experiment", return_value=({}, {})) as run:
                    run_settings(settings, transport=transport)
                    run.assert_called_once()
                    self.assertEqual(run.call_args.kwargs["information_runtime"].configuration["bindings"], {})
                transport.assert_not_called()

    def test_current_settings_reject_rehashed_criteria_and_other_saved_declarations(self):
        data = self.configuration(days=1)
        data["outcome_checks"] = {"supply": dict(node="Outlet", minimum_cms=10)}
        settings = self.save(data)
        transport = Mock(side_effect=AssertionError("network forbidden"))
        with patch("llm_reservoir_agent.experiment._run_network", side_effect=self.fixed_one_day):
            run_settings(settings, transport=transport)
        transport.assert_not_called()
        self.assertEqual(verify_settings_output(settings)["status"], "PASS")
        output = Path(settings.report["output"])
        names = ("experiment.json", "outcome_audit.jsonl", "summary.json", "index.json")
        original = {name: (output/name).read_bytes() for name in names}
        for variant in ("criterion", "catalog", "information_binding", "outcome_agent"):
            with self.subTest(variant=variant):
                for name, raw in original.items():
                    (output/name).write_bytes(raw)
                experiment = json.loads(original["experiment.json"])
                if variant == "criterion":
                    # Recreate the confirmed FAIL -> PASS attack, including its hashes.
                    experiment["outcome_checks"]["supply"]["minimum_cms"] = 1
                    events = [json.loads(line) for line in original["outcome_audit.jsonl"].splitlines()]
                    self.assertEqual(events[0]["status"], "FAIL")
                    events[0]["minimum_cms"], events[0]["status"] = 1, "PASS"
                    (output/"outcome_audit.jsonl").write_text(
                        "".join(json.dumps(e)+"\n" for e in events), encoding="utf-8", newline="\n")
                elif variant == "catalog":
                    experiment["information_config"]["sources"]["demand"]["value"] = 1
                elif variant == "information_binding":
                    experiment["information_config"]["bindings"]["R1"] = "other"
                else:
                    experiment["information_agents"]["operator-0"]["reservoir"] = "other"
                (output/"experiment.json").write_text(json.dumps(experiment), encoding="utf-8")
                for name in ("summary.json", "index.json"):
                    value = json.loads(original[name])
                    summary = value["summary"]
                    summary["output_files"]["experiment.json"] = hashlib.sha256((output/"experiment.json").read_bytes()).hexdigest()
                    if variant == "criterion":
                        summary["outcome_checks"]["supply"]["minimum_cms"] = 1
                        summary["outcome_audit_counts"] = {"PASS": 1}
                        summary["additional_output_files"]["outcome_audit.jsonl"] = hashlib.sha256((output/"outcome_audit.jsonl").read_bytes()).hexdigest()
                    (output/name).write_text(json.dumps(value), encoding="utf-8")
                if variant == "criterion":
                    with self.assertRaisesRegex(ValueError, "cached run differs"):
                        verify_settings_output(settings)
                else:
                    # Check authoritative inputs before delegating self-consistency inspection.
                    with patch("llm_reservoir_agent.verification.verify_run", return_value={"status": "PASS"}) as inspect:
                        with self.assertRaisesRegex(ValueError, "cached run differs"):
                            verify_settings_output(settings)
                        inspect.assert_not_called()
        for name, raw in original.items():
            (output/name).write_bytes(raw)
        self.assertEqual(verify_settings_output(settings)["status"], "PASS")
