"""Actual CLI/HTTP/native-routing tests; the local server performs no inference.

All cases are new synthetic fixtures. Original experiments are never replayed.
The production driver, urllib transport, parser, physics and verifier are used.
"""
from datetime import date, timedelta
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from threading import Thread

import pytest
import yaml

from llm_reservoir_agent.network import PROJECT_ROOT
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings
from test_llm_network import network
from test_passive_and_balance import passive


class FixtureServer:
    """Ollama/OpenAI-shaped replies over a real, private loopback HTTP socket."""

    def __init__(self):
        self.requests = []
        self.fault = None
        self.downstream_rule = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                user = json.loads(payload["messages"][1]["content"])
                owner.requests.append({"path": self.path, "payload": payload, "user": user})
                fields = user["info"]["fields"]
                selected = fields.get("target", {})
                release = selected.get("value", 5) if selected.get("status") == "AVAILABLE" else 5
                if owner.downstream_rule:
                    previous_flow = fields["downstream"]
                    release = 2 if previous_flow["status"] == "AVAILABLE" and previous_flow["value"] > 3 else 5
                action = {"schema_version": "reservoir-action.v1", "release_cms": release}
                content = json.dumps(action)
                if owner.fault == "invalid_json":
                    content = "This is not a JSON decision."
                elif owner.fault == "duplicate_key":
                    content = '{"schema_version":"reservoir-action.v1","release_cms":2,"release_cms":4}'
                elif owner.fault == "negative":
                    content = json.dumps({**action, "release_cms": -1})
                if self.path.endswith("/api/chat"):
                    reply = {"done": True, "done_reason": "stop", "message": {"content": content}}
                    if owner.fault == "incomplete":
                        reply.update(done=False, done_reason="length")
                    elif owner.fault == "missing_completion":
                        reply.pop("done")
                elif self.path.endswith("/chat/completions"):
                    reply = {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
                else:
                    self.send_error(404)
                    return
                body = json.dumps(reply).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


@pytest.fixture
def server():
    value = FixtureServer()
    try:
        yield value
    finally:
        value.close()


@pytest.fixture
def folder(request, tmp_path):
    saved = os.environ.get("HYDROOPS_E2E_OUTPUT")
    if not saved:
        return tmp_path
    destination = Path(saved) / ("test-" + sha256(request.node.nodeid.encode()).hexdigest()[:16])
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "fixture-test.json").write_text(json.dumps({"test": request.node.nodeid, "inference": False}), encoding="utf-8")
    return destination


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def make_case(folder, server, *, count=1, days=3, branch=False, provider="ollama", passive_last=False):
    config, rows = network(count=count, days=days, branch=branch)
    if passive_last:
        passive(config, f"R{count}")
    write_json(folder / "case.json", {"schema_version": "llm-reservoir-network-case.v1",
                                      "data_kind": "synthetic_fixture", "network": config,
                                      "inflow_records": rows})
    # Each placeholder is visible in one structured message and can be inspected.
    (folder / "prompt.txt").write_text(
        '{"agent":$agent_id,"info":$information,"observation":$observation,'
        '"previous":$previous_transition,"knowledge":$knowledge}', encoding="utf-8")
    controlled = [name for name in config["reservoirs"] if config["reservoirs"][name].get("operation_mode") != "passive_outlet"]
    settings = {"schema_version": "llm-reservoir-experiment.v1", "case": "case.json",
                "run_id": "new-synthetic-http-e2e", "output": "run",
                "max_calls": days * len(controlled),
                "models": {"fixture": {"provider": provider, "model": "gemma3:4b",
                                          "temperature": 0.7, "base_url": server.url}},
                "information_sources": {"demand": {"type": "static", "quantity": "required_flow",
                                                      "unit": "m3/s", "location": "external-use-point", "value": 4}},
                "information_profiles": {"selected": {"fields": {"target": {"source": "demand", "required": True}}}},
                "auditors": {"bounds": {"type": "release_bounds"}},
                "outcome_checks": {"supply": {"node": "Outlet", "minimum_information": {"agent": "operator-0", "field": "target"}}},
                "agents": {f"operator-{i}": {"reservoir": name, "mode": "llm", "model": "fixture",
                                                  "prompt": "prompt.txt", "information": "selected", "auditors": ["bounds"]}
                           for i, name in enumerate(controlled)}}
    return settings, config, rows


def save_settings(folder, data):
    path = folder / "experiment.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def cli(folder, command, argument, *, network_allowed=False, expect_success=True):
    argv = [sys.executable, str(PROJECT_ROOT / "run_experiment.py"), command, str(argument)]
    if network_allowed:
        argv.append("--allow-network")
    # Preserve actual subprocess bytes; Windows text writes translate line endings.
    proc = subprocess.run(argv, cwd=PROJECT_ROOT, capture_output=True, timeout=90)
    stdout_path = folder / f"{command}-stdout.log"
    stderr_path = folder / f"{command}-stderr.log"
    stdout_path.write_bytes(proc.stdout)
    stderr_path.write_bytes(proc.stderr)
    assert stdout_path.read_bytes() == proc.stdout and stderr_path.read_bytes() == proc.stderr
    write_json(folder / f"{command}-command.json", {
        "argv": argv, "exit_code": proc.returncode,
        "stdout_sha256": sha256(proc.stdout).hexdigest(),
        "stderr_sha256": sha256(proc.stderr).hexdigest(),
        "stdout_bytes": len(proc.stdout), "stderr_bytes": len(proc.stderr),
        "capture": "raw subprocess bytes",
    })
    if expect_success:
        assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    else:
        assert proc.returncode != 0, proc.stdout.decode("utf-8", errors="replace")
    return proc


def records(path):
    return [row.get("record", row) for row in [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]]


def run_cli_case(folder, server, data):
    settings = save_settings(folder, data)
    cli(folder, "check", settings)
    assert server.requests == [] and not (folder / "run").exists()
    cli(folder, "run", settings, network_allowed=True)
    cli(folder, "verify", folder / "run")
    verified = verify_run(folder / "run")
    assert verified["status"] == "PASS"
    assert verified["max_system_balance_residual_m3"] < 1e-6
    assert verified["max_routing_difference_cms"] == 0
    assert verified["observed_network_calls"] == len(server.requests) == data["max_calls"]
    for request in server.requests:
        payload = request["payload"]
        assert payload["model"] == "gemma3:4b"
        assert payload.get("options", payload)["temperature"] == 0.7
        assert payload.get("stream", False) is False
    write_json(folder / "fixture-http-requests.json", {"inference": False, "requests": server.requests})
    write_json(folder / "path-acceptance.json", {"status": "PASS", "entry": "formal CLI",
                                                "http": "loopback fixture; no inference", "verification": verified})
    return records(folder / "run/physics.jsonl")


@pytest.mark.parametrize("source_kind", ["static", "csv_observation", "csv_forecast", "native_inflow", "native_storage", "native_release", "native_downstream"])
def test_each_source_reaches_prompt_and_native_results(folder, server, source_kind):
    data, config, rows = make_case(folder, server)
    fields = data["information_profiles"]["selected"]["fields"]
    if source_kind.startswith("csv"):
        forecast = source_kind == "csv_forecast"
        if forecast:
            body = "issued_at,valid_time,available_at,value\n2019-12-31T00:00:00Z,2020-01-04T00:00:00Z,2019-12-31T01:00:00Z,4\n"
        else:
            body = "valid_time,available_at,value\n2019-12-31T00:00:00Z,2020-01-01T00:00:00Z,141.25866688595435\n2019-12-31T00:00:00Z,2020-01-05T00:00:00Z,999\n"
        (folder / "measurement.csv").write_text(body, encoding="utf-8")
        data["information_sources"]["demand"].update(type="csv", kind="forecast" if forecast else "observation", path="measurement.csv")
        data["information_sources"]["demand"].pop("value")
        if not forecast:
            data["information_sources"]["demand"]["unit"] = "cfs"
            fields["target"]["unit"] = "m3/s"
    elif source_kind.startswith("native"):
        quantity = source_kind.removeprefix("native_")
        if quantity == "downstream":
            quantity, location = "flow", "Outlet"
            server.downstream_rule = True
        else:
            location = "R1"
        data["information_sources"]["native"] = {"type": "simulation", "quantity": quantity,
                                                 "unit": "m3" if quantity == "storage" else "m3/s", "location": location}
        fields["downstream" if source_kind == "native_downstream" else "native"] = {
            "source": "native", "required": False, "history": 3}
    physical = run_cli_case(folder, server, data)
    messages = [r["user"] for r in server.requests]
    if source_kind in ("static", "csv_observation", "csv_forecast"):
        assert [m["info"]["fields"]["target"]["value"] for m in messages] == pytest.approx([4, 4, 4])
        assert [p["action"]["release_cms"] for p in physical] == pytest.approx([4, 4, 4])
    elif source_kind == "native_downstream":
        assert [p["action"]["release_cms"] for p in physical] == [5, 2, 5]
        assert messages[0]["info"]["fields"]["downstream"]["status"] == "MISSING"
        assert messages[1]["info"]["fields"]["downstream"]["value"] == physical[0]["transition"]["total_outflow_cms"]
        assert messages[2]["info"]["fields"]["downstream"]["value"] == physical[1]["transition"]["total_outflow_cms"]
    else:
        selected = [m["info"]["fields"]["native"] for m in messages]
        if source_kind == "native_release":
            assert selected[0]["status"] == "MISSING"
            assert selected[1]["value"] == physical[0]["transition"]["controlled_release_cms"]
        elif source_kind == "native_inflow":
            assert selected[0]["value"] == physical[0]["observation"]["inflow_cms"]
        else:
            assert selected[0]["value"] == physical[0]["observation"]["state"]["storage_m3"]
    assert messages[0]["previous"] is None
    assert messages[1]["previous"]["transition"]["storage_end_m3"] == physical[0]["transition"]["storage_end_m3"]
    # The saved rendered prompt and raw reply must be bound to each decision.
    decisions = records(folder / "run/decisions.jsonl")
    raw = [json.loads((folder / "run" / event["raw_policy_ref"]["path"]).read_text(encoding="utf-8")) for event in decisions]
    assert len(raw) == 3
    for m, raw_record in zip(messages, raw):
        trace = raw_record["backend_trace"]
        assert json.loads(trace["messages"][1]["content"])["info"] == m["info"]
        assert trace["raw_reply"] is not None and trace["parsed_action"] is not None


def test_python_extension_runs_full_native_and_http_path(folder, server):
    data, config, rows = make_case(folder, server)
    data["information_sources"]["demand"] = {"type": "extension", "provider": "registered", "kind": "forecast",
                                               "quantity": "required_flow", "unit": "m3/s", "location": "external-control"}
    calls = []
    def provider(**kwargs):
        calls.append(kwargs["timestep"])
        return [{"issued_at": "2019-12-31T00:00:00Z", "available_at": "2019-12-31T01:00:00Z",
                 "valid_time": "2020-01-04T00:00:00Z", "value": 4}]
    provider.version = "synthetic-source-v1"
    settings = load_settings(save_settings(folder, data), information_providers={"registered": provider})
    run_settings(settings, allow_network=True, information_providers={"registered": provider})
    verify_run(folder / "run")
    assert calls == [0, 1, 2]
    assert len(server.requests) == 3
    assert [r["user"]["info"]["fields"]["target"]["value"] for r in server.requests] == [4, 4, 4]
    assert calls == [0, 1, 2], "Verification must not reacquire extension data"
    write_json(folder / "fixture-http-requests.json", {"inference": False, "requests": server.requests})


def test_openai_compatible_http_and_knowledge_in_prompt(folder, server):
    data, config, rows = make_case(folder, server, provider="openai_compatible")
    (folder / "knowledge.md").write_text("Synthetic operating knowledge, not approved operating policy.", encoding="utf-8")
    data["agents"]["operator-0"]["knowledge"] = {"test-knowledge": "knowledge.md"}
    run_cli_case(folder, server, data)
    assert all(r["path"].endswith("/chat/completions") for r in server.requests)
    assert all("Synthetic operating knowledge" in r["user"]["knowledge"]["test-knowledge"] for r in server.requests)


@pytest.mark.parametrize("layout,count,days", [("serial", 3, 3), ("confluence", 3, 3), ("delay", 3, 3), ("passive", 3, 31), ("many", 10, 3)])
def test_network_count_topology_and_agent_isolation(folder, server, layout, count, days):
    data, config, rows = make_case(folder, server, count=count, days=days, branch=layout != "serial", passive_last=layout == "passive")
    if layout == "delay":
        for edge in config["connections"]:
            edge["unit_hydrograph"] = [0, 1]
        write_json(folder / "case.json", {"schema_version": "llm-reservoir-network-case.v1", "data_kind": "synthetic_fixture", "network": config, "inflow_records": rows})
    for i, (agent_id, agent) in enumerate(data["agents"].items()):
        name = f"demand-{i}"
        data["information_sources"][name] = {"type": "static", "quantity": "required_flow", "unit": "m3/s", "location": f"user-{i}", "value": i + 2}
        data["information_profiles"][name] = {"fields": {"target": {"source": name}}}
        agent["information"] = name
    physical = run_cli_case(folder, server, data)
    for r in server.requests:
        i = int(r["user"]["agent"].split("-")[-1])
        assert r["user"]["info"]["fields"]["target"]["value"] == i + 2
    assert len(physical) == count * days
    if layout == "passive":
        assert len(server.requests) == 2 * 31
        assert {r["user"]["agent"] for r in server.requests} == {"operator-0", "operator-1"}
    flows = list(csv.DictReader((folder / "run/network_flows.csv").open(encoding="utf-8")))
    outlet = [float(r["routed_flow_cms"]) for r in flows if r["node"] == "Outlet"]
    if layout == "delay":
        assert outlet == pytest.approx([0, 9, 9])
    elif layout == "confluence":
        assert outlet == pytest.approx([9, 9, 9])
    elif layout == "serial":
        assert outlet == pytest.approx([4, 4, 4])


def test_clipping_spill_and_executed_history_not_requested_history(folder, server):
    data, config, rows = make_case(folder, server)
    p = config["reservoirs"]["R1"]["physical"]
    p.update(capacity_m3=100000, initial_storage_m3=90000, maximum_release_cms=3)
    write_json(folder / "case.json", {"schema_version": "llm-reservoir-network-case.v1", "data_kind": "synthetic_fixture", "network": config, "inflow_records": rows})
    data["information_sources"]["demand"]["value"] = 20
    data["information_sources"]["release"] = {"type": "simulation", "quantity": "release", "unit": "m3/s", "location": "R1"}
    data["information_profiles"]["selected"]["fields"]["executed"] = {"source": "release", "required": False, "history": 3}
    physical = run_cli_case(folder, server, data)
    assert [r["action"]["release_cms"] for r in physical] == [20, 20, 20]
    assert [r["transition"]["controlled_release_cms"] for r in physical] == [3, 3, 3]
    assert all(r["transition"]["spill_cms"] > 0 for r in physical)
    for r in physical:
        t = r["transition"]
        assert t["total_outflow_cms"] == pytest.approx(t["controlled_release_cms"] + t["spill_cms"])
    assert server.requests[1]["user"]["info"]["fields"]["executed"]["value"] == 3
    assert server.requests[1]["user"]["previous"]["transition"]["controlled_release_cms"] == 3
    assert json.loads((folder / "run/summary.json").read_text())["summary"]["audit_counts"] == {"FAIL": 3}


@pytest.mark.parametrize("fault", ["invalid_json", "duplicate_key", "negative", "incomplete", "missing_completion"])
def test_bad_reply_stops_before_physics_without_retry(folder, server, fault):
    data, config, rows = make_case(folder, server)
    server.fault = fault
    path = save_settings(folder, data)
    cli(folder, "check", path)
    cli(folder, "run", path, network_allowed=True, expect_success=False)
    assert len(server.requests) == 1
    assert (folder / "run/physics.jsonl").read_bytes() == b""
    failure = json.loads((folder / "run/summary.json").read_text())
    assert failure["status"] == "FAILED" and failure["error"]
    assert failure["summary"]["automatic_retry"] is False
    events = records(folder / "run/backend_events.jsonl")
    stopped = [event for event in events if event["event_type"] == "decision_failed"]
    assert len(stopped) == 1
    ref = stopped[0]["raw_backend_ref"]
    payload = (folder / "run" / ref["path"]).read_bytes()
    assert sha256(payload).hexdigest() == ref["sha256"]
    evidence = json.loads(payload)["audit_execution"]["available_backend_evidence"]
    assert evidence["freshness"] == "unverified"
    assert evidence["latest_trace"]["raw_reply"] is not None
    write_json(folder / "fixture-http-requests.json", {"inference": False, "requests": server.requests})
    write_json(folder / "expected-stop.json", {"expected": True, "http_requests": 1, "physical_transitions": 0, "inference": False})


@pytest.mark.parametrize("condition", ["required_missing", "required_stale", "first_downstream_required", "optional_missing"])
def test_availability_guards_at_actual_entrypoint(folder, server, condition):
    data, config, rows = make_case(folder, server)
    field = data["information_profiles"]["selected"]["fields"]["target"]
    if condition == "first_downstream_required":
        data["information_sources"]["demand"] = {"type": "simulation", "quantity": "flow", "unit": "m3/s", "location": "Outlet"}
    else:
        stale = condition == "required_stale"
        stamp = "2019-12-01T00:00:00Z" if stale else "2020-01-03T00:00:00Z"
        (folder / "source.csv").write_text(f"valid_time,available_at,value\n{stamp},{stamp},4\n", encoding="utf-8")
        data["information_sources"]["demand"] = {"type": "csv", "kind": "observation", "path": "source.csv", "quantity": "required_flow", "unit": "m3/s", "location": "external"}
        if stale:
            field["max_age_seconds"] = 86400
    if condition == "optional_missing":
        field["required"] = False
        run_cli_case(folder, server, data)
        assert server.requests[0]["user"]["info"]["fields"]["target"]["status"] == "MISSING"
    else:
        path = save_settings(folder, data)
        cli(folder, "check", path)
        cli(folder, "run", path, network_allowed=True, expect_success=False)
        assert server.requests == []
        assert (folder / "run/physics.jsonl").read_bytes() == b""


def test_changed_csv_after_api_check_stops_before_http(folder, server):
    data, config, rows = make_case(folder, server)
    (folder / "source.csv").write_text("valid_time,available_at,value\n2019-12-31T00:00:00Z,2019-12-31T00:00:00Z,4\n", encoding="utf-8")
    data["information_sources"]["demand"] = {"type": "csv", "kind": "observation", "path": "source.csv", "quantity": "required_flow", "unit": "m3/s", "location": "external"}
    settings = load_settings(save_settings(folder, data))
    (folder / "source.csv").write_text((folder / "source.csv").read_text().replace(",4\n", ",5\n"), encoding="utf-8")
    with pytest.raises(ValueError, match="changed after"):
        run_settings(settings, allow_network=True)
    assert server.requests == [] and not (folder / "run").exists()


@pytest.mark.parametrize("purpose", ["flood_control", "other"])
def test_rule_benchmark_cli_through_same_physics(folder, server, purpose):
    data, config, rows = make_case(folder, server)
    history = folder / "synthetic_reference_2019.csv"
    with history.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "reservoir", "inflow"])
        for i in range(365):
            writer.writerow([(date(2019, 1, 1) + timedelta(days=i)).isoformat(), "reservoir_1", 10])
    source = {"path": history.name, "sha256": sha256(history.read_bytes()).hexdigest(),
              "date_column": "date", "flow_column": "inflow", "flow_to_cms": 1,
              "reservoir_column": "reservoir", "reservoir_value": "reservoir_1"}
    write_json(folder / "statistics.json", {"schema_version": "reservoir-benchmark-statistics.v1",
        "reservoir_id": "reservoir_1", "reference_start": "2019-01-01", "reference_end": "2019-12-31",
        "source": source, "mean_inflow_cms": 10, "monthly_mean_inflow_cms": {str(i): 10 for i in range(1, 13)},
        "reference_day_count": 365})
    for key in ("models", "information_sources", "information_profiles", "outcome_checks"):
        data.pop(key)
    data["max_calls"] = 0
    data["agents"] = {"rule": {"reservoir": "R1", "mode": "offline", "strategy": "benchmark",
                                   "benchmark": {"statistics": "statistics.json", "purpose": purpose}, "auditors": ["bounds"]}}
    settings = save_settings(folder, data)
    cli(folder, "check", settings)
    cli(folder, "run", settings)
    cli(folder, "verify", folder / "run")
    assert server.requests == []
    verified = verify_run(folder / "run", require_offline=True)
    assert verified["days"] == 3 and verified["max_system_balance_residual_m3"] < 1e-6
    assert len(records(folder / "run/physics.jsonl")) == 3
    write_json(folder / "path-acceptance.json", {"entry": "formal CLI benchmark", "verification": verified})


def test_selected_information_changes_actual_water_trajectory(folder, server):
    end_storage = []
    inflows = []
    for target in (4, 6):
        destination = folder / f"target-{target}"
        destination.mkdir()
        data, config, rows = make_case(destination, server)
        data["information_sources"]["demand"]["value"] = target
        physical = run_cli_case(destination, server, data)
        assert [p["transition"]["controlled_release_cms"] for p in physical] == [target] * 3
        end_storage.append(physical[-1]["transition"]["storage_end_m3"])
        inflows.append([p["observation"]["inflow_cms"] for p in physical])
        server.requests.clear()
    assert inflows[0] == inflows[1] == [10] * 3
    assert end_storage[1] - end_storage[0] == pytest.approx(-2 * 3 * 86400)
    write_json(folder / "information-effect.json", {"inference": False, "fixed_inflow_cms": inflows[0],
                                                     "targets_cms": [4, 6], "storage_end_m3": end_storage,
                                                     "storage_difference_m3": end_storage[1] - end_storage[0]})
