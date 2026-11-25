"""Exercise the real notebook workflow with and without enabling Ollama."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from llm_reservoir_agent import workflow
from tests.reservoir_fixtures import walter_study_reply


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "tutorials" / "fe_walter.ipynb"


@pytest.mark.parametrize("directory, enable_llm", [(ROOT, False), (ROOT / "tutorials", True)])
def test_walter_notebook_runs_and_plots_verified_results(tmp_path, monkeypatch, directory, enable_llm):
    cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    requests = []
    run_original = workflow.run_settings

    def transport(_url, payload, _headers, _timeout):
        requests.append(payload["messages"])
        return {
            "model": "gemma4:12b",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(walter_study_reply(payload["format"]))},
        }

    def run_with_local_stub(settings, *, allow_network):
        return run_original(settings, allow_network=allow_network, transport=transport)

    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    monkeypatch.setattr(workflow, "run_settings", run_with_local_stub)
    plt.switch_backend("Agg")
    monkeypatch.setattr(plt, "show", lambda: None)
    monkeypatch.chdir(directory)
    namespace: dict = {}

    try:
        for cell in cells:
            if cell["cell_type"] != "code":
                continue
            if cell["id"] == "compare-llm-runs":
                assert namespace["RUN_LLM"] is False
                assert requests == []
                namespace["RUN_LLM"] = enable_llm
                namespace["verify_study_model"] = lambda port: None
            exec(compile("".join(cell["source"]), f"{NOTEBOOK}:{cell['id']}", "exec"), namespace)

        baseline = namespace["baseline"]
        assert baseline["verification"]["status"] == "PASS"
        assert baseline["verification"]["days"] == 7
        assert baseline["verification"]["observed_network_calls"] == 0
        assert baseline["output"].is_relative_to(tmp_path)
        assert (baseline["output"] / "reservoir_trajectory.csv").is_file()
        assert len(baseline["trajectory"]) == 7
        preview = namespace["reference_runs"]
        assert len(namespace["preview_figure"].axes[0].lines) == 4
        assert len(namespace["preview_figure"].axes[1].lines) == 3
        assert list(preview["Rule-based"]["trajectory"]["storage_end_m3"]) == pytest.approx(
            baseline["trajectory"]["storage_end_m3"].to_list()
        )
        assert all(len(run["trajectory"]) == 7 for run in preview.values())
        assert {name: requests for name, (_, requests) in namespace["reference_cases"].items()} == {
            "Rule-based": 0, "Without operational knowledge": 7, "With operational knowledge": 7,
        }

        without = "Without operational knowledge"
        with_knowledge = "With operational knowledge"
        reports = namespace["check_results"]
        assert set(reports) == {"Rule-based", without, with_knowledge}
        for name, checked in reports.items():
            assert (checked["start_date"], checked["end_date"]) == ("2021-01-01", "2021-01-07")
            assert checked["planned_llm_calls"] == (0 if name == "Rule-based" else 7)
            assert checked["network_calls"] == 0
        assert namespace["comparison"][without]["Operating guidance"] == ""
        assert namespace["comparison"][with_knowledge]["Operating guidance"] == "dkp.md"
        assert not (ROOT / "runs").exists()
        if enable_llm:
            assert set(namespace["llm_runs"]) == {without, with_knowledge}
            assert len(requests) == 14
            assert all("R-MINNORM" not in messages[1]["content"] for messages in requests[:7])
            assert all("R-MINNORM" in messages[1]["content"] for messages in requests[7:])
            assert len(namespace["comparison_figure"].axes[0].lines) == 4
            for run in namespace["llm_runs"].values():
                assert run["verification"]["status"] == "PASS"
                assert run["verification"]["days"] == 7
                assert run["output"].is_relative_to(tmp_path)
        else:
            assert namespace["llm_runs"] == {}
            assert requests == []
    finally:
        plt.close("all")
