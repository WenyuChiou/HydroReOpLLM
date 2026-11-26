"""Validate the tutorial notebook structure, embedded PNGs, and end-to-end execution."""

import base64
import io
import json
from pathlib import Path
import re

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pytest

from llm_reservoir_agent import workflow
from tests.reservoir_fixtures import walter_study_reply


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "tutorials" / "fe_walter.ipynb"
ATTACHMENT_RE = re.compile(r"!\[[^\]]*\]\(attachment:([^)\s]+)\)")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_ATTACHMENTS = {
    "framework.png",
    "fe-walter-study-area.png",
    "simulation-stages.png",
    "results-outputs-map.png",
    "hybrid-cascade.png",
}


EXPECTED_OUTPUT_CELLS = {
    "preview-summary",
    "preview-figure",
    "baseline-results",
    "baseline-figure",
    "check-configurations",
    "preview-day1-prompts",
    "hybrid-config-preview",
    "compare-llm-runs",
}
EXPECTED_PLOT_CELLS = {"preview-figure", "baseline-figure"}
PERSONAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:[/\\]{1,2}users[/\\]|/users/|appdata|local[/\\]{1,2}temp)")


def _decode_png_payload(encoded: str | list[str]) -> None:
    if isinstance(encoded, list):
        encoded = "".join(encoded)
    raw = base64.b64decode(encoded, validate=True)
    assert raw.startswith(PNG_SIGNATURE)
    decoded = mpimg.imread(io.BytesIO(raw), format="png")
    assert decoded.ndim >= 2
    assert decoded.shape[0] > 0 and decoded.shape[1] > 0


def test_walter_notebook_structure_and_png_attachments():
    assert NOTEBOOK.stat().st_size <= 1_500_000
    raw_bytes = NOTEBOOK.read_bytes()
    assert b"\r" not in raw_bytes, "notebook must use LF line endings"
    notebook_text = raw_bytes.decode("utf-8")
    assert not PERSONAL_PATH_RE.search(notebook_text), "personal or temp path leaked into saved notebook"

    notebook = json.loads(notebook_text)
    assert notebook["nbformat"] == 4
    assert notebook["nbformat_minor"] >= 5

    found_attachments: set[str] = set()
    seen_output_cells: set[str] = set()
    seen_plot_cells: set[str] = set()

    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            cell_id = cell.get("id")
            assert isinstance(cell["execution_count"], int) and cell["execution_count"] >= 1
            outputs = cell["outputs"]
            assert all(out.get("output_type") != "error" for out in outputs), f"error output in cell {cell_id}"
            if cell_id in EXPECTED_OUTPUT_CELLS:
                assert outputs, f"expected saved outputs in cell {cell_id}"
                seen_output_cells.add(cell_id)
            if cell_id in EXPECTED_PLOT_CELLS:
                png_outputs = [
                    out["data"]["image/png"]
                    for out in outputs
                    if "image/png" in out.get("data", {})
                ]
                assert png_outputs, f"expected image/png output in plot cell {cell_id}"
                for png_payload in png_outputs:
                    _decode_png_payload(png_payload)
                seen_plot_cells.add(cell_id)
            continue
        if cell["cell_type"] != "markdown":
            continue

        markdown = "".join(cell["source"])
        referenced = ATTACHMENT_RE.findall(markdown)
        attachments = cell.get("attachments", {})
        assert set(referenced) == set(attachments), f"mismatched attachments in cell {cell.get('id')}"

        for name in referenced:
            payload = attachments[name]
            assert "image/png" in payload
            _decode_png_payload(payload["image/png"])
            found_attachments.add(name)

    assert seen_output_cells == EXPECTED_OUTPUT_CELLS
    assert seen_plot_cells == EXPECTED_PLOT_CELLS
    assert EXPECTED_ATTACHMENTS.issubset(found_attachments)


@pytest.mark.parametrize("directory, enable_llm", [(ROOT, False), (ROOT / "tutorials", True)])
def test_walter_notebook_runs_and_plots_verified_results(tmp_path, monkeypatch, directory, enable_llm):
    cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    code_cells = [cell for cell in cells if cell["cell_type"] == "code"]
    assert len(code_cells) == 10

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
        for cell in code_cells:
            if cell["id"] == "compare-llm-runs":
                assert namespace["RUN_LLM"] is False
                assert namespace["LLM_START_DATE"] == "2021-01-01"
                assert namespace["LLM_END_DATE"] == "2021-12-31"
                assert namespace["LLM_SEED"] == 3
                assert requests == []
                namespace["RUN_LLM"] = enable_llm
                namespace["verify_study_model"] = lambda port: None
            exec(compile("".join(cell["source"]), f"{NOTEBOOK}:{cell['id']}", "exec"), namespace)

        baseline = namespace["baseline"]
        assert baseline["verification"]["status"] == "PASS"
        assert baseline["verification"]["days"] == 365
        assert baseline["verification"]["observed_network_calls"] == 0
        assert baseline["output"].is_relative_to(tmp_path)
        assert (baseline["output"] / "reservoir_trajectory.csv").is_file()
        assert len(baseline["trajectory"]) == 365

        preview = namespace["reference_runs"]
        preview_fig = namespace["preview_figure"]
        assert len(preview_fig.axes[0].lines) == 5
        assert len(preview_fig.axes[1].lines) == 4
        assert preview_fig.axes[0].get_ylabel() == "Water elevation (ft)"
        assert preview_fig.axes[1].get_ylabel() == "Water release (ft³/s)"
        expected_baseline_lines = 4 if (baseline["trajectory"]["spill_cms"] > 0).any() else 3
        assert len(namespace["baseline_figure"].axes[0].lines) == expected_baseline_lines
        assert len(namespace["baseline_figure"].axes[1].lines) == 1
        assert list(preview["Rule-based"]["trajectory"]["storage_end_m3"]) == pytest.approx(
            baseline["trajectory"]["storage_end_m3"].to_list()
        )
        assert all(len(run["trajectory"]) == 365 for run in preview.values())
        assert {name: calls for name, (_, calls) in namespace["reference_cases"].items()} == {
            "Rule-based": 0,
            "Without operational knowledge": 365,
            "With operational knowledge": 365,
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
        assert namespace["comparison"][without]["max_calls"] == 14
        assert namespace["comparison"][with_knowledge]["live_ready"] is True

        multi_llm_report = namespace["multi_llm_report"]
        assert multi_llm_report["planned_llm_calls"] == 10
        assert multi_llm_report["network_calls"] == 0
        assert multi_llm_report["agent_types"] == {
            "upper_operator": "rule_based",
            "lower_operator": "llm",
        }
        assert multi_llm_report["agent_rules"] == {"upper_operator": "hanasaki"}
        preview_content = namespace["multi_llm_preview"]["messages"][0]["content"]
        assert "reservoir-action.v1" in preview_content
        assert "lower_operator" in preview_content

        hybrid_report = namespace["hybrid_report"]
        assert hybrid_report["agent_types"] == {
            "upper_operator": "rule_based",
            "lower_operator": "llm",
        }
        assert hybrid_report["agent_rules"] == {"upper_operator": "hanasaki"}
        assert hybrid_report["days"] == 10
        assert hybrid_report["planned_llm_calls"] == 10
        assert hybrid_report["network_calls"] == 0
        assert "lower_operator" in hybrid_report["prompt_previews"]

        multi_rule_verification = namespace["multi_rule_verification"]
        assert multi_rule_verification["status"] == "PASS"
        assert multi_rule_verification["days"] == 10
        assert multi_rule_verification["observed_network_calls"] == 0
        multi_rule_trajectory = namespace["multi_rule_trajectory"]
        assert set(multi_rule_trajectory["reservoir_id"]) == {"upper", "lower"}
        assert len(multi_rule_trajectory) == 20

        assert not (ROOT / "runs").exists()
        assert not (ROOT / "tutorials" / "runs").exists()

        if enable_llm:
            assert set(namespace["llm_runs"]) == {without, with_knowledge}
            assert len(requests) == 730
            assert all("R-MINNORM" not in messages[1]["content"] for messages in requests[:365])
            assert all("R-MINNORM" in messages[1]["content"] for messages in requests[365:])
            comp_fig = namespace["comparison_figure"]
            assert len(comp_fig.axes[0].lines) == 5
            assert len(comp_fig.axes[1].lines) == 4
            assert comp_fig.axes[0].get_ylabel() == "Water elevation (ft)"
            assert comp_fig.axes[1].get_ylabel() == "Water release (ft³/s)"
            for run in namespace["llm_runs"].values():
                assert run["verification"]["status"] == "PASS"
                assert run["verification"]["days"] == 365
                assert run["verification"]["observed_network_calls"] == 365
                assert run["output"].is_relative_to(tmp_path)
        else:
            assert namespace["llm_runs"] == {}
            assert requests == []
    finally:
        plt.close("all")
