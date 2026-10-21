"""Resolve the approved portable GIS source without starting ArcGIS or a model."""
import importlib.util
from pathlib import Path
import zipfile

import pytest


@pytest.mark.parametrize("project", ["native/project/river-legend-study-area.aprx",
                                     "p30/historical.aprx"])
def test_export_uses_the_packaged_project_directory(tmp_path, monkeypatch, project):
    source = Path(__file__).resolve().parents[1] / "docs/figures/source/render_fe_catchment.py"
    spec = importlib.util.spec_from_file_location("map_export", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    package = tmp_path / "source.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(project, b"offline project fixture")
    calls = []

    def capture(command, *, check, cwd):
        project_file = Path(command[command.index("--project") + 1])
        assert project_file.is_file()
        assert project_file.as_posix().endswith(project)
        assert cwd == project_file.parent
        assert check is True
        calls.append(command)

    monkeypatch.setattr(module.subprocess, "run", capture)
    module.export_map(package, tmp_path / "map", 240)
    assert len(calls) == 1
