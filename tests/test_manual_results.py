"""Check saved scientific evidence and its transport into the manual; no inference."""
from collections import Counter
import csv
from datetime import date, timedelta
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples/fe_walter/reference_outputs/long_term_dkp"


def test_full_period_evidence_pins():
    manifest = json.loads((DATA / "source_manifest.json").read_text())
    assert manifest["original_source_hashes"]["trajectory.csv"] == "83c2e8c3f82a708485ca58ab3207a0aef2e88cf37f5061de9b57cfb3ded885b7"
    assert manifest["model"] == "gemma4:12b"
    assert manifest["temperature"] == 0.7
    assert manifest["strategy_acceptance"] == "FAIL"
    for name, expected in manifest["copied_file_hashes"].items():
        assert "\\" not in name, "Manifest paths must work on POSIX and Windows"
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == expected, name
    assert manifest["unknown_attempt_and_cost_retained"] is True


def test_daily_results_preserve_causal_accounting_and_failed_audits():
    with (DATA / "plotted_daily.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1827
    previous_storage = 2457848.279729185
    for day, row in enumerate(rows):
        assert row["date"] == (date(2016, 1, 1) + timedelta(days=day)).isoformat()
        start = float(row["storage_start_m3"])
        end = float(row["storage_end_m3"])
        assert start == previous_storage
        total = float(row["total_outflow_cms"])
        assert total == float(row["controlled_release_cms"]) + float(row["spill_cms"])
        assert float(row["mass_balance_residual_m3"]) == 0
        expected = start + (float(row["inflow_cms"]) - total) * 86400
        assert math.isclose(end, expected, rel_tol=0, abs_tol=1e-7)
        previous_storage = end
    assert Counter(row["audit_status"] for row in rows) == {"PASS":946, "WARN":170, "FAIL":711}
    assert rows[-1]["date"] == "2020-12-31"


def test_manual_prepare_copies_original_downloads_without_network():
    spec = importlib.util.spec_from_file_location("manual_build", ROOT / "docs/build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as folder, mock.patch("socket.socket", side_effect=AssertionError("network prohibited")):
        output = Path(folder)
        module.prepare(output, source_ref="codex/manual-book-v1")
        for name in ("main", "advanced"):
            assert (output / f"_notebook_downloads/{name}.ipynb").read_bytes() == (ROOT / f"tutorials/{name}.ipynb").read_bytes()
        published = output / "_case_downloads/dkp_2016_2020"
        assert len(list(published.iterdir())) == 14
        assert (published / "plotted_daily.csv").read_bytes() == (DATA / "plotted_daily.csv").read_bytes()
        assert (published / "trace_2020-06-15.json").read_bytes() == (DATA / "trace_2020-06-15.json").read_bytes()
        config = (output / "conf.py").read_text()
        assert 'nb_execution_mode = "off"' in config
        assert (output / "examples/fe_walter/results.md").exists()
        assert not (output / "paper").exists(), "Research drafts must not be published"
        assert not (output / "results").exists(), "Manual assets must come from curated examples"
        method = (output / "examples/fe_walter/zero_shot/README.md").read_text(encoding="utf-8")
        assert "/blob/codex%2Fmanual-book-v1/" in method
