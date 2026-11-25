"""Execute the tutorial notebook cells end-to-end without leaving artifacts in the repo."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_walter_notebook_checks_both_cases_without_inference(monkeypatch):
    notebook_path = ROOT / "tutorials" / "fe_walter.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert len(code_cells) == 4

    monkeypatch.chdir(ROOT)
    namespace: dict = {}
    for cell in code_cells:
        source = "".join(cell["source"])
        exec(compile(source, str(notebook_path), "exec"), namespace)

    reports = namespace["check_results"]
    assert set(reports) == {"Seasonal Target", "DKP"}
    for checked in reports.values():
        assert checked["days"] == checked["planned_llm_calls"] == 7
        assert checked["network_calls"] == 0
    assert set(namespace["prompt_texts"]) == set(reports)
    assert namespace["comparison"]["Seasonal Target"]["knowledge"] == {}
    assert namespace["comparison"]["DKP"]["knowledge"]
    assert not (ROOT / "runs").exists()
