import copy
import csv
import importlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tests.fixtures.fe_walter_legacy.case import sha256
from tests.fixtures.fe_walter_legacy.hydrology import AGGREGATE, CORE, MANIFEST, MODEL, UNITS, WEATHER, load_smoke_inputs, main, run_smoke


class HydrologyInputTests(unittest.TestCase):
    def test_missing_weather_day_rejected_even_with_updated_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in (MODEL, WEATHER, CORE, MANIFEST):
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            with (root / WEATHER).open(newline="") as stream:
                reader = csv.DictReader(stream); fields = reader.fieldnames; rows = list(reader)
            with (root / WEATHER).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows[1:])
            manifest = json.loads((root / MANIFEST).read_text())
            for item in manifest["files"]:
                if item["path"] == WEATHER: item["sha256"] = sha256(root / WEATHER)
            (root / MANIFEST).write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "every day"):
                load_smoke_inputs(root)

    def test_input_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in (MODEL, WEATHER, CORE, MANIFEST):
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            with (root / WEATHER).open("a") as stream: stream.write("changed\n")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_smoke_inputs(root)

    def test_existing_output_rejected_before_hydrology_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("tests.fixtures.fe_walter_legacy.hydrology.run_smoke") as execute:
                with self.assertRaises(FileExistsError): main(["--output", folder])
                execute.assert_not_called()
            self.assertEqual(list(Path(folder).iterdir()), [])


class HydrologyProvenanceTests(unittest.TestCase):
    def test_bundled_hydrocnhs_without_separate_distribution_has_source_pin(self):
        from importlib.metadata import PackageNotFoundError
        import hydrocnhs
        from tests.fixtures.fe_walter_legacy.cli import implementation_provenance

        def version(name):
            if name == "hydrocnhs":
                raise PackageNotFoundError(name)
            return "fixture-version"

        with patch("importlib.metadata.version", side_effect=version):
            report = implementation_provenance(ROOT, "hydrocnhs")
        self.assertIsNone(report["runtime"]["packages"]["hydrocnhs"])
        source = report["runtime"]["module_sources"]["hydrocnhs"]
        self.assertEqual(source["file"], str(Path(hydrocnhs.__file__).resolve()))
        self.assertEqual(source["sha256"], sha256(Path(source["file"])))

    def test_missing_required_dependency_metadata_is_not_suppressed(self):
        from importlib.metadata import PackageNotFoundError
        from tests.fixtures.fe_walter_legacy.cli import implementation_provenance

        def version(name):
            if name == "numpy":
                raise PackageNotFoundError(name)
            return "fixture-version"

        with patch("importlib.metadata.version", side_effect=version):
            with self.assertRaises(PackageNotFoundError):
                implementation_provenance(ROOT, "hydrocnhs")


@unittest.skipUnless(importlib.util.find_spec("hydrocnhs"), "optional HydroCNHS runtime is not installed")
class NativeHydrologyTests(unittest.TestCase):
    def test_all_seven_units_run_accepted_gwlf_with_real_lagged_routing(self):
        import hydrocnhs
        import numpy as np
        engine = importlib.import_module("hydrocnhs.hydrocnhs")
        source = hydrocnhs.load_model(str(ROOT / MODEL), print_summary=False)
        parameters = copy.deepcopy(source["RainfallRunoff"])
        _, _, weather = load_smoke_inputs(ROOT)
        before = sha256(ROOT / MODEL)
        with patch.object(engine, "run_GWLF", wraps=engine.run_GWLF) as gwlf:
            rows, summary = run_smoke(ROOT)
        self.assertEqual(gwlf.call_count, 7)
        area_to_unit = {parameters[u]["Inputs"]["Area"]: u for u in UNITS}
        seen = set()
        for call in gwlf.call_args_list:
            unit = area_to_unit[call.kwargs["inputs"]["Area"]]; seen.add(unit)
            self.assertEqual(call.kwargs["pars"], parameters[unit]["Pars"])
            self.assertEqual(call.kwargs["inputs"], parameters[unit]["Inputs"])
            self.assertIsNone(call.kwargs["vars"])
            self.assertEqual(len(call.kwargs["prec"]), 59)
            self.assertAlmostEqual(call.kwargs["prec"][0], weather[unit]["1989-01-01"]["precipitation_mm"] / 10)
        self.assertEqual(seen, set(UNITS)); self.assertEqual(sha256(ROOT / MODEL), before)
        self.assertEqual(summary["assigned_flow_outlets"], [AGGREGATE])
        self.assertFalse(summary["assigned_unit_hydrographs"])
        self.assertEqual(len(rows), 59)
        inflow = np.array([r["fe_walter_inflow_cms"] for r in rows])
        local_total = np.array([sum(r[f"{u}_generated_cms"] for u in UNITS) for r in rows])
        routed_total = np.array([sum(r[f"{u}_routed_cms"] for u in UNITS) for r in rows])
        np.testing.assert_allclose(routed_total, inflow, rtol=0, atol=1e-10)
        self.assertFalse(np.allclose(local_total, inflow))
        self.assertTrue(np.isfinite(inflow).all()); self.assertTrue((inflow > 0).all())


if __name__ == "__main__": unittest.main()
