"""Generic-core and import-boundary checks for the active FE Walter entry."""
from datetime import date
import builtins
import importlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

from llm_reservoir_agent.configured_backend import ConfiguredBackend
from llm_reservoir_agent.network import PROJECT_ROOT
from examples.fe_walter.extensions import native_case, reference_backend


class AnikGenericCaseTests(unittest.TestCase):
    def test_active_modules_reload_with_vendor_imports_blocked(self):
        forbidden = {"reservoir_model", "zeroshot_llm_release", "dkp_llm_release", "benchmark_release"}
        original = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in forbidden:
                raise AssertionError(f"active runtime imported vendor oracle {name}")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded):
            importlib.reload(native_case)
            active = importlib.reload(reference_backend)
        self.assertEqual(active.ReferenceBackend.__bases__, (object,))
        source = Path(active.__file__).read_text(encoding="utf-8")
        self.assertNotIn("load_anik", source)
        self.assertNotIn("third_party.anik_v3_7", source)

    def test_backend_composes_generic_core_and_preview_is_pure(self):
        from llm_reservoir_agent.workflow import load_settings

        settings = load_settings(PROJECT_ROOT / "tests/fixtures/fe_walter_current/zeroshot.yaml")
        agent = settings.agents["fe_operator"]
        backend = reference_backend.ReferenceBackend(
            agent["reference"], settings.network["reservoirs"]["FEWalter"]["physical"],
            runtime_root=PROJECT_ROOT,
        )
        self.assertIsInstance(backend._core, ConfiguredBackend)
        preview = reference_backend.preview_backend(
            agent, settings.network["reservoirs"]["FEWalter"]["physical"], PROJECT_ROOT)
        self.assertEqual(preview["kind"], "config_preview")
        self.assertEqual(preview["messages"][0]["role"], "system")
        self.assertFalse(preview["model_used"])
        self.assertEqual(backend.network_calls, 0)

    def test_seasonal_boundaries_are_total_and_explicit(self):
        profile = native_case.load_case_profile(PROJECT_ROOT)
        expected = {
            date(2016, 3, 14): ("winter", 1300.0),
            date(2016, 3, 15): ("spring_fill", 1370.0),
            date(2016, 5, 9): ("spring_fill", 1370.0),
            date(2016, 5, 10): ("summer", 1370.0),
            date(2016, 10, 14): ("summer", 1370.0),
            date(2016, 10, 15): ("fall_drawdown", 1300.0),
            date(2016, 10, 31): ("fall_drawdown", 1300.0),
            date(2016, 11, 1): ("winter", 1300.0),
        }
        for day, value in expected.items():
            with self.subTest(day=day):
                period = profile.target_period(day)
                self.assertEqual((period["id"], period["target_ft"]), value)

    def test_profile_and_implicit_resources_are_pinned_before_execution(self):
        from llm_reservoir_agent.workflow import load_settings, run_settings

        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            extension_dir = scratch / "examples/fe_walter/extensions"
            profile_dir = scratch / "examples/fe_walter/profiles"
            curve_dir = scratch / "cases/fe_belt_prompton_offline"
            shutil.copytree(PROJECT_ROOT / "examples/fe_walter/extensions", extension_dir,
                            ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(PROJECT_ROOT / "examples/fe_walter/profiles", profile_dir)
            curve_dir.mkdir(parents=True)
            curve = curve_dir / "fe_walter_storage_elevation.csv"
            shutil.copy2(PROJECT_ROOT / "cases/fe_belt_prompton_offline/fe_walter_storage_elevation.csv", curve)

            source = PROJECT_ROOT / "experiments/fe_walter_reference_zeroshot.yaml"
            data = yaml.safe_load(source.read_text(encoding="utf-8"))
            data["extensions"] = {key: str(extension_dir / "__init__.py")
                                  for key in data["extensions"]}
            data["case"] = str((source.parent / data["case"]).resolve())
            data["output"] = str(scratch / "output")
            response = data["agents"]["fe_operator"]["reference"]["responses"]
            data["agents"]["fe_operator"]["reference"]["responses"] = str((source.parent / response).resolve())
            data["agents"]["fe_operator"]["reference"].update(
                system_prompt=str((PROJECT_ROOT / "examples/fe_walter/prompts/available_information.txt").resolve()),
                system_prompt_mode="custom",
            )
            config = scratch / "experiment.yaml"
            config.write_text(yaml.safe_dump(data), encoding="utf-8")
            settings = load_settings(config)

            pinned = set(settings.files)
            profile = profile_dir / "reservoir.json"
            self.assertTrue({str(profile.resolve()), str(curve.resolve()),
                             str((PROJECT_ROOT / "examples/fe_walter/prompts/available_information.txt").resolve())
                             }.issubset(pinned))
            changed = json.loads(profile.read_text(encoding="utf-8"))
            changed["target_periods"][0]["target_ft"] = 1301.0
            profile.write_text(json.dumps(changed), encoding="utf-8")
            transport = Mock(side_effect=AssertionError("transport must remain unused"))
            with self.assertRaisesRegex(ValueError, "changed after configuration check"):
                run_settings(settings, transport=transport)
            transport.assert_not_called()
            self.assertFalse(Path(data["output"]).exists())


if __name__ == "__main__":
    unittest.main()
