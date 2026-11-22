"""The vendored HydroCNHS source must match its pinned provenance manifest."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bundled_hydrocnhs_files_match_pinned_source_manifest():
    manifest = json.loads((ROOT / "third_party" / "hydrocnhs" / "SOURCE.json").read_text())
    assert manifest["schema_version"] == "bundled-source.v1"
    assert manifest["commit"] == "fdd5097a3fcabb312c6c3739efc71da2d67c47da"

    for relative, record in manifest["files"].items():
        content = (ROOT / relative).read_bytes()
        assert len(content) == record["bytes"], relative
        assert hashlib.sha256(content).hexdigest() == record["sha256"], relative
        patch = record.get("patch")
        if patch is not None:
            patch_content = (ROOT / patch["path"]).read_bytes()
            assert hashlib.sha256(patch_content).hexdigest() == patch["sha256"], patch["path"]


def test_runtime_pin_selects_the_same_bundled_commit_and_hashes():
    runtime = json.loads((ROOT / "environment" / "hydrocnhs-core.json").read_text())
    source = json.loads((ROOT / "third_party" / "hydrocnhs" / "SOURCE.json").read_text())
    assert runtime["hydrocnhs_commit"] == source["commit"]
    for record in runtime["files"]:
        relative = ROOT / "src" / "hydrocnhs" / record["path"]
        normalized = relative.read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(normalized).hexdigest() == record["normalized_sha256"], record["path"]
