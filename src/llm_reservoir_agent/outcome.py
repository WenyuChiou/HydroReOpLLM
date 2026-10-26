"""Diagnostic control-point checks after routing, separate from request audits.

Role: Check completed routed flow at configured control points.

Connections and data: workflow validates bounds; experiment supplies completed records
and routed flows. Returns per-day diagnostic statuses with limit sources and decision
references. These are downstream outcome checks, distinct from response parsing and
requested-action audits.
"""
import hashlib
import json

from .audit import json_snapshot
from .contracts import finite_nonnegative


def validate_outcome_checks(checks, nodes, agents, profiles, sources=None):
    if not isinstance(checks, dict):
        raise ValueError("outcome_checks must be a mapping")
    allowed = {"node", "minimum_cms", "maximum_cms", "minimum_information", "maximum_information", "tolerance_cms"}
    for identifier, spec in checks.items():
        if not isinstance(identifier, str) or not identifier.strip() or not isinstance(spec, dict) or set(spec)-allowed:
            raise ValueError("invalid outcome check keys")
        if spec.get("node") not in nodes:
            raise ValueError("outcome check references an unknown control point")
        if not any(key in spec for key in allowed-{"node", "tolerance_cms"}):
            raise ValueError("outcome check requires at least one bound")
        for bound in ("minimum", "maximum"):
            scalar, selected = bound+"_cms", bound+"_information"
            if scalar in spec and selected in spec:
                raise ValueError("choose a scalar or information bound, not both")
            if scalar in spec:
                finite_nonnegative(spec[scalar], scalar)
            if selected in spec:
                ref = spec[selected]
                if not isinstance(ref, dict) or set(ref) != {"agent", "field"} or ref["agent"] not in agents:
                    raise ValueError("invalid outcome information reference")
                profile = agents[ref["agent"]].get("information")
                if profile not in profiles or ref["field"] not in profiles[profile]["fields"]:
                    raise ValueError("outcome bound requires a selected information field")
                field = profiles[profile]["fields"][ref["field"]]
                source = (sources or {})[field["source"]]
                if field.get("unit", source["unit"]) != "m3/s":
                    raise ValueError("control-point bound information must be in m3/s")
        finite_nonnegative(spec.get("tolerance_cms", 1e-9), "tolerance_cms")
        if "minimum_cms" in spec and "maximum_cms" in spec and spec["minimum_cms"] > spec["maximum_cms"]:
            raise ValueError("minimum outcome bound exceeds maximum")
    return json_snapshot(checks)


def evaluate_outcomes(checks, records, flows, rows, agents, run_id):
    result = []
    for timestep, row in enumerate(rows):
        for identifier, spec in checks.items():
            limits, sources, refs = {}, {}, []
            for bound in ("minimum", "maximum"):
                selected = spec.get(bound+"_information")
                value = spec.get(bound+"_cms")
                if selected:
                    agent = agents[selected["agent"]]
                    record = records[agent["reservoir"]][timestep]
                    info = record["observation"]["context"]["decision_information"]
                    field = info["fields"][selected["field"]]
                    sources[bound] = json_snapshot(field)
                    value = field.get("value") if field.get("status") == "AVAILABLE" else None
                    if value is not None:
                        if field["unit"] != "m3/s":
                            raise ValueError("control-point bound information must be in m3/s")
                        value = finite_nonnegative(value, "outcome bound")
                    payload = [run_id, record["observation"]["context"]["reservoir_id"], timestep,
                               record["observation"]["timestamp"]]
                    digest = hashlib.sha256((json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                                       separators=(",", ":"))+"\n").encode()).hexdigest()
                    refs.append({"agent": selected["agent"], "field": selected["field"], "decision_id": digest})
                limits[bound] = value
            flow = float(flows[spec["node"]][timestep])
            tolerance = spec.get("tolerance_cms", 1e-9)
            missing = any(bound+"_information" in spec and limits[bound] is None for bound in limits)
            if missing:
                status = "UNKNOWN"
            elif limits["minimum"] is not None and limits["maximum"] is not None and limits["minimum"] > limits["maximum"]:
                status = "FAIL"
            else:
                status = "FAIL" if ((limits["minimum"] is not None and flow < limits["minimum"]-tolerance) or
                                    (limits["maximum"] is not None and flow > limits["maximum"]+tolerance)) else "PASS"
            result.append(dict(schema_version="control-point-audit.v1", check_id=identifier,
                               timestep=timestep, timestamp=row["timestamp"] if "timestamp" in row else row["date"], node=spec["node"],
                               routed_flow_cms=flow, minimum_cms=limits["minimum"], maximum_cms=limits["maximum"],
                               status=status, limit_sources=sources, decision_refs=refs))
    return result
