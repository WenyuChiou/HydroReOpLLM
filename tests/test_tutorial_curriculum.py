"""Validate all 4 streamlined tutorial curriculum modules: structure, trilingual guides, PNG outputs, and offline execution."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
import re

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pytest


ROOT = Path(__file__).resolve().parents[1]
TUTORIALS_DIR = ROOT / "tutorials"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PERSONAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:[/\\]{1,2}users[/\\]|/users/|appdata|local[/\\]{1,2}temp)")

CURRICULUM_MODULES = (
    ("01_hydrocnhs_watershed_inflows", "01_hydrocnhs_watershed_inflows.ipynb", 1_000_000),
    ("02_reservoir_and_agent_setup", "02_reservoir_and_agent_setup.ipynb", 1_000_000),
    ("03_run_single_reservoir_simulation", "03_run_single_reservoir_simulation.ipynb", 1_000_000),
    ("04_run_multi_reservoir_cascade", "04_run_multi_reservoir_cascade.ipynb", 1_000_000),
)


def _decode_png_payload(encoded: str | list[str]) -> None:
    if isinstance(encoded, list):
        encoded = "".join(encoded)
    raw = base64.b64decode(encoded, validate=True)
    assert raw.startswith(PNG_SIGNATURE)
    decoded = mpimg.imread(io.BytesIO(raw), format="png")
    assert decoded.ndim >= 2
    assert decoded.shape[0] > 0 and decoded.shape[1] > 0


@pytest.mark.parametrize(
    ("folder_name", "notebook_name", "max_bytes"),
    CURRICULUM_MODULES,
    ids=[entry[0] for entry in CURRICULUM_MODULES],
)
def test_tutorial_module_structure_hygiene_and_png_outputs(folder_name, notebook_name, max_bytes):
    module_dir = TUTORIALS_DIR / folder_name
    assert module_dir.is_dir(), f"missing module folder: {folder_name}"
    for guide_name in ("README.md", "README.zh-TW.md", "README.zh-CN.md"):
        guide_path = module_dir / guide_name
        assert guide_path.is_file(), f"missing {guide_name} in {folder_name}"
        assert guide_path.read_text(encoding="utf-8").strip(), f"empty {guide_name} in {folder_name}"

    nb_path = module_dir / notebook_name
    assert nb_path.is_file(), f"missing notebook {notebook_name} in {folder_name}"

    raw_bytes = nb_path.read_bytes()
    assert b"\r" not in raw_bytes, f"{notebook_name} must use LF line endings"
    assert len(raw_bytes) <= max_bytes, f"{notebook_name} exceeds {max_bytes:,} bytes ({len(raw_bytes):,})"

    nb_text = raw_bytes.decode("utf-8")
    assert not PERSONAL_PATH_RE.search(nb_text), f"personal or temp path leaked into {notebook_name}"

    notebook = json.loads(nb_text)
    assert notebook["nbformat"] == 4
    assert notebook.get("nbformat_minor", 0) >= 5

    md_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "markdown"]
    assert all(
        "```mermaid" not in "".join(cell["source"]).lower() for cell in md_cells
    ), f"{notebook_name} must keep Mermaid diagrams in README.md, not inside .ipynb"

    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert code_cells, f"{notebook_name} must contain code cells"

    png_count = 0
    for cell in code_cells:
        cell_id = cell.get("id")
        assert isinstance(cell.get("execution_count"), int) and cell["execution_count"] >= 1, (
            f"unexecuted code cell {cell_id} in {notebook_name}"
        )
        outputs = cell.get("outputs", [])
        assert all(out.get("output_type") != "error" for out in outputs), (
            f"error output in cell {cell_id} of {notebook_name}"
        )
        for out in outputs:
            data = out.get("data")
            if isinstance(data, dict) and "image/png" in data:
                _decode_png_payload(data["image/png"])
                png_count += 1

    assert png_count >= 2, f"{notebook_name} must embed at least two valid PNG plot outputs"


@pytest.mark.parametrize(
    ("folder_name", "notebook_name", "_max_bytes"),
    CURRICULUM_MODULES,
    ids=[entry[0] for entry in CURRICULUM_MODULES],
)
def test_tutorial_module_executes_offline_cleanly(folder_name, notebook_name, _max_bytes, tmp_path, monkeypatch):
    module_dir = TUTORIALS_DIR / folder_name
    nb_path = module_dir / notebook_name
    notebook = json.loads(nb_path.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]

    plt.switch_backend("Agg")
    monkeypatch.setattr(plt, "show", lambda: None)
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    monkeypatch.chdir(module_dir)

    namespace: dict = {}
    try:
        for cell in code_cells:
            source = "".join(cell["source"])
            exec(compile(source, f"{nb_path}:{cell.get('id')}", "exec"), namespace)

        if folder_name == "03_run_single_reservoir_simulation":
            assert namespace["verification"]["status"] == "PASS"
            agent_env = namespace["runtime_environment"]["agents"]["FEWalter"]
            snap = agent_env["server_runtime_snapshot"]["primary"]
            assert snap["server_version"]
            assert str(snap["model_digest_sha256"]).startswith("sha256:")
            assert agent_env["seed"] == 3
            assert namespace["tamper_caught"] is True
            assert namespace["balance_residual"] < 1e-6

        assert not (ROOT / "runs").exists()
        assert not (TUTORIALS_DIR / "runs").exists()
        assert not (module_dir / "runs").exists()
    finally:
        plt.close("all")
