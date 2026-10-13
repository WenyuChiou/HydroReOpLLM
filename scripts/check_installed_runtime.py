"""Verify an installed wheel with a two-day synthetic case and no model calls."""
from datetime import date, timedelta
import json
from pathlib import Path
import sysconfig
import tempfile
from unittest.mock import patch

import hydrocnhs
import yaml
from llm_reservoir_agent import workflow
from llm_reservoir_agent.verification import verify_run


def main():
    installed = Path(sysconfig.get_path("purelib")).resolve()
    for module in (hydrocnhs, workflow):
        if not Path(module.__file__).resolve().is_relative_to(installed):
            raise RuntimeError("wheel check imported a source checkout instead of the installed package")
    with tempfile.TemporaryDirectory(prefix="hydroopslm-wheel-") as directory:
        root = Path(directory)
        config = {
            "schema_version": "llm-reservoir-network.v1", "start_date": "2016-01-01",
            "outlet": "outlet", "reservoirs": {"dam": {
                "inflow_node": "headwater", "physical": {
                    "reservoir_id": "wheel_fixture", "capacity_m3": 2000000.0,
                    "dead_storage_m3": 0.0, "initial_storage_m3": 1000000.0,
                    "minimum_release_cms": 0.0, "maximum_release_cms": 10.0,
                    "dt_seconds": 86400.0,
                }}}, "connections": [
                    {"source": "dam", "target": "outlet", "unit_hydrograph": [1.0]}],
        }
        rows = [{"date": (date(2016, 1, 1) + timedelta(days=i)).isoformat(),
                 "local_inflow_cms": {"headwater": 2.0, "outlet": 0.0}} for i in range(2)]
        (root / "case.json").write_text(json.dumps({
            "schema_version": "llm-reservoir-network-case.v1", "data_kind": "synthetic_fixture",
            "network": config, "inflow_records": rows}), encoding="utf-8")
        (root / "prompt.txt").write_text("$observation", encoding="utf-8")
        settings = {"schema_version": "llm-reservoir-experiment.v1", "case": "case.json",
                    "run_id": "installed-wheel-check", "output": "output", "agents": {
                        "operator": {"reservoir": "dam", "mode": "offline",
                                     "release_cms": 1.0, "prompt": "prompt.txt"}}}
        path = root / "experiment.yaml"
        path.write_text(yaml.safe_dump(settings), encoding="utf-8")
        def forbidden(*args, **kwargs):
            raise AssertionError("installed-wheel check attempted network access")
        with patch("socket.socket.connect", side_effect=forbidden), patch("urllib.request.urlopen", side_effect=forbidden):
            plan = workflow.load_settings(path)
            workflow.run_settings(plan)
            proof = verify_run(root / "output", require_offline=True)
        if proof["days"] != 2 or proof["observed_network_calls"] != 0:
            raise RuntimeError("installed wheel failed bounded execution verification")
        print(json.dumps({"status": proof["status"], "days": proof["days"],
                          "model_calls": proof["observed_network_calls"],
                          "max_system_balance_residual_m3": proof["max_system_balance_residual_m3"],
                          "audit_counts": proof["audit_counts"], "operating_strategy_accepted": None,
                          "runtime_root": str(workflow.PROJECT_ROOT)}))


if __name__ == "__main__":
    main()
