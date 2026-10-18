"""Independent annual Anik oracle versus the production coupled entry.

Replay accepted upstream inflows and fixed replies, never a real LLM or a new
hydrological simulation. The approved target curve and optional daily prompt
context are supplied through the original policy entry. Its water balance is
independent of our physics.
"""
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import socket
import sys

import pandas as pd
import pytest
import yaml

from examples.fe_walter.extensions.anik_v3_7 import load_anik
from examples.fe_walter.extensions.seasonal_prompt_context import (
    SeasonalContextBackend, load_seasonal_prompt_context,
)
from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
from llm_reservoir_agent.verification import verify_run


ROOT = Path(__file__).resolve().parents[1]
COUPLED = ROOT / "examples/fe_walter/coupled"


def annual_inflow():
    """Use only the shared inlet column, never saved operating decisions."""
    data = pd.read_csv(COUPLED / "outputs/2016/daily.csv")
    data = data[data["method"] == "llm_available"]
    assert len(data) == data["date"].nunique() == 366
    return pd.Series(data["inflow_cms"].to_numpy(), index=pd.to_datetime(data["date"]))


def configure(tmp_path, method):
    source = COUPLED / f"{method}.yaml"
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    for key in ("hydrology", "agents", "models", "auditors"):
        data[key]["file"] = str((source.parent / data[key]["file"]).resolve())
    data["case"] = str((source.parent / data["case"]).resolve())
    data["extensions"] = {key: str((source.parent / value).resolve())
                          for key, value in data["extensions"].items()}
    data.update(output=str(tmp_path / "coupled"), run_id=f"offline-oracle-{method}")
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return load_coupled_settings(path, runtime_root=ROOT)


def oracle(method, replies, inflow):
    """Run the unmodified original engine, not our transition function."""
    anik = load_anik(ROOT)
    base = next(cfg for cfg in anik.RESERVOIRS if cfg.inflow_reservoir_key == "fe_walter")
    criteria = json.loads((ROOT / "examples/fe_walter/seasonal_pool_criteria.json").read_text())
    # A point on every day avoids the original curve's interpolation changing
    # the confirmed four-season targets. No physical parameter is substituted.
    curve = tuple((day.strftime("%m-%d"),
                   1300.0 if day < pd.Timestamp("2016-03-15")
                   or day >= pd.Timestamp("2016-10-15") else 1370.0)
                  for day in inflow.index)
    cfg = replace(base, operation_target_description=criteria["operation_target"],
                  seasonal_target_curve=curve)
    zero = sys.modules["zeroshot_llm_release"]
    info = zero.ReservoirBasicInfo(
        name=cfg.name, purpose=cfg.purpose.replace("_", " "), capacity_af=cfg.capacity_af,
        max_release_cfs=cfg.max_release_cfs, min_release_cfs=cfg.min_release_cfs,
        river=cfg.river, normal_pool_af=cfg.normal_pool_af, monthly_target_af=cfg.monthly_target_af,
        operation_target_description=cfg.operation_target_description, decision_interval="daily",
        public_profile=tuple(cfg.public_profile or ()), public_capacity_af=cfg.public_capacity_af,
        prompt_storage=False, show_availability_line=False, show_operation_target=True,
        target_storage_equivalents={e: anik.elevation_to_storage_af(cfg, e) for e in (1300.0, 1370.0)},
    )
    calls = []

    class FixedReplies:
        name = "fixed-offline-oracle"

        def decide(self, system, prompt, schema=None):
            calls.append((system, prompt, schema or zero.DECISION_SCHEMA))
            return deepcopy(replies[len(calls) - 1])

    # The original policy still builds its own prompt and runs native physics.
    # Its thin backend wrapper adds only the approved daily context, matching
    # the opt-in field now enabled in the two current agent files.
    context = load_seasonal_prompt_context(ROOT / "examples/fe_walter/seasonal_pool_criteria.json")
    common = dict(info=info, backend=SeasonalContextBackend(FixedReplies(), context),
                  audit_action="record", max_audit_revisions=0)
    if method == "llm_available":
        policy = zero.ZeroShotLLMPolicy(**common)
    else:
        policy = sys.modules["dkp_llm_release"].DKPLLMPolicy(
            **common, dkp_path=ROOT / "examples/fe_walter/knowledge/DKP_FEWalter_Dam_v1.2.md",
            include_missing_inputs=False)
    with redirect_stdout(io.StringIO()):
        result = anik.simulate(cfg, policy, inflow, inflow_change_threshold=-1.0,
                               timestep="daily", llm_failure_action="stop")
    assert len(calls) == 366
    return anik, result, calls


@pytest.mark.parametrize("method", ("llm_available", "llm_knowledge"))
def test_complete_annual_coupling_matches_independent_anik(tmp_path, monkeypatch, method):
    inflow = annual_inflow()
    settings = configure(tmp_path, method)
    replies = []
    for i, day in enumerate(inflow.index):
        # Deliberately excite storage depletion, capacity/spill and history.
        reply = dict(applicable_target_ft=1300.0, pool_position="at_target",
                     intended_storage_direction="hold", release_relation_to_inflow="equal_to_inflow",
                     reasoning="Synthetic engineering parity fixture, not model evidence.",
                     release_cfs=(50.0 if i < 330 else 10000.0))
        if method == "llm_knowledge":
            reply.update(operating_mode="pass_inflow", rules_applied=["R-RELEASE"])
        replies.append(reply)
    anik, expected, original_calls = oracle(method, replies, inflow)
    requests = []

    def no_network(*args, **kwargs):
        raise AssertionError("real HTTP and socket access are forbidden")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr("llm_reservoir_agent.configured_backend.http_json_transport", no_network)

    def replay_hydrology(weather, runtime_root):
        # Explicit replay boundary: all hydrological dates remain in the input;
        # accepted inlet values are provided for the operation year only.
        values = [float(inflow.get(pd.Timestamp(day), 0.0)) for day in weather["dates"]]
        return {"routed": {"__AGGREGATION_OUTLET__": values}}

    monkeypatch.setattr("llm_reservoir_agent.coupled.simulate_weather", replay_hydrology)

    def transport(url, payload, headers, timeout):
        requests.append(deepcopy(payload))
        return {"message": {"content": json.dumps(replies[len(requests) - 1])},
                "done": True, "done_reason": "stop"}

    _, actual = run_coupled(settings, allow_network=True, runtime_root=ROOT, transport=transport)
    assert len(requests) == 366
    operation = Path(settings.report["output"]) / "operation"
    verify_run(operation)
    records = [json.loads(line) for line in (operation / "physics.jsonl").read_text().splitlines()]
    assert len(records) == 366
    # Compare every actual provider request, including next-day history and
    # seasonal-boundary retrieval; equal synthetic replies alone prove nothing.
    for i, (request, original, record) in enumerate(zip(requests, original_calls, records)):
        day = str(inflow.index[i].date())
        assert request["messages"] == [{"role": "system", "content": original[0]},
                                        {"role": "user", "content": original[1]}], day
        assert request["format"] == original[2], day
        row = expected.iloc[i]
        transition = record["record"]["transition"]
        assert record["record"]["observation"]["inflow_cms"] == pytest.approx(
            row["inflow_cfs"] * anik.CFS_TO_CMS, abs=1e-10), day
        assert record["record"]["action"]["release_cms"] == pytest.approx(
            row["decision_release_cfs"] * anik.CFS_TO_CMS, abs=1e-10), day
        for key, value, tolerance in (
            ("controlled_release_cms", row["controlled_release_cfs"] * anik.CFS_TO_CMS, 1e-8),
            ("spill_cms", row["spill_cfs"] * anik.CFS_TO_CMS, 1e-8),
            ("storage_end_m3", row["storage_end_cf"] * anik.M3_PER_CF, 1e-5),
        ):
            assert transition[key] == pytest.approx(value, rel=1e-11, abs=tolerance), (day, key)
    # The teaching case declares identity downstream routing. Compare its outlet
    # directly with the independent original total outflow, not our own solver.
    flows = pd.read_csv(operation / "network_flows.csv")
    outlet = flows[flows["node"] == "Downstream"]
    assert list(outlet["date"]) == [str(day.date()) for day in inflow.index]
    assert outlet["routed_flow_cms"].to_numpy() == pytest.approx(
        expected["release_cfs"].to_numpy() * anik.CFS_TO_CMS, rel=1e-11, abs=1e-8)
    assert expected["spill_cfs"].max() > 0
    assert (expected["controlled_release_cfs"] < expected["decision_release_cfs"] - 0.1).any()
    assert actual["summary"]["max_mass_balance_residual_m3"] < 1e-5
