"""Case-level pool checks; no policy, provider or simulation is executed."""
import importlib.util
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/fe_walter/check_pool_levels.py"
SPEC = importlib.util.spec_from_file_location("fe_walter_pool_check", SCRIPT)
pool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pool)


class SeasonalPoolTests(unittest.TestCase):
    def check_rows(self, *rows):
        return pool.evaluate([dict(date=d, pool_elevation_start_ft=h) for d, h in rows])

    def test_season_boundaries_and_leap_day(self):
        for day, expected in [("2020-02-29", "winter_hold"), ("2020-03-14", "winter_hold"),
                              ("2020-03-15", "spring_fill"), ("2020-05-09", "spring_fill"),
                              ("2020-05-10", "summer"), ("2020-10-14", "summer"),
                              ("2020-10-15", "fall_drawdown"), ("2020-10-31", "fall_drawdown"),
                              ("2020-11-01", "winter_hold")]:
            with self.subTest(day=day):
                self.assertEqual(self.check_rows((day, 1300))[0]["season"], expected)

    def test_inclusive_height_bounds(self):
        for day, level, expected in [("2020-01-01", 1297, "PASS"), ("2020-01-01", 1303, "PASS"),
                                     ("2020-01-01", 1296.99, "FAIL"), ("2020-01-01", 1303.01, "FAIL"),
                                     ("2020-04-01", 1300, "PASS"), ("2020-04-01", 1370, "PASS"),
                                     ("2020-04-01", 1299, "FAIL"), ("2020-06-01", 1200, "PASS"),
                                     ("2020-06-01", 1370.01, "FAIL")]:
            with self.subTest(day=day, level=level):
                self.assertEqual(self.check_rows((day, level))[0]["status"], expected)

    def test_windows_cover_every_day_once(self):
        seasons = pool.load_criteria()["seasons"]
        day = date(2020, 1, 1)
        while day.year == 2020:
            md = day.strftime("%m-%d")
            matches = [s for s in seasons if (
                s["start"] <= md < s["end_exclusive"] if s["start"] < s["end_exclusive"]
                else md >= s["start"] or md < s["end_exclusive"])]
            self.assertEqual(len(matches), 1, day)
            day += timedelta(days=1)

    def test_fall_requires_a_strict_daily_decline(self):
        rows = self.check_rows(("2020-10-14", 1360), ("2020-10-15", 1359),
                               ("2020-10-16", 1359), ("2020-10-17", 1360))
        self.assertEqual([r["status"] for r in rows], ["PASS", "PASS", "FAIL", "FAIL"])
        self.assertIn("not_falling", rows[2]["findings"])

    def test_missing_fall_history_is_unknown_but_bad_bounds_still_fail(self):
        self.assertEqual(self.check_rows(("2020-10-15", 1360))[0]["status"], "UNKNOWN")
        self.assertEqual(self.check_rows(("2020-10-15", 1371))[0]["status"], "FAIL")
        rows = self.check_rows(("2020-10-14", 1360), ("2020-10-16", 1350))
        self.assertEqual(rows[1]["status"], "UNKNOWN")

    def test_missing_or_nonfinite_level_is_unknown(self):
        for value in [None, "", "NaN", "inf", "-inf"]:
            with self.subTest(value=value):
                self.assertEqual(self.check_rows(("2020-01-01", value))[0]["status"], "UNKNOWN")

    def test_invalid_input_does_not_become_a_pass(self):
        for rows in [[], [("2020-01-01", "bad")], [("2020-01-01", 1300), ("2020-01-01", 1301)],
                     [("2020-01-02", 1300), ("2020-01-01", 1300)], [("2020-2-1", 1300)]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.check_rows(*rows)

    def test_cli_keeps_source_bytes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "levels.csv", Path(tmp) / "checks.csv"
            source.write_text("date,pool_elevation_start_ft,audit_status\n2020-01-01,1300,FAIL\n", encoding="utf-8")
            before = source.read_bytes()
            summary = pool.check_file(source, output)
            self.assertEqual(summary["counts"], {"PASS": 1, "FAIL": 0, "UNKNOWN": 0})
            self.assertEqual(source.read_bytes(), before)
            self.assertIn("input_sha256", output.read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                pool.check_file(source, output)

    def test_prompt_variants_share_the_versioned_target(self):
        target = pool.load_criteria()["operation_target"]
        for method in ["zeroshot", "dkp"]:
            text = (ROOT / f"prompts/fe_walter_reference/{method}_seasonal_v1_system.txt").read_text(encoding="utf-8")
            self.assertIn("- Operation target: " + target, text)
            original = (ROOT / f"prompts/fe_walter_reference/{method}_system.txt").read_text(encoding="utf-8")
            old_line = next(line for line in original.splitlines() if line.startswith("- Operation target:"))
            self.assertEqual(text, original.replace(old_line, "- Operation target: " + target))


class FigureManualTests(unittest.TestCase):
    def test_manual_downloads_keep_the_current_figure_bytes(self):
        spec = importlib.util.spec_from_file_location("figure_manual_build", ROOT / "docs/build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            build.prepare(target, source_ref="codex/figure1-readme33-preview")
            home = (target / "index.md").read_text(encoding="utf-8")
            overview = (target / "docs/README.md").read_text(encoding="utf-8")
            for ext in ["png", "pdf"]:
                name = "hydroopsllm-figure1." + ext
                self.assertIn("_figure_downloads/" + name, home)
                self.assertIn("_figure_downloads/" + name, overview)
                self.assertEqual((target / "_figure_downloads" / name).read_bytes(),
                                 (ROOT / ("docs/figures/hydrocnhs-coupling-framework-en." + ext)).read_bytes())


if __name__ == "__main__":
    unittest.main()
