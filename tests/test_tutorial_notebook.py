"""Execute the tutorial notebook cells end-to-end without leaving artifacts in the repo."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_offline_synthetic_notebook_runs_cleanly(monkeypatch):
    notebook_path = ROOT / "tutorials" / "offline_synthetic.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert len(code_cells) == 4

    monkeypatch.chdir(ROOT)
    namespace: dict = {}
    for cell in code_cells:
        source = "".join(cell["source"])
        exec(compile(source, str(notebook_path), "exec"), namespace)

    assert namespace["trajectory"][-1]["storage_m3"] == 1_345_600.0
    assert namespace["report"]["status"] == "PASS"
    assert namespace["report"]["days"] == 4
    assert namespace["report"]["observed_network_calls"] == 0
    assert namespace["trajectory_df"]["storage_end_m3"].iloc[-1] == 1_345_600.0
    assert not (ROOT / "runs").exists()
