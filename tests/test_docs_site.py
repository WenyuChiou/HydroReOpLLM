"""The publication validator includes the current lesson and preserves its bytes."""
from pathlib import Path

import pytest

from scripts.check_docs_site import validate

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ("operation.ipynb", "main.ipynb", "advanced.ipynb", "downstream_validation.ipynb")


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text("<html><body>Manual</body></html>", encoding="utf-8")
    for index, name in enumerate(NOTEBOOKS):
        folder = tmp_path / "_downloads" / str(index)
        folder.mkdir(parents=True)
        (folder / name).write_bytes((ROOT / "tutorials" / name).read_bytes())
    return tmp_path


def test_current_operation_notebook_is_part_of_publication_inventory(site):
    report = validate(site)
    assert report["notebook_downloads"] == 4


def test_missing_operation_notebook_is_rejected(site):
    (site / "_downloads/0/operation.ipynb").unlink()
    with pytest.raises(ValueError, match="Expected 4 original notebook downloads, found 3"):
        validate(site)


def test_changed_operation_notebook_bytes_are_rejected(site):
    path = site / "_downloads/0/operation.ipynb"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Notebook download differs.*operation.ipynb"):
        validate(site)
