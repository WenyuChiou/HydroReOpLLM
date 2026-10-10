"""Optional real Dam-loop contract fixture; uses assigned flow, no rainfall runoff."""

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

from .case import CFS_TO_CMS, PROJECT_ROOT


def build_dam_model(config, days, *, project_root=PROJECT_ROOT):
    start = date.fromisoformat(config["start_date"])
    end = start + timedelta(days=days - 1)
    route = lambda control: {
        "Inputs": {"FlowLength": 0.0, "InstreamControl": control},
        "Pars": {"GShape": None, "GScale": None, "Velo": None, "Diff": None},
    }
    return {
        "Path": {"WD": str(project_root), "Modules": str(project_root / "examples")},
        "WaterSystem": {
            "StartDate": start.strftime("%Y/%m/%d"), "EndDate": end.strftime("%Y/%m/%d"),
            "DataLength": days, "NumSubbasins": 2,
            "Outlets": ["FEW_INFLOW", "Downstream"], "NodeGroups": [],
            "RainfallRunoff": "Other", "Routing": "Lohmann",
            "ABM": {"Modules": ["fe_walter_abm.py"], "InstitDMClasses": {},
                    "DMClasses": [], "DamAPI": ["FEWalterDamAgent"],
                    "RiverDivAPI": [], "InsituAPI": [], "ConveyingAPI": [], "Institutions": {}},
        },
        "RainfallRunoff": {o: {"Inputs": {}, "Pars": {}} for o in ["FEW_INFLOW", "Downstream"]},
        "Routing": {"FEW_INFLOW": {"FEW_INFLOW": route(False)},
                    "Downstream": {"FEWalter": route(True), "Downstream": route(False)}},
        "ABM": {"FEWalterDamAgent": {"FEWalter": deepcopy(config["agent_config"])}},
    }


def run_hydrocnhs(config, rows, *, project_root=PROJECT_ROOT, policy=None):
    # Optional import occurs only when the user explicitly chooses this engine.
    import hydrocnhs
    import numpy as np

    core = json.loads((project_root / "environment/hydrocnhs-core.json").read_text(encoding="utf-8"))
    package_root = Path(hydrocnhs.__file__).resolve().parent
    for item in core["files"]:
        source = (package_root / item["path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(source).hexdigest() != item["normalized_sha256"]:
            raise ValueError(f"installed HydroCNHS core differs from the accepted pin: {item['path']}")

    model = hydrocnhs.Model(build_dam_model(config, len(rows), project_root=project_root), rn_gen=hydrocnhs.create_rn_gen(7))
    sequence = model.sys_parsed_data["SimSeq"]
    if sequence.index("FEW_INFLOW") >= sequence.index("FEWalter"):
        raise ValueError("HydroCNHS must route inflow before calling the Dam agent")
    model.agents["FEWalter"].verify_simulation_sequence(sequence)
    if policy is not None:
        if not callable(getattr(policy, "decide", None)):
            raise TypeError("policy must provide decide(observation)")
        model.agents["FEWalter"].policy = policy
        model.agents["FEWalter"].policy_id = getattr(policy, "policy_id", type(policy).__name__)
    inflow = np.array([float(row["simulated_inflow_cfs"]) * CFS_TO_CMS for row in rows])
    zeros = np.zeros(len(rows))
    result = model.run(
        temp={}, prec={}, pet={}, assigned_Q={"FEW_INFLOW": inflow, "Downstream": zeros},
        # The pinned core uses len(UH)-1 during convolution. A terminal zero
        # preserves the identity response without changing accepted core code.
        assigned_UH={pair: np.array([1.0, 0.0]) for pair in [
            ("FEW_INFLOW", "FEW_INFLOW"), ("FEWalter", "Downstream"), ("Downstream", "Downstream")
        ]}, disable=True,
    )
    agent = model.agents["FEWalter"]
    if not np.allclose(model.dc.Q_routed["FEW_INFLOW"], inflow, rtol=0, atol=1e-12):
        raise RuntimeError("assigned reservoir inflow changed during the Dam fixture")
    expected = [r["transition"]["total_outflow_cms"] for r in agent.operations_log]
    for outlet in ("FEWalter", "Downstream"):
        if not np.allclose(result[outlet], expected, rtol=0, atol=1e-12):
            raise RuntimeError(f"Dam outflow was lost or duplicated at {outlet}")
    return agent.operations_log, {
        "engine": "hydrocnhs_dam_fixture", "days": len(rows),
        "hydrology_recomputed": False,
        "provider_network_calls": 0 if policy is None else getattr(policy, "network_calls", None),
        "simulation_sequence": sequence,
        "downstream_routing": "identity unit hydrograph for contract test only",
        "verified_hydrocnhs_commit": core["hydrocnhs_commit"],
    }
