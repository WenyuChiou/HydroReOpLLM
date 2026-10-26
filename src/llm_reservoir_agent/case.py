"""Hash-pinned input loaders and explicitly offline response fixtures.

Role: Load a network case, pinned inflows and saved response fixtures.

Connections and data: workflow uses load_case to obtain configuration and ordered daily
rows. RecordedResponseBackend returns supplied actions for offline tests; it is not
evidence of a newly generated model response. Network validation remains in network.py.
"""
from collections.abc import Mapping
import csv
import hashlib
import json
from pathlib import Path

from .contracts import finite_nonnegative, parse_action
from .network import PROJECT_ROOT, validate_inflows

CFS_TO_CMS = 0.028316846592
HYDROCNHS_COMMIT = "fdd5097a3fcabb312c6c3739efc71da2d67c47da"


def inside(root, relative):
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("input path must remain inside the project")
    return path


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("non-finite JSON value: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique, parse_constant=invalid)


def load_case(path, *, project_root=PROJECT_ROOT):
    path = inside(project_root, path)
    case = read_json(path)
    if case.get("schema_version") == "llm-reservoir-network-case.v1":
        config = case["network"]
        from .time_axis import TimeAxis
        clock = TimeAxis.from_network(config)
        if "inflow_records" in case:
            if case.get("data_kind") != "synthetic_fixture" or "inflow_source" in case:
                raise ValueError("inline network case requires synthetic_fixture and exactly one inflow source")
            rows = case["inflow_records"]
        else:
            if case.get("data_kind") not in ("simulated_local_inflow", "observed_local_inflow", "synthetic_fixture"):
                raise ValueError("network case must declare its inflow data_kind")
            source_spec = case["inflow_source"]
            source_format = "daily-node-local-cms.v1" if clock.legacy_daily else "interval-node-local-cms.v1"
            if set(source_spec) != {"path", "sha256", "format"} or source_spec["format"] != source_format:
                raise ValueError("unsupported network inflow source")
            source = inside(project_root, path.parent / source_spec["path"])
            if hashlib.sha256(source.read_bytes()).hexdigest() != source_spec["sha256"]:
                raise ValueError("network inflow checksum mismatch")
            daily = {}
            with source.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames != [clock.key, "node", "local_inflow_cms"]:
                    raise ValueError(f"network inflow CSV requires {clock.key},node,local_inflow_cms columns")
                for row in reader:
                    flows = daily.setdefault(row[clock.key], {})
                    if row["node"] in flows:
                        raise ValueError("duplicate daily node inflow")
                    flows[row["node"]] = finite_nonnegative(float(row["local_inflow_cms"]), "local inflow")
            rows = [dict({clock.key: day}, local_inflow_cms=flows) for day, flows in daily.items()]
            config["source_files"] = {str(source): source_spec["sha256"]}
        knowledge = {}
        for identifier, spec in case.get("knowledge_packages", {}).items():
            if set(spec) != {"path", "sha256"}:
                raise ValueError("knowledge package requires path and sha256")
            source = inside(project_root, path.parent / spec["path"])
            if hashlib.sha256(source.read_bytes()).hexdigest() != spec["sha256"]:
                raise ValueError("knowledge package checksum mismatch: " + identifier)
            knowledge[identifier] = {"path": str(source), "sha256": spec["sha256"]}
        config["knowledge_packages"] = knowledge
        for settings in config["reservoirs"].values():
            if "passive_outlet_source" in settings:
                if "passive_outlet" in settings:
                    raise ValueError("only one passive rating source is permitted")
                spec = settings.pop("passive_outlet_source")
                if set(spec) != {"path", "sha256"}:
                    raise ValueError("passive rating source requires path and sha256")
                source = inside(project_root, path.parent / spec["path"])
                if hashlib.sha256(source.read_bytes()).hexdigest() != spec["sha256"]:
                    raise ValueError("passive outlet checksum mismatch")
                settings["passive_outlet"] = read_json(source)
                config.setdefault("source_files", {})[str(source)] = spec["sha256"]
        config.setdefault("source_files", {})[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        config["data_kind"] = case["data_kind"]
    elif case.get("schema_version") == "llm-reservoir-case.v1":
        if case.get("hydrocnhs_commit") != HYDROCNHS_COMMIT:
            raise ValueError("HydroCNHS baseline drift")
        legacy = case["reservoir_configuration"]
        name = legacy["agent_name"]
        agent = legacy["agent_config"]
        links = agent["Inputs"]["Links"]
        inlets = [node for node, value in links.items() if value == -1]
        if len(links) != 2 or len(inlets) != 1 or links.get(name) != 1:
            raise ValueError("single-reservoir links require one inflow and one agent output")
        inlet, outlet = inlets[0], legacy["downstream_outlet"]
        config = {"schema_version": "llm-reservoir-network.v1", "start_date": legacy["start_date"],
            "outlet": outlet, "reservoirs": {name: {"inflow_node": inlet, "physical": agent["Attributes"]["Physical"]}},
            "connections": [{"source": name, "target": outlet, "unit_hydrograph": [1.0]}],
            "assumptions": legacy.get("assumptions", {}), "data_kind": "accepted_short_inflow_fixture"}
        source = inside(project_root, case["inflow_csv"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != case["inflow_sha256"]:
            raise ValueError("inflow checksum mismatch")
        if case["inflow_unit"] not in ("cfs", "cms"):
            raise ValueError("inflow_unit must be cfs or cms")
        factor = CFS_TO_CMS if case["inflow_unit"] == "cfs" else 1.0
        with source.open(encoding="utf-8-sig", newline="") as handle:
            rows = [dict(date=row["date"], local_inflow_cms={inlet:
                         finite_nonnegative(float(row[case["inflow_column"]]), "inflow") * factor, outlet: 0.0})
                    for row in csv.DictReader(handle)]
        config["source_files"] = {str(path.relative_to(Path(project_root).resolve())):
                                  hashlib.sha256(path.read_bytes()).hexdigest(),
                                  case["inflow_csv"]: case["inflow_sha256"]}
    else:
        raise ValueError("unsupported reservoir case schema")
    validate_inflows(config, rows)
    return config, rows


class RecordedResponseBackend:
    policy_id = "offline_recorded_responses"
    network_calls = 0

    def __init__(self, records, *, data_kind, source_sha256):
        if data_kind not in ("recorded_llm_response", "synthetic_fixture"):
            raise ValueError("unsupported response data_kind")
        if not isinstance(records, list) or not records:
            raise ValueError("response records must be a non-empty list")
        self.records = []
        for record in records:
            original = json.loads(json.dumps(record, allow_nan=False))
            if set(record) == {"date", "response"}:
                response = record["response"]
                if not isinstance(response, Mapping) or set(response).difference({"release_cfs", "reasoning"}):
                    raise ValueError("unsupported legacy response fields")
                record = {"date": record["date"], "release_cfs": response["release_cfs"],
                          "rationale": response.get("reasoning")}
            if set(record).difference({"date", "release_cms", "release_cfs", "rationale", "audit"}):
                raise ValueError("unsupported recorded response fields")
            if ("release_cms" in record) == ("release_cfs" in record):
                raise ValueError("supply exactly one release unit")
            value = record.get("release_cms") if "release_cms" in record else (
                finite_nonnegative(record["release_cfs"], "release_cfs") * CFS_TO_CMS)
            self.records.append({"date": record["date"], "action": parse_action({"release_cms": value}).to_dict(),
                                 "audit": record.get("audit"), "raw": original})
        self.provenance = {"data_kind": data_kind, "response_source_sha256": source_sha256}
        self.latest_audit = None
        self.latest_trace = None
        self.feedback = []

    def decide(self, observation):
        record = self.records[observation["timestep"]]
        if record["date"] != observation["timestamp"][:10]:
            raise ValueError("response date differs from the observation")
        self.latest_audit = record["audit"]
        self.latest_trace = record["raw"]
        return record["action"]

    def record_transition(self, record):
        self.feedback.append(record)


def load_responses(path, config, rows, *, project_root=PROJECT_ROOT):
    path = inside(project_root, path)
    value = read_json(path)
    controlled = {name for name, spec in config["reservoirs"].items()
                  if spec.get("operation_mode", "controlled") == "controlled"}
    if value.get("schema_version") == "recorded-llm-responses.v1" and len(controlled) == 1:
        supplied = {next(iter(controlled)): value}
    elif value.get("schema_version") == "reservoir-network-responses.v1":
        supplied = value["reservoirs"]
    else:
        raise ValueError("unsupported recorded response file")
    if not isinstance(supplied, Mapping) or set(supplied) != controlled:
        raise ValueError("recorded responses must cover controlled reservoirs only")
    result = {}
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    for name, item in supplied.items():
        if (set(item) != {"schema_version", "data_kind", "records"}
                or item["schema_version"] != "recorded-llm-responses.v1"):
            raise ValueError("unsupported response record schema")
        backend = RecordedResponseBackend(item["records"], data_kind=item["data_kind"], source_sha256=source_sha)
        if [r["date"] for r in backend.records] != [r["date"] for r in rows]:
            raise ValueError("response dates must match all inflow dates")
        result[name] = backend
    return result
