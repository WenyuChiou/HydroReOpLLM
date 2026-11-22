"""Regression coverage and provenance for the reviewed HydroCNHS visual patch."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from hydrocnhs.visual import Visual


ROOT = Path(__file__).resolve().parents[1]
VISUAL = ROOT / "src/hydrocnhs/visual.py"
SOURCE = ROOT / "third_party/hydrocnhs/SOURCE.json"


def test_plot_reg_uses_public_indicator_api_and_preserves_return_contract(monkeypatch):
    monkeypatch.setattr(plt, "show", lambda: pytest.fail("show=False called pyplot.show"))
    observed = [1.0, 2.0, 3.0, 4.0, float("nan")]
    simulated = [1.2, 1.8, 3.4, 3.9, 5.0]

    axis = Visual.plot_reg(observed, simulated, show=False)
    try:
        assert axis.figure is not None
        annotation = axis.texts[0].get_text()
        assert all(label in annotation for label in ("$r$", "$r^2$", "RMSE", "NSE", "KGE"))
        values = [float(line.rsplit(":", 1)[1]) for line in annotation.splitlines()]
        assert len(values) == 5 and all(math.isfinite(value) for value in values)
    finally:
        plt.close(axis.figure)

    parameters = Visual.plot_reg(observed, simulated, show=False, return_reg_par=True)
    try:
        assert isinstance(parameters, list) and len(parameters) == 2
        assert all(math.isfinite(value) for value in parameters)
        assert parameters == pytest.approx([0.97, 0.15])
    finally:
        plt.close("all")


def test_bundled_visual_patch_is_fully_hash_bound():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    entry = source["files"]["src/hydrocnhs/visual.py"]
    patch = entry["patch"]
    patch_path = ROOT / patch["path"]

    assert source["commit"] == "fdd5097a3fcabb312c6c3739efc71da2d67c47da"
    assert entry["upstream_sha256"] == (
        "6dcf127865e2dd2475254505c7488d90fdab96d0362884ecfb1fec6e5d2faaf3")
    assert entry["sha256"] == hashlib.sha256(VISUAL.read_bytes()).hexdigest()
    assert entry["bytes"] == VISUAL.stat().st_size
    assert patch == {
        "id": "hydrocnhs-visual-indicator-api",
        "version": 1,
        "path": "third_party/hydrocnhs/patches/visual-indicator-api.patch",
        "sha256": hashlib.sha256(patch_path.read_bytes()).hexdigest(),
    }
