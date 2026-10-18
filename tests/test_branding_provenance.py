"""Current branding receipts bind the source and every advertised export."""
import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = (
    "docs/_static/hydroopslm-social-preview.json",
    "docs/figures/assets/branding/provenance.json",
)


def assert_identity(path, expected):
    data = (ROOT / path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected["sha256"], path
    assert len(data) == expected["bytes"], path


@pytest.mark.parametrize("path", MANIFESTS)
def test_current_name_revision_files_match_their_receipt(path):
    receipt = json.loads((ROOT / path).read_text(encoding="utf-8"))
    revision = receipt["branding_revision"]
    assert revision["display_name"] == "HydroReOpLLM"
    for source, expected in revision["current_files"].items():
        assert_identity(source, expected)
    assert receipt["historical_records"]["before_name_change"]
    assert receipt["historical_records"]["incoming_name_revision_before_consistency_review"]


def test_branding_file_index_describes_current_bytes():
    receipt = json.loads((ROOT / MANIFESTS[1]).read_text(encoding="utf-8"))
    for expected in receipt["files"]:
        assert_identity(expected["file"], expected)


def test_social_preview_source_and_export_fields_agree():
    receipt = json.loads((ROOT / MANIFESTS[0]).read_text(encoding="utf-8"))
    for prefix, field in (("source", "source_file"), ("editable", "editable_file"),
                          ("export", "export_file")):
        data = (ROOT / receipt[field]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == receipt[prefix + "_sha256"]
    assert len((ROOT / receipt["export_file"]).read_bytes()) == receipt["export_bytes"]
