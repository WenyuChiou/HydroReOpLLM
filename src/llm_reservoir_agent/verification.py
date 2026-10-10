"""Independent saved-file acceptance for a completed reservoir-network run."""
from collections import Counter
from collections.abc import Mapping
import csv
import hashlib
import json
import math
from pathlib import Path

from .case import inside, read_json
from .audit import normalize_audit
from .contracts import ReservoirObservation, finite_nonnegative, parse_action
from .network import validate_inflows
from .passive import PassiveOutlet
from .physics import PhysicalConfig, apply_transition


_STREAMS = ("decisions", "physics", "audit", "backend_events")
_OUTPUTS = {
    "experiment.json", "reservoir_trajectory.csv", "network_flows.csv",
    "network_balance.csv", "reach_volume_trace.json",
}
_AUDIT_STATUSES = {"PASS", "WARN", "FAIL", "UNKNOWN"}


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _close(a, b, message, *, tolerance=1e-6):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc
    _check(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tolerance, message)


def _volume_tolerance(*values):
    """Match the physical kernels' absolute-plus-scale volume tolerance."""
    return 1e-6 + 1e-12 * max(1.0, *(abs(float(value)) for value in values))


def _decision_id(run_id, reservoir_id, timestep, timestamp):
    data = json.dumps(
        [run_id, reservoir_id, timestep, timestamp], ensure_ascii=False,
        allow_nan=False, sort_keys=True, separators=(",", ":"),
    ) + "\n"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return reader.fieldnames, rows


def _event_key(event, *, result, ids, days, expected_type=None):
    _check(event.get("schema_version") == result["schema_version"], "trace schema mismatch")
    _check(event.get("run_id") == result["run_id"], "trace run mismatch")
    reservoir_id, timestep = event.get("reservoir_id"), event.get("timestep")
    _check(reservoir_id in ids, "unexpected trace reservoir identity")
    _check(isinstance(timestep, int) and not isinstance(timestep, bool) and 0 <= timestep < len(days),
           "unexpected trace timestep")
    _check(event.get("timestamp") == days[timestep], "trace date mismatch")
    expected_id = _decision_id(result["run_id"], reservoir_id, timestep, days[timestep])
    _check(event.get("decision_id") == expected_id, "decision ID does not match trace scope")
    if expected_type is not None:
        _check(event.get("event_type") == expected_type, "unexpected trace event type")
    return reservoir_id, timestep


def verify_run(output, *, require_offline=False):
    """Verify hashes, durable causality, exported physics and routed volumes.

    Existing audit FAIL/WARN/UNKNOWN values remain unchanged. Passing these file
    checks does not accept an operating strategy that was not separately audited.
    """
    output = Path(output).resolve()
    result = read_json(output / "summary.json")
    _check(read_json(output / "index.json") == result, "summary/index mismatch")
    _check(result.get("status") == "COMPLETED" and result.get("error") is None, "run is not completed")
    _check(result.get("schema_version") == "reservoir-trace.v1", "unsupported trace schema")
    experiment = read_json(output / "experiment.json")
    _check(experiment.get("run_id") == result["run_id"], "experiment run mismatch")
    config, rows = experiment["network"], experiment["inflow_records"]
    topology, local = validate_inflows(config, rows)
    days = [row["date"] for row in rows]
    n, nr = len(days), len(config["reservoirs"])
    summary = result["summary"]

    _check(set(summary.get("output_files", {})) == _OUTPUTS, "output file coverage mismatch")
    for name, digest in summary["output_files"].items():
        _check(hashlib.sha256(inside(output, name).read_bytes()).hexdigest() == digest,
               "output hash mismatch: " + name)

    _check(set(result.get("streams", {})) == set(_STREAMS), "trace stream coverage mismatch")
    streams = {}
    for name in _STREAMS:
        spec = result["streams"][name]
        _check(spec.get("path") == name + ".jsonl", "unexpected trace path: " + name)
        raw = inside(output, spec["path"]).read_bytes()
        _check(hashlib.sha256(raw).hexdigest() == spec.get("sha256"), "trace hash mismatch: " + name)
        _check(not raw or raw.endswith(b"\n"), "incomplete trace tail")
        events = [json.loads(line) for line in raw.splitlines()]
        _check(len(events) == spec.get("event_count") == spec.get("durable_event_count"),
               "trace count/durability mismatch: " + name)
        _check(spec.get("incomplete_tail") is False, "reported incomplete trace")
        streams[name] = events
    actual_counts = {name: len(streams[name]) for name in _STREAMS}
    _check(result.get("event_counts") == actual_counts, "event counts mismatch")
    _check(result.get("durable_event_counts") == actual_counts, "non-durable event counts")

    ids = {settings["physical"]["reservoir_id"]: name for name, settings in config["reservoirs"].items()}
    indexed = {}
    decision_order = []
    for stream, event_type in (("decisions", "decision"), ("physics", "physics"), ("audit", "audit")):
        _check(len(streams[stream]) == n * nr, "missing reservoir-day trace: " + stream)
        by_key = {}
        order = []
        for event in streams[stream]:
            key = _event_key(event, result=result, ids=ids, days=days, expected_type=event_type)
            _check(key not in by_key, "duplicate trace key: " + stream)
            by_key[key] = event
            order.append(key)
            for ref_name in ("raw_policy_ref", "original_payload_ref"):
                if ref_name in event:
                    ref = event[ref_name]
                    _check(isinstance(ref, Mapping) and set(ref) == {"path", "sha256"}, "invalid raw trace reference")
                    _check(hashlib.sha256(inside(output, ref["path"]).read_bytes()).hexdigest() == ref["sha256"],
                           "raw trace hash mismatch")
        for reservoir_id in ids:
            _check(sorted(t for rid, t in by_key if rid == reservoir_id) == list(range(n)),
                   "non-consecutive reservoir trace")
        if stream == "decisions":
            decision_order = order
        else:
            _check(order == decision_order, "trace stream sequence mismatch: " + stream)
        indexed[stream] = by_key

    backend = streams["backend_events"]
    _check(len(backend) == 3 * n * nr, "incomplete successful backend lifecycle")
    expected_backend = []
    backend_by_key = {key: [] for key in decision_order}
    for event in backend:
        key = _event_key(event, result=result, ids=ids, days=days)
        _check(key in backend_by_key, "backend event has no decision")
        backend_by_key[key].append(event)
    for key in decision_order:
        events = backend_by_key[key]
        _check([(event.get("event_type"), event.get("status")) for event in events] == [
            ("decision_started", "STARTED"), ("decision_returned", "RETURNED"),
            ("feedback_completed", "COMPLETED")], "invalid backend event sequence")
        decision = indexed["decisions"][key]
        _check(events[0].get("request_id") is None, "started event unexpectedly has a request identity")
        _check(all(event.get("decision_id") == decision["decision_id"] for event in events),
               "backend event decision mismatch")
        _check(events[1].get("request_id") == decision.get("request_id") == events[2].get("request_id"),
               "backend event request mismatch")
        expected_backend.extend(events)
    _check(expected_backend == backend, "backend lifecycle order mismatch")

    records = {name: [] for name in config["reservoirs"]}
    max_balance = 0.0
    for reservoir_id, name in ids.items():
        spec = config["reservoirs"][name]
        physical_config = spec["physical"]
        kernel_config = PhysicalConfig(**physical_config)
        previous = physical_config["initial_storage_m3"]
        passive = PassiveOutlet(physical_config, spec["passive_outlet"]) if spec.get("operation_mode") == "passive_outlet" else None
        for timestep in range(n):
            key = reservoir_id, timestep
            decision, physical, audit = [indexed[stream][key] for stream in ("decisions", "physics", "audit")]
            _check(decision["decision_id"] == physical["decision_id"] == audit["decision_id"], "uncorrelated trace IDs")
            _check(decision.get("request_id") == physical.get("request_id") == audit.get("request_id"), "uncorrelated request IDs")
            _check(decision.get("status") == "RECORDED" and physical.get("status") == "RECORDED", "unrecorded event")
            _check(audit.get("status") in _AUDIT_STATUSES, "invalid retained audit status")
            original = (read_json(inside(output, audit["original_payload_ref"]["path"]))
                        if "original_payload_ref" in audit else None)
            retained = normalize_audit(original)
            _check(audit.get("audit_schema_version") == retained["schema_version"], "retained audit schema mismatch")
            for field in ("status", "reasons", "warnings", "citations", "hits"):
                _check(audit.get(field) == retained[field], "retained audit payload mismatch: " + field)
            record = physical["record"]
            _check(record["observation"] == decision["observation"] and record["action"] == decision["action"],
                   "mutated decision/physics trace")
            transition = record["transition"]
            observation = record["observation"]
            _check(ReservoirObservation(**observation).to_dict() == observation, "noncanonical observation")
            _check(parse_action(record["action"]).to_dict() == record["action"], "noncanonical action")
            _check(observation.get("context", {}).get("reservoir_id") == reservoir_id and
                   observation.get("timestep") == timestep and
                   isinstance(observation.get("timestamp"), str) and
                   observation["timestamp"][:10] == days[timestep], "observation scope mismatch")
            _close(observation["state"]["storage_m3"], previous, "observation storage mismatch")
            state_fields = ("capacity_m3", "dead_storage_m3", "minimum_release_cms", "maximum_release_cms", "dt_seconds")
            _check(set(observation["state"]) == {"storage_m3", *state_fields}, "observation state field coverage mismatch")
            for field in state_fields:
                value = finite_nonnegative(observation["state"][field], "observation.state." + field)
                _close(value, physical_config[field], "observation configured state mismatch: " + field)
            upper = min(kernel_config.maximum_release_cms,
                        max(0.0, observation["inflow_cms"] + (previous - kernel_config.dead_storage_m3) / kernel_config.dt_seconds))
            _close(observation["release_upper_bound_cms"], upper, "observation release bound mismatch", tolerance=1e-9)
            for field in ("evaporation_m3", "seepage_m3"):
                _close(observation["context"][field], 0.0, "observation unsupported loss mismatch")
            if passive:
                release, _ = passive.solve(previous, observation["inflow_cms"])
                _close(record["action"]["release_cms"], release, "passive solver action mismatch", tolerance=1e-9)
            expected_transition = apply_transition(kernel_config, previous, observation["inflow_cms"],
                                                   record["action"]["release_cms"]).to_dict()
            _check(set(transition) == set(expected_transition), "physical transition field coverage mismatch")
            for field, value in expected_transition.items():
                if field == "adjustments":
                    _check(transition[field] == value, "physical adjustment mismatch")
                else:
                    tolerance = (_volume_tolerance(previous, value) if field.endswith("_m3") else 1e-9)
                    _close(transition[field], value, "configured physics mismatch: " + field, tolerance=tolerance)
            _close(transition["storage_start_m3"], previous, "storage continuity failed")
            _close(transition["inflow_cms"], record["observation"]["inflow_cms"], "transition inflow mismatch")
            _close(transition["target_release_cms"], record["action"]["release_cms"], "target release mismatch")
            _check(physical_config["dead_storage_m3"] <= transition["storage_end_m3"] <= physical_config["capacity_m3"],
                   "storage outside bounds")
            _close(transition["total_outflow_cms"], transition["controlled_release_cms"] + transition["spill_cms"],
                   "spill counted incorrectly", tolerance=1e-10)
            residual = math.fsum([previous, transition["inflow_cms"] * 86400,
                                  -transition["total_outflow_cms"] * 86400, -transition["storage_end_m3"]])
            reservoir_scale = (previous, transition["storage_end_m3"], transition["inflow_cms"] * 86400,
                               transition["total_outflow_cms"] * 86400)
            _close(residual, 0.0, "reservoir balance failed", tolerance=_volume_tolerance(*reservoir_scale))
            _close(transition["mass_balance_residual_m3"], residual, "reported reservoir balance mismatch")
            max_balance = max(max_balance, abs(residual))
            if passive:
                _close(transition["controlled_release_cms"], passive.rate(transition["storage_end_m3"]),
                       "passive rating/balance mismatch", tolerance=1e-9)
                _check(decision["provenance"].get("provider") == "physical", "passive node externally controlled")
            previous = transition["storage_end_m3"]
            records[name].append(record)

    trajectory_fields, trajectory = _csv(output / "reservoir_trajectory.csv")
    transition_fields = list(records[next(iter(records))][0]["transition"])
    _check(trajectory_fields[:2] == ["date", "reservoir_id"] and
           set(trajectory_fields[2:]) == set(transition_fields) and
           len(trajectory_fields[2:]) == len(transition_fields), "trajectory columns mismatch")
    trajectory_map = {}
    for row in trajectory:
        key = row["reservoir_id"], row["date"]
        _check(key not in trajectory_map, "duplicate trajectory identity")
        trajectory_map[key] = row
    expected_trajectory = [(records[name][t]["observation"]["timestamp"],
                            config["reservoirs"][name]["physical"]["reservoir_id"],
                            records[name][t]["transition"])
                           for name in config["reservoirs"] for t in range(n)]
    _check(len(trajectory_map) == len(expected_trajectory), "trajectory row count mismatch")
    for day, reservoir_id, transition in expected_trajectory:
        _check((reservoir_id, day) in trajectory_map, "trajectory identity mismatch")
        row = trajectory_map[reservoir_id, day]
        for field, expected in transition.items():
            if isinstance(expected, list):
                _check(row[field] == str(expected), "trajectory adjustment mismatch")
            else:
                _close(row[field], expected, "trajectory/physics mismatch: " + field, tolerance=1e-10)

    flow_fields, saved_flows = _csv(output / "network_flows.csv")
    _check(flow_fields == ["date", "node", "local_inflow_cms", "routed_flow_cms"], "flow columns mismatch")
    _check(len(saved_flows) == len(topology["nodes"]) * n, "flow row count mismatch")
    flow_map = {}
    for row in saved_flows:
        key = row["node"], row["date"]
        _check(key not in flow_map, "duplicate flow row")
        _check(row["node"] in topology["nodes"] and row["date"] in days, "unexpected flow identity")
        expected_local = local[row["node"]][days.index(row["date"])] if row["node"] in local else None
        _check((row["local_inflow_cms"] == "") if expected_local is None else True, "reservoir flow has local inflow")
        if expected_local is not None:
            _close(row["local_inflow_cms"], expected_local, "local inflow export mismatch", tolerance=1e-10)
        flow_map[key] = float(row["routed_flow_cms"])
    flows = {}
    max_routing = 0.0
    for node in topology["sequence"]:
        if node in records:
            expected = [record["transition"]["total_outflow_cms"] for record in records[node]]
            inlet = config["reservoirs"][node]["inflow_node"]
            for timestep, record in enumerate(records[node]):
                _close(record["observation"]["inflow_cms"], flows[inlet][timestep],
                       "wrong causal reservoir inflow", tolerance=1e-10)
        else:
            expected = list(local[node])
            for edge in topology["edges"]:
                if edge["target"] == node:
                    for departure, discharge in enumerate(flows[edge["source"]]):
                        for lag, weight in enumerate(edge["unit_hydrograph"]):
                            if departure + lag < n:
                                expected[departure + lag] += discharge * edge["fraction"] * weight
        flows[node] = expected
        for timestep, day in enumerate(days):
            observed = flow_map[node, day]
            max_routing = max(max_routing, abs(observed - expected[timestep]))
            _close(observed, expected[timestep], "routed output mismatch", tolerance=1e-10)

    reach_document = read_json(output / "reach_volume_trace.json")
    _check(reach_document.get("schema_version") == "reach-volume-trace.v1", "reach trace schema mismatch")
    reaches = reach_document.get("reaches")
    _check(isinstance(reaches, list) and len(reaches) == len(topology["edges"]), "reach trace edge coverage mismatch")
    stocks = [0.0] * n
    for saved, edge in zip(reaches, topology["edges"]):
        for field in ("source", "target", "fraction", "unit_hydrograph"):
            _check(saved.get(field) == edge[field], "reach trace edge mismatch")
        _close(saved.get("initial_in_transit_m3"), 0.0, "reach initial stock mismatch")
        daily = saved.get("daily")
        _check(isinstance(daily, list) and len(daily) == n, "reach trace timestep coverage mismatch")
        entered_total = arrived_total = 0.0
        for timestep, row in enumerate(daily):
            entered = flows[edge["source"]][timestep] * edge["fraction"] * 86400
            arrived = math.fsum(flows[edge["source"]][timestep-lag] * weight
                                for lag, weight in enumerate(edge["unit_hydrograph"]) if lag <= timestep)
            arrived *= edge["fraction"] * 86400
            entered_total += entered
            arrived_total += arrived
            stock = entered_total - arrived_total
            volume_tolerance = _volume_tolerance(entered_total, arrived_total, stock)
            _check(row.get("date") == days[timestep], "reach trace date mismatch")
            _close(row.get("entered_m3"), entered, "reach entered volume mismatch",
                   tolerance=_volume_tolerance(entered))
            _close(row.get("arrived_m3"), arrived, "reach arrived volume mismatch",
                   tolerance=_volume_tolerance(arrived))
            _close(row.get("in_transit_end_m3"), stock, "reach in-transit volume mismatch",
                   tolerance=volume_tolerance)
            stocks[timestep] += stock
        _close(saved.get("final_in_transit_m3"), daily[-1]["in_transit_end_m3"], "reach final stock mismatch",
               tolerance=_volume_tolerance(entered_total, arrived_total, daily[-1]["in_transit_end_m3"]))

    ledger_fields, ledger = _csv(output / "network_balance.csv")
    expected_ledger_fields = ["date", "local_input_m3", "outlet_outflow_m3", "reservoir_storage_change_m3",
                              "channel_storage_change_m3", "channel_storage_end_m3", "system_residual_m3"]
    _check(ledger_fields == expected_ledger_fields and len(ledger) == n, "network ledger coverage mismatch")
    max_system, previous_stock = 0.0, 0.0
    for timestep, row in enumerate(ledger):
        local_input = math.fsum(local[node][timestep] for node in local) * 86400
        outlet = flows[config["outlet"]][timestep] * 86400
        storage_change = math.fsum(series[timestep]["transition"]["storage_end_m3"] -
                                   series[timestep]["transition"]["storage_start_m3"] for series in records.values())
        channel_change = stocks[timestep] - previous_stock
        residual = math.fsum([local_input, -outlet, -storage_change, -channel_change])
        system_tolerance = _volume_tolerance(local_input, outlet, storage_change, channel_change,
                                             stocks[timestep], previous_stock)
        _check(row["date"] == days[timestep], "network ledger dates mismatch")
        for field, expected in (("local_input_m3", local_input), ("outlet_outflow_m3", outlet),
                                ("reservoir_storage_change_m3", storage_change),
                                ("channel_storage_change_m3", channel_change),
                                ("channel_storage_end_m3", stocks[timestep]),
                                ("system_residual_m3", residual)):
            _close(row[field], expected, "network ledger mismatch: " + field,
                   tolerance=system_tolerance if field.startswith("channel_storage") else 1e-6)
        _close(residual, 0.0, "system balance failed", tolerance=system_tolerance)
        max_system = max(max_system, abs(residual))
        previous_stock = stocks[timestep]

    counts = Counter(event["status"] for event in streams["audit"])
    _check(dict(counts) == summary.get("audit_counts"), "audit counts mismatch")
    _check(summary.get("days") == n and summary.get("reservoir_count") == nr, "summary dimensions mismatch")
    _check(summary.get("completed_reservoir_days") == dict.fromkeys(ids, n), "summary completion mismatch")
    _check(summary.get("final_storage_m3") == {name: series[-1]["transition"]["storage_end_m3"] for name, series in records.items()},
           "summary final storage mismatch")
    _close(summary.get("max_mass_balance_residual_m3"), max_balance, "summary reservoir balance mismatch")
    _close(summary.get("max_system_balance_residual_m3"), max_system, "summary system balance mismatch")
    _close(summary.get("final_channel_storage_m3"), stocks[-1], "summary channel stock mismatch")

    calls = summary.get("network_calls_by_reservoir")
    if require_offline:
        _check(isinstance(calls, Mapping) and set(calls) == set(config["reservoirs"]), "network-call coverage mismatch")
        _check(all(value == 0 for value in calls.values()) and summary.get("observed_network_calls") == 0,
               "nonzero or unknown provider calls")
        provenance = experiment.get("backend_provenance")
        _check(isinstance(provenance, Mapping) and set(provenance) == set(config["reservoirs"]),
               "backend provenance coverage mismatch")
        for metadata in provenance.values():
            _check(isinstance(metadata, Mapping) and
                   (metadata.get("provider") == "physical" or metadata.get("data_kind") == "synthetic_fixture"),
                   "unverified offline backend")

    return {
        "status": "PASS", "days": n, "reservoir_count": nr, "reservoir_days": n * nr,
        "date_start": days[0], "date_end": days[-1], "audit_counts": dict(counts),
        "max_reservoir_balance_residual_m3": max_balance,
        "max_system_balance_residual_m3": max_system,
        "max_routing_difference_cms": max_routing,
        "final_channel_storage_m3": stocks[-1],
        "observed_network_calls": summary["observed_network_calls"],
        "operating_strategy_accepted": None,
    }
