"""Case-level pool checks; no policy, provider or simulation is executed."""
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

import yaml


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

    def test_prompt_variants_share_prof_yang_target(self):
        target = json.loads((ROOT / "examples/fe_walter/profiles/reservoir.json").read_text(encoding="utf-8"))["operation_target_description"]
        self.assertEqual(target, 'Your goal is to keep the water level within the designated seasonal pool levels. From mid-October until late spring, keep the pool near the conservation pool at 1300.0 ft N.G.V.D. On or before 1 April, when hydrologic conditions allow, raise the pool toward 1370.0 ft N.G.V.D., the top of the temporary recreation pool, to reach it by early May. From May through mid-October, keep the pool at or below 1370.0 ft N.G.V.D. By mid-October, release any remaining stored water to return the pool to 1300.0 ft.')
        for method in ["zeroshot", "dkp"]:
            text = (ROOT / ("examples/fe_walter/prompts/" + {"zeroshot": "available_information.txt", "dkp": "retrieved_knowledge.txt"}[method])).read_text(encoding="utf-8")
            self.assertIn("- Operation target: " + target, text)

    def test_active_entries_use_the_canonical_current_prompts(self):
        target = json.loads((ROOT / "examples/fe_walter/profiles/reservoir.json").read_text(encoding="utf-8"))["operation_target_description"]
        entries = (
            ("coupled/agents.llm_available.yaml", "zeroshot"),
            ("coupled/agents.llm_knowledge.yaml", "dkp"),
        )
        for name, method in entries:
            with self.subTest(entry=name):
                path = ROOT / "examples/fe_walter" / name
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                agent = data["fe_operator"]
                reference = agent["customization"]["parameters"]["reference"]
                self.assertNotIn("seasonal_criteria_file", reference)
                self.assertIs(reference["prompt_storage"], False)
                self.assertIs(reference["hide_availability_line"], True)
                self.assertIs(reference["dkp_no_missing_inputs"], True)
                actual = (path.parent / reference["system_prompt"]).read_text(encoding="utf-8")
                canonical = ROOT / "examples/fe_walter/prompts" / {
                    "zeroshot": "available_information.txt", "dkp": "retrieved_knowledge.txt"}[method]
                self.assertEqual(actual, canonical.read_text(encoding="utf-8"))
                self.assertIn("- Operation target: " + target, actual)

    def test_november_first_requires_winter_pool_even_if_run_completed(self):
        for level, status in [(1300.0, "PASS"), (1390.8590831121244, "FAIL"),
                              (1450.0000027053293, "FAIL")]:
            with self.subTest(level=level):
                row = self.check_rows(("2016-11-01", level))[0]
                self.assertEqual(row["season"], "winter_hold")
                self.assertEqual(row["status"], status)


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
            for page in (home, overview):
                self.assertIn("hydrocnhs-coupling-framework-en.png", page)
                self.assertNotIn("_figure_downloads/", page)
            self.assertIn("hydroopslm-cover.png", home)
            self.assertNotIn("hydroopslm-cover.png", overview)
            self.assertLess(home.index("hydroopslm-cover.png"),
                            home.index("hydrocnhs-coupling-framework-en.png"))
            # Keep the core workflow in the Overview and its original figure
            # downloads byte-exact; branding stays separate from that workflow.
            self.assertIn("hydrocnhs-coupling-framework-en.png", overview)
            for ext in ["png", "pdf"]:
                name = "hydroopsllm-figure1." + ext
                self.assertEqual((target / "_figure_downloads" / name).read_bytes(),
                                 (ROOT / ("docs/figures/hydrocnhs-coupling-framework-en." + ext)).read_bytes())


if __name__ == "__main__":
    unittest.main()
