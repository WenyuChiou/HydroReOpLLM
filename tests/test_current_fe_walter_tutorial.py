"""Current teaching entries retain approved inputs and replay saved annual evidence."""
import hashlib
import importlib.util
import json
import html
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import yaml

from llm_reservoir_agent.configuration import read_configuration
from llm_reservoir_agent.coupled import load_coupled_settings


ROOT = Path(__file__).resolve().parents[1]
COUPLED = ROOT / "examples/fe_walter/coupled"


@pytest.mark.parametrize("current,agent", [
    ("experiment.yaml", "agents.rule.yaml"),
    ("llm_available.yaml", "agents.llm_available.yaml"),
    ("llm_knowledge.yaml", "agents.llm_knowledge.yaml"),
])
def test_current_entry_resolves_to_approved_resources(current, agent):
    """Each canonical entry connects the same accepted shared resources."""
    with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
        path = COUPLED / current
        settings = load_coupled_settings(path)
        current_data, _ = read_configuration(path)
    entry = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert (path.parent / entry["case"]).resolve() == COUPLED / "reservoirs.json"
    for layer, name in (("agents", agent), ("hydrology", "hydrology.yaml"),
                        ("auditors", "auditors.yaml")):
        resource = COUPLED / name
        assert (path.parent / entry[layer]["file"]).resolve() == resource
        assert current_data["source_dependencies"][str(resource.resolve())] == hashlib.sha256(resource.read_bytes()).hexdigest()
    assert settings.report["days"] == 366
    assert settings.report["network_calls"] == 0
    assert settings.report["planned_llm_calls"] == (0 if current == "experiment.yaml" else 366)
    assert Path(settings.report["output"]) == ROOT / "runs" / settings.data["run_id"]
    if current != "experiment.yaml":
        assert entry["models"]["file"] == "models.yaml"


def test_current_notebook_sources_match_saved_annual_inflow_and_model():
    annual = COUPLED / "outputs/gemma4_2016_comparison"
    daily = pd.read_csv(annual / "daily.csv")
    rule = pd.read_csv(COUPLED / "outputs/2016/daily.csv")
    rule = rule.loc[rule["method"] == "rule"]
    for (_, _), group in daily.groupby(["engine", "method"]):
        assert len(group) == len(rule) == 366
        assert group["date"].tolist() == rule["date"].tolist()
        assert (abs(group["inflow_cms"].to_numpy() - rule["inflow_cms"].to_numpy()) < 1e-10).all()
        assert group["storage_start_m3"].iloc[0] == pytest.approx(2457848.279729185)
    profile = yaml.safe_load((COUPLED / "models.yaml").read_text(encoding="utf-8"))["reservoir_model"]
    summary = json.loads((annual / "summary.json").read_text(encoding="utf-8"))
    for field in ("temperature", "num_ctx", "think", "timeout_seconds", "max_attempts", "retry_delay_seconds", "seed"):
        assert profile[field] == summary["model_controls"][field]
    assert profile["max_tokens"] == summary["model_controls"]["num_predict"]
    for method in ("llm_available", "llm_knowledge"):
        pair = json.loads((annual / f"{method}_pair.json").read_text(encoding="utf-8"))
        record = pair["engines"]["framework"]
        request = record["provider_request"]
        serialized = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        assert hashlib.sha256(serialized.encode()).hexdigest() == record["provider_request_sha256"]
        assert request["model"] == profile["model"]
        assert request["options"]["temperature"] == profile["temperature"]
        assert request["options"]["num_predict"] == profile["max_tokens"]
        assert request["options"]["num_ctx"] == profile["num_ctx"]
        assert request["think"] == profile["think"]


def test_current_configs_publish_as_exact_local_downloads(tmp_path):
    spec = importlib.util.spec_from_file_location("current_tutorial_builder", ROOT / "docs/build.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.prepare(tmp_path, source_ref="main")
    for name in ("experiment.yaml", "llm_available.yaml", "llm_knowledge.yaml", "models.yaml"):
        relative = f"examples/fe_walter/coupled/{name}"
        expected = (ROOT / relative).read_bytes()
        assert (tmp_path / relative).read_bytes() == expected
        assert (tmp_path / "_config_downloads" / name).read_bytes() == expected


def test_manual_links_the_repository_tutorial_and_preserves_download(tmp_path):
    """The manual stays concise; the complete lesson lives in the repository."""
    spec = importlib.util.spec_from_file_location("notebook_docs_builder", ROOT / "docs/build.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.prepare(tmp_path, source_ref="main")
    assert (tmp_path / "_notebook_downloads/main.ipynb").read_bytes() == (ROOT / "tutorials/main.ipynb").read_bytes()
    assert "url=main.html" in (tmp_path / "tutorials/fe_walter.md").read_text(encoding="utf-8")
    text = (tmp_path / "tutorials/main.md").read_text(encoding="utf-8")
    assert "https://github.com/WenyuChiou/HydroReOpLLM/tree/main/tutorials" in text
    assert "https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/main.ipynb" in text
    assert not (tmp_path / "tutorials/main.ipynb").exists()
    assert "show_file(" not in text
    assert len(text.splitlines()) < 40


def test_notebook_displays_the_complete_current_settings():
    """Displayed files must match their current bytes, including aligned comments."""
    from tutorials.build_notebooks import main_cells
    notebook = json.loads((ROOT / "tutorials/main.ipynb").read_text(encoding="utf-8"))
    assert [c["source"] for c in notebook["cells"]] == [c["source"] for c in main_cells()]
    outputs = "\n".join(
        "".join(output.get("data", {}).get("text/html", []))
        for cell in notebook["cells"] for output in cell.get("outputs", [])
    )
    for path in [*COUPLED.glob("*.yaml"), COUPLED / "reservoirs.json",
                 * (ROOT / "examples/fe_walter/prompts").glob("*.txt"),
                 ROOT / "examples/fe_walter/knowledge/operating_rules.md",
                 ROOT / "examples/fe_walter/seasonal_pool_criteria.json"]:
        assert html.escape(path.read_text(encoding="utf-8")) in outputs, path
    assert "366" in outputs


def test_selected_notebook_build_preserves_exports_and_other_notebooks(tmp_path, monkeypatch):
    """Updating lesson text must not regenerate accepted scientific artifacts."""
    from tutorials import build_notebooks as builder
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "TUTORIALS", tmp_path)
    monkeypatch.setattr(builder, "_prepare_current_outputs", lambda: pytest.fail("figure refresh forbidden"))
    advanced = tmp_path / "advanced.ipynb"
    advanced.write_bytes(b"accepted advanced notebook")
    reports = builder.build(execute=False, notebook="main.ipynb")
    assert len(reports) == 1
    assert advanced.read_bytes() == b"accepted advanced notebook"
    assert json.loads((tmp_path / "main.ipynb").read_text(encoding="utf-8"))["cells"]
