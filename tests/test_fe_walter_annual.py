"""Contract checks for the annual teaching-case preparation, without inference."""
import importlib.util
from pathlib import Path
import tempfile
import sys
import unittest
from datetime import date, timedelta


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/fe_walter/annual/prepare.py"
sys.path.insert(0, str(ROOT / "src"))


def load_example():
    spec = importlib.util.spec_from_file_location("annual_example", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AnnualCaseTests(unittest.TestCase):
    def setUp(self):
        self.example = load_example()
        self.rows = [{"date": (date(2016, 1, 1) + timedelta(days=i)).isoformat(),
                      "fe_walter_inflow_cms": 2.0} for i in range(366)]

    def test_leap_year_keeps_all_days_in_order(self):
        result = self.example.select_year(self.rows, 2016)
        self.assertEqual(len(result), 366)
        self.assertEqual(result[59]["date"], "2016-02-29")
        self.assertEqual(result[-1]["date"], "2016-12-31")

    def test_missing_or_duplicate_day_is_rejected(self):
        for rows in (self.rows[:-1], self.rows + [self.rows[0]]):
            with self.subTest(length=len(rows)), self.assertRaisesRegex(ValueError, "consecutive"):
                self.example.select_year(rows, 2016)

    def test_bad_flow_is_rejected(self):
        for value in (-1, float("nan"), float("inf")):
            rows = [dict(row) for row in self.rows]
            rows[3]["fe_walter_inflow_cms"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "flow"):
                self.example.select_year(rows, 2016)

    def test_existing_directory_is_rejected_before_hydrology(self):
        with tempfile.TemporaryDirectory() as folder:
            def forbidden():
                self.fail("existing output must be rejected before simulation")
            with self.assertRaises(FileExistsError):
                self.example.prepare(2016, Path(folder), "test", hydrology_runner=forbidden)

    def test_llm_arms_use_native_method_prompts_and_explicit_retry_settings(self):
        import yaml
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "paired"
            self.example.prepare(2016, target, "paired",
                                 hydrology_runner=lambda: (self.rows, {"fixture": True}))
            settings = [yaml.safe_load((target / f"{name}.yaml").read_text())
                        for name in ("llm_available", "llm_knowledge")]
            prompts = [s["agents"]["fe_operator"]["customization"]["parameters"]["reference"]["system_prompt"]
                       for s in settings]
            self.assertNotEqual(prompts[0], prompts[1])
            self.assertEqual([Path(p).name for p in prompts],
                             ["zeroshot_seasonal_v1_system.txt", "dkp_seasonal_v1_system.txt"])
            self.assertTrue(all(Path(p).is_file() for p in prompts))
            for spec in settings:
                self.assertIsNone(spec["max_calls"])
                self.assertEqual(spec["models"]["reservoir_model"]["max_attempts"], 2)

    def test_prepared_case_passes_the_formal_cli_contract(self):
        from llm_reservoir_agent.workflow import load_settings
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "new-case"
            self.example.prepare(2016, target, "contract-test",
                                 hydrology_runner=lambda: (self.rows, {"fixture": True}))
            for name in ("rule", "llm_available", "llm_knowledge"):
                with self.subTest(method=name):
                    report = load_settings(target / f"{name}.yaml").report
                    self.assertEqual(report["days"], 366)
                    self.assertEqual(report["planned_llm_calls"], 0 if name == "rule" else 366)
                    self.assertFalse(report["live_ready"])


if __name__ == "__main__":
    unittest.main()
