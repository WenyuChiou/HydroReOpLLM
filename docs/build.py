"""Build a portable HTML manual from maintained pages and saved notebook outputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "https://github.com/WenyuChiou/HydroReOpLLM"
FIGURE_DOWNLOADS = {
    f"docs/figures/hydrocnhs-coupling-framework-en.{ext}": f"hydroopsllm-figure1.{ext}"
    for ext in ("png", "pdf")
}
FIGURE_DOWNLOADS.update({
    f"docs/figures/{name}.{ext}": f"{name}.{ext}"
    for name in ("simulation-stages", "reservoir-agent-mapping",
                 "prompt-context-workflow", "fe-walter-weather-workflow")
    for ext in ("drawio", "svg")
})
# Publish only accepted comparison plots and their numeric display exports.
# Raw model records and unrelated experiment folders remain outside the manual.
FIGURE_DOWNLOADS.update({
    "examples/fe_walter/completed_results/" + name: "completed_results/" + name
    for name in (
        "daily_2021_2025.png", "daily_2021_2025.pdf", "daily_2021_2025.svg",
        "daily_2021_2025_range.png", "daily_2021_2025_range.pdf", "daily_2021_2025_range.svg",
        "hourly_events_AB.png", "hourly_events_AB.pdf", "hourly_events_AB.svg",
        "daily_chart_data.csv", "daily_run_range.csv", "daily_target_reference.csv",
        "hourly_chart_data.csv", "table3_daily_simulation_performance.png",
        "table3_daily_simulation_performance.pdf", "table3_summary.csv",
        "table3_metrics_per_seed.csv", "provenance.json",
    )
})
MAP_DOWNLOADS = {
    **{f"docs/figures/fe-walter-catchment.{ext}": f"fe-walter-catchment.{ext}"
       for ext in ("png", "svg", "pdf")},
    "data/figures/manual_map/fe-walter-arcgis-source.zip": "fe-walter-arcgis-source.zip",
}
HYDROLOGY_DOWNLOADS = {
    **{f"examples/fe_walter/hydrology_data/{name}": name for name in (
        "calibration_validation_metrics.csv", "subcatchments.csv", "provenance.json",
        "reproduced_cv_metrics_20261016.csv", "reproduction_20261016.json",
    )},
    "data/accepted/fe_walter_hydrology.yaml": "fe_walter_hydrology.yaml",
    "data/accepted/historical_manifest.json": "historical_manifest.json",
}
HYDROLOGY_DOWNLOADS.update({
    f"examples/fe_walter/hydrology_data/climate/{name}": name
    for name in ("fe_walter_climate_monthly_1989_2025.csv",
                 "fe_walter_climate_1989_2025.png", "fe_walter_climate_1989_2025.svg",
                 "fe_walter_climate_1989_2025.pdf")
})
HYDROLOGY_DOWNLOADS["examples/fe_walter/hydrology_data/climate/provenance.json"] = "climate-provenance.json"
ANNUAL_DOWNLOADS = {
    **{
    f"examples/fe_walter/annual/outputs/{name}": name for name in (
        "daily.csv", "attempt_summary.json", "failed_reply_2016_06_18.txt",
        "annual_attempt.pdf", "annual_attempt.svg",
    )
    },
}
CONFIG_DOWNLOADS = {
    f"examples/fe_walter/coupled/{name}": name
    for name in (
        "experiment.yaml", "llm_available.yaml", "llm_knowledge.yaml",
        "hydrology.yaml", "models.yaml", "agents.rule.yaml", "agents.llm_available.yaml",
        "agents.llm_knowledge.yaml", "auditors.yaml", "reservoirs.json",
    )
}
CONFIG_DOWNLOADS.update({
    f"examples/fe_walter/prompts/{name}": name
    for name in ("available_information.txt", "retrieved_knowledge.txt")
})
CONFIG_DOWNLOADS.update({
    "examples/fe_walter/seasonal_pool_criteria.json": "seasonal_pool_criteria.json",
    "examples/fe_walter/knowledge/operating_rules.md": "operating-knowledge.txt",
})
COMPLETED_DOWNLOADS = {
    f"examples/fe_walter/coupled/outputs/{name}": name
    for name in ("daily.csv", "summary.json", "pool_release.svg", "pool_release.pdf",
                 "llm_available_decision.json", "llm_knowledge_decision.json")
}
YEAR_DOWNLOADS = {
    f"examples/fe_walter/coupled/outputs/2016/{name}": f"2016-{name}"
    for name in ("daily.csv", "summary.json", "pins.json", "pool_release.png", "pool_release.svg",
                 "pool_release.pdf", "llm_available_decision.json", "llm_knowledge_decision.json")
}
COMPARISON_DOWNLOADS = {
    f"examples/fe_walter/coupled/outputs/gemma4_2016_comparison/{name}": f"gemma4-2016-{name}"
    for name in ("daily.csv", "summary.json", "pool_release.png", "pool_release.svg",
                 "pool_release.pdf", "llm_available_pair.json", "llm_knowledge_pair.json")
}
TUTORIAL_DOWNLOADS = {
    f"examples/fe_walter/coupled/outputs/current_tutorial/{name}": name
    for name in (
        "daily.csv", "provenance.json",
        "daily_water_elevation.png", "daily_water_elevation.svg", "daily_water_elevation.pdf",
        "controlled_release_daily.png", "controlled_release_daily.svg", "controlled_release_daily.pdf",
        "reservoir_operations.png", "reservoir_operations.svg", "reservoir_operations.pdf",
    )
}
# Curated five-year case: portable inputs and saved baseline, without raw journals.
TUTORIAL_DOWNLOADS.update({
    "examples/fe_walter/operation/" + name: "operation/" + name
    for name in (
        "experiment.yaml", "llm_available.yaml", "llm_knowledge.yaml", "agents.rule.yaml",
        "case.json", "inflows.csv", "initialization.json", "provenance.json",
        "hydrology/model.yaml", "hydrology/forcing.csv.gz", "hydrology/hydrology.yaml",
        "outputs/reservoir_daily.csv", "outputs/streamflow_daily.csv", "outputs/summary.json",
        "outputs/reservoir_operations.png", "outputs/reservoir_operations.svg", "outputs/reservoir_operations.pdf",
        "outputs/downstream_streamflow.png", "outputs/downstream_streamflow.svg", "outputs/downstream_streamflow.pdf",
    )
})
DAILY_DOWNLOADS = {
    "examples/daily_offline/" + name: "daily-offline/" + name
    for name in ("single.yaml", "single.json", "cascade.yaml", "cascade.json", "operator.txt")
}
DAILY_DOWNLOADS.update({
    "docs/qa/module-inventory.json": "qa/module-inventory.json",
    "examples/fe_walter/operation/engineering-sources-v2.json": "operation/engineering-sources-v2.json",
    "examples/fe_walter/operation/engineering-sources-v3.json": "operation/engineering-sources-v3.json",
})
# Generic templates are maintained once and included verbatim in the chapters.
DOWNSTREAM_DOWNLOADS = {
    "examples/fe_walter/downstream/" + name: name
    for name in (
        "prepare.py", "plot.py", "prepare_observations.py", "validate.py", "validation.yaml", "calibration.yaml",
        "inputs/observations.csv", "inputs/source_manifest.json",
        "inputs/gauge_basin.geojson", "inputs/dam_reach_basin.geojson", "inputs/reach.geojson",
        "inputs/station.json", "inputs/station_metadata.txt",
        "outputs/daily.csv", "outputs/lateral_inflow.csv", "outputs/routing_tail.csv",
        "outputs/partition.json", "outputs/catchment_partition.geojson", "outputs/routing.json",
        "outputs/report.json", "outputs/manifest.json",
        "outputs/streamflow.png", "outputs/streamflow.svg", "outputs/streamflow.pdf",
        "outputs/watershed.png", "outputs/watershed.svg", "outputs/watershed.pdf",
    )
}
DOWNSTREAM_DOWNLOADS["tutorials/downstream_validation.ipynb"] = "downstream_validation.ipynb"
# Publish the curated C&V files; full research inputs and search records stay external.
DOWNSTREAM_DOWNLOADS.update({
    "examples/fe_walter/downstream/outputs/hydrology_validation/" + name:
    "outputs/hydrology_validation/" + name
    for name in (
        "calibration_progress.pdf", "calibration_progress.svg", "daily.csv",
        "hydrology_validation.pdf", "hydrology_validation.png", "hydrology_validation.svg",
        "model_selection.csv", "regionalization.csv", "summary.json",
    )
})
FIGURE_DOWNLOADS.update({
    "docs/figures/downstream-workflow.drawio": "downstream-workflow.drawio",
    "docs/figures/downstream-workflow.svg": "downstream-workflow.svg",
    "docs/figures/downstream-validation.drawio": "downstream-validation.drawio",
    "docs/figures/downstream-validation.svg": "downstream-validation.svg",
})
TEMPLATE_FILES = (
    "experiment.yaml", "hydrology.yaml", "reservoirs.yaml", "agents.rule.yaml",
    "agents.llm.yaml", "models.yaml", "auditors.yaml", "information.yaml",
    "prompts/system.txt", "prompts/operator.txt", "extensions/user_registered_rule/__init__.py",
)
TEMPLATE_DOWNLOADS = {"templates/coupled/" + name: name for name in TEMPLATE_FILES}
MULTI_RESERVOIR_FILES = (
    "agents.llm.yaml", "agents.rule.yaml", "auditors.yaml", "experiment.llm.yaml",
    "experiment.yaml", "forcing.csv", "hydrology.yaml", "information.yaml",
    "model.yaml", "models.yaml", "reference_a.csv", "reference_b.csv",
    "reservoirs.yaml", "statistics_a.json", "statistics_b.json",
    "extensions/__init__.py", "knowledge/guidance.json", "prompts/operator.txt",
    "prompts/system.txt",
)
MULTI_RESERVOIR_DOWNLOADS = {
    f"examples/multiple_reservoirs/{name}": name for name in MULTI_RESERVOIR_FILES
}
MULTI_SHARED_RULES = ("examples/rules/hanasaki/__init__.py",)
PAGES = {
    "docs/index.md": "index.md",
    "docs/index.zh-TW.md": "index.zh-TW.md",
    "README.md": "repository.md",
    "README.zh-TW.md": "repository.zh-TW.md",
    "examples/fe_walter/README.md": "examples/fe_walter/README.md",
    "examples/fe_walter/README.zh-TW.md": "examples/fe_walter/README.zh-TW.md",
    "examples/fe_walter/operation/README.md": "examples/fe_walter/operation/README.md",
    "examples/fe_walter/completed_results/README.md": "examples/fe_walter/completed_results/README.md",
    "examples/fe_walter/operation/README.zh-TW.md": "examples/fe_walter/operation/README.zh-TW.md",
    "examples/fe_walter/hydrology.md": "examples/fe_walter/hydrology.md",
    "examples/fe_walter/configuration.md": "examples/fe_walter/configuration.md",
    "examples/fe_walter/annual/README.md": "examples/fe_walter/annual/README.md",
    "examples/fe_walter/coupled/README.md": "examples/fe_walter/coupled/README.md",
    "examples/fe_walter/annual/results.md": "examples/fe_walter/annual/results.md",
    "examples/fe_walter/annual/decision_2016_01_01.md": "examples/fe_walter/annual/decision_2016_01_01.md",
    "examples/fe_walter/hydrology.zh-TW.md": "examples/fe_walter/hydrology.zh-TW.md",
    "examples/fe_walter/coupling.md": "examples/fe_walter/coupling.md",
    "examples/fe_walter/coupling.zh-TW.md": "examples/fe_walter/coupling.zh-TW.md",
    "examples/fe_walter/results.md": "examples/fe_walter/results.md",
    "examples/fe_walter/results.zh-TW.md": "examples/fe_walter/results.zh-TW.md",
    "examples/fe_walter/downstream/README.md": "examples/fe_walter/downstream/README.md",
    "examples/fe_walter/downstream/README.zh-TW.md": "examples/fe_walter/downstream/README.zh-TW.md",
    "examples/fe_walter/downstream/validation.md": "examples/fe_walter/downstream/validation.md",
    "examples/fe_walter/downstream/validation.zh-TW.md": "examples/fe_walter/downstream/validation.zh-TW.md",
    "examples/fe_walter/results_history.md": "examples/fe_walter/results_history.md",
    "examples/fe_walter/results_history.zh-TW.md": "examples/fe_walter/results_history.zh-TW.md",
    "examples/fe_walter/engine_comparison.md": "examples/fe_walter/engine_comparison.md",
    "examples/fe_walter/prompt_review.md": "examples/fe_walter/prompt_review.md",
    **{f"examples/fe_walter/{method}/{name}": f"examples/fe_walter/{method}/{name}"
       for method in ("benchmark", "zero_shot", "dkp")
       for name in ("README.md", "README.zh-TW.md")},
    "examples/fe_walter/notebook.md": "tutorials/main.md",
    "tutorials/advanced.ipynb": "tutorials/advanced.ipynb",
    "archive/README.md": "archive/README.md",
    **{f"docs/{name}": f"docs/{name}" for name in (
        "README.md", "README.zh-TW.md", "LLM_MODULES.md", "LLM_MODULES.zh-TW.md",
        "USER_GUIDE.md", "USER_GUIDE.zh-TW.md", "HYDROLOGY_SETUP.md",
        "LIVE_READINESS.md", "auditor_plugins.md", "PROJECT_INVENTORY.md", "BUILDING.md",
        "GETTING_STARTED.md", "BUILD_SIMULATION.md", "BUILD_SIMULATION.zh-TW.md", "INFORMATION.md", "INFORMATION.zh-TW.md",
        "DAILY_WORKFLOW.md", "DAILY_EXAMPLES.md", "MODULE_INVENTORY.md", "VARIABLES_AND_UNITS.md", "DAILY_QA.md",
        "TIME_SCALES.md", "YAML_TIME_SCALES.md", "HOURLY_GWLF.md", "GWLF_GROUNDWATER.md",
        "CONFIGURATION.md", "MODEL_PROVIDERS.md", "MULTI_RESERVOIR.md", "INPUT_OUTPUT.md", "API_REFERENCE.md",
        "GLOBAL_SETTINGS.md", "TEMPLATES.md", "CASE_STUDIES.md",
        "PARAMETER_REFERENCE.md", "RESULTS_GUIDE.md", "REFERENCE.md", "RUNNING.md", "CODE_STRUCTURE.md", "WEATHER_INPUTS.md",
        "TROUBLESHOOTING.md", "RECORDS.md",
    )},
}
# Match the inner image in a linked badge before its enclosing Markdown link.
LINK = re.compile(r"(!?\[[^\[\]]*\]\()([^\s)]+)(\))")


def prepare(source: Path, *, source_ref: str = "main") -> None:
    """Keep manual pages local; link source/evidence to the private repository."""
    def rewrite(text: str, original: str, destination: str) -> str:
        def replace(match: re.Match) -> str:
            href = match[2]
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path:
                return match[0]
            target = ((ROOT / original).parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                raise ValueError(f"missing or escaping link in {original}: {href}")
            relative = target.relative_to(ROOT).as_posix()
            if relative in PAGES:
                import os
                value = Path(os.path.relpath(source / PAGES[relative], (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in FIGURE_DOWNLOADS:
                import os
                output = source / "_figure_downloads" / FIGURE_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in MAP_DOWNLOADS:
                import os
                output = source / "_map_downloads" / MAP_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in HYDROLOGY_DOWNLOADS:
                import os
                output = source / "_hydrology_downloads" / HYDROLOGY_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in ANNUAL_DOWNLOADS:
                import os
                output = source / "_annual_downloads" / ANNUAL_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in CONFIG_DOWNLOADS:
                import os
                output = source / "_config_downloads" / CONFIG_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in COMPLETED_DOWNLOADS:
                import os
                output = source / "_completed_downloads" / COMPLETED_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in YEAR_DOWNLOADS:
                import os
                output = source / "_completed_downloads" / YEAR_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in COMPARISON_DOWNLOADS:
                import os
                output = source / "_completed_downloads" / COMPARISON_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in TUTORIAL_DOWNLOADS:
                import os
                output = source / "_tutorial_downloads" / TUTORIAL_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in DAILY_DOWNLOADS:
                import os
                output = source / "_daily_downloads" / DAILY_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in DOWNSTREAM_DOWNLOADS:
                import os
                output = source / "_downstream_downloads" / DOWNSTREAM_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in TEMPLATE_DOWNLOADS:
                import os
                output = source / "_template_downloads" / TEMPLATE_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif relative.startswith("docs/_static/"):
                import os
                output = source / "_static" / target.relative_to(ROOT / "docs/_static")
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif not match[1].startswith("!") and relative in MULTI_RESERVOIR_DOWNLOADS:
                import os
                output = source / "_multiple_reservoir_downloads" / MULTI_RESERVOIR_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif match[1].startswith("!"):
                output = source / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target, output)
                import os
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            else:
                kind = "tree" if target.is_dir() else "blob"
                value = f"{REMOTE}/{kind}/{quote(source_ref, safe='')}/{relative}"
            if parsed.fragment:
                value += "#" + parsed.fragment
            return match[1] + value + match[3]
        return LINK.sub(replace, text)

    for original, destination in PAGES.items():
        target = source / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if original.endswith(".ipynb"):
            notebook = json.loads((ROOT / original).read_text(encoding="utf-8"))
            for cell in notebook["cells"]:
                if cell["cell_type"] == "markdown":
                    cell["source"] = rewrite("".join(cell["source"]), original, destination).splitlines(True)
            target.write_text(json.dumps(notebook, ensure_ascii=False), encoding="utf-8")
        else:
            text = rewrite((ROOT / original).read_text(encoding="utf-8"), original, destination)
            if original in {"README.md", "README.zh-TW.md"}:
                # Raw HTML images are not rewritten by MyST; reuse the local logo.
                text = text.replace(
                    'src="docs/figures/assets/branding/hydroopslm-logo.png"',
                    'src="_static/hydroopslm-logo.svg"',
                )
            target.write_text(text, encoding="utf-8")
    # Preserve old bookmarks without maintaining a second tutorial in Markdown.
    (source / "tutorials/fe_walter.md").write_text(
        "---\norphan: true\n---\n\n# F.E. Walter tutorial\n\n"
        "[Open the outputs and notebook guide](main.md).\n\n"
        "```{raw} html\n<meta http-equiv=\"refresh\" content=\"0; url=main.html\">\n```\n",
        encoding="utf-8",
    )
    # Keep a readable manual hierarchy; notebooks are also downloadable as original bytes.
    downloads = source / "_notebook_downloads"
    downloads.mkdir()
    for name in ("main", "advanced"):
        shutil.copyfile(ROOT / f"tutorials/{name}.ipynb", downloads / f"{name}.ipynb")
    figure_downloads = source / "_figure_downloads"
    figure_downloads.mkdir()
    for relative, name in FIGURE_DOWNLOADS.items():
        destination = figure_downloads / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    # Only the named map exports and editable project are downloadable; no service reads.
    map_downloads = source / "_map_downloads"
    map_downloads.mkdir()
    for relative, name in MAP_DOWNLOADS.items():
        shutil.copyfile(ROOT / relative, map_downloads / name)
    # Only these named, accepted hydrological inputs/evidence are published.
    hydrology_downloads = source / "_hydrology_downloads"
    hydrology_downloads.mkdir()
    for relative, name in HYDROLOGY_DOWNLOADS.items():
        shutil.copyfile(ROOT / relative, hydrology_downloads / name)
    # Publish only the selected annual teaching evidence, including the failed reply.
    annual_downloads = source / "_annual_downloads"
    annual_downloads.mkdir()
    for relative, name in ANNUAL_DOWNLOADS.items():
        shutil.copyfile(ROOT / relative, annual_downloads / name)
    config_downloads = source / "_config_downloads"
    config_downloads.mkdir()
    for relative, name in CONFIG_DOWNLOADS.items():
        shutil.copyfile(ROOT / relative, config_downloads / name)
        # Canonical files also support copyable literalinclude blocks in tutorials.
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    template_downloads = source / "_template_downloads"
    template_downloads.mkdir()
    for relative, name in TEMPLATE_DOWNLOADS.items():
        for target in (template_downloads / name, source / relative):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
    with zipfile.ZipFile(template_downloads / "coupled-configuration.zip", "w",
                         compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in (*TEMPLATE_FILES, "README.md"):
            bundle.write(ROOT / "templates/coupled" / name, arcname="coupled/" + name)
    completed_downloads = source / "_completed_downloads"
    completed_downloads.mkdir()
    for relative, name in COMPLETED_DOWNLOADS.items():
        shutil.copyfile(ROOT / relative, completed_downloads / name)
    # Keep current-year downloads distinct from the historical same-basename assets.
    # Canonical source copies support direct local references and source-byte checks.
    for relative, name in YEAR_DOWNLOADS.items():
        shutil.copyfile(ROOT / relative, completed_downloads / name)
        canonical = source / relative
        canonical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, canonical)
    # Keep new Daily fixtures and engineering records separate from accepted
    # historical teaching namespaces and preserve exact downloadable bytes.
    for relative, name in DAILY_DOWNLOADS.items():
        for target in (source / "_daily_downloads" / name, source / relative):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
    # Only these curated comparison assets are published; raw HTTP journals stay private.
    for relative, name in COMPARISON_DOWNLOADS.items():
        shutil.copyfile(ROOT / relative, completed_downloads / name)
        canonical = source / relative
        canonical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, canonical)
    # Publish only the current three-method teaching data and its two figures.
    tutorial_downloads = source / "_tutorial_downloads"
    tutorial_downloads.mkdir()
    for relative, name in TUTORIAL_DOWNLOADS.items():
        destination = tutorial_downloads / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
        canonical = source / relative
        canonical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, canonical)
    for relative, name in DOWNSTREAM_DOWNLOADS.items():
        download = source / "_downstream_downloads" / name
        download.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, download)
        canonical = source / relative
        canonical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, canonical)
    for name in ("llm_available_reply.txt", "llm_knowledge_reply.txt"):
        relative = "examples/fe_walter/coupled/outputs/2016/" + name
        shutil.copyfile(ROOT / relative, source / relative)
    # Publish one complete, explicit teaching bundle. Keep paths inside the bundle
    # so split YAML, prompts, provenance inputs and extension code remain runnable.
    multiple_downloads = source / "_multiple_reservoir_downloads"
    multiple_downloads.mkdir()
    archive = multiple_downloads / "hydroopslm-multiple-reservoirs.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative, name in MULTI_RESERVOIR_DOWNLOADS.items():
            item = ROOT / relative
            bundle.write(item, arcname=f"multiple_reservoirs/{name}")
            download = multiple_downloads / name
            download.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, download)
            canonical = source / relative
            canonical.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, canonical)
        # Shared user-rule modules keep their sibling location after extraction.
        # Never put ../ paths in an archive or flatten these imports into a core module.
        for relative in MULTI_SHARED_RULES:
            item = ROOT / relative
            bundle.write(item, arcname=Path(relative).relative_to('examples').as_posix())
            canonical = source / relative
            canonical.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, canonical)
    for name in ("llm_available_reply.txt", "llm_knowledge_reply.txt"):
        relative = "examples/fe_walter/coupled/outputs/" + name
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    # Publish selected original-byte case evidence for local viewing and downloads.
    case_downloads = source / "_case_downloads/dkp_2016_2020"
    case_downloads.mkdir(parents=True)
    # Explicit publication list: never sweep future raw logs or configuration into the public site.
    selected = ["plotted_daily.csv", "trajectory.csv", "annual_summary.csv", "source_manifest.json",
                *[f"{kind}_{day}.json" for kind in ("trace", "operation") for day in ("2020-05-02", "2020-06-15")]]
    selected += [f"figures/fe_walter_{figure}.{ext}" for figure in ("2016_2020_daily", "2020_detail", "audit_by_year") for ext in ("pdf", "svg")]
    for relative in selected:
        item = ROOT / "examples/fe_walter/reference_outputs/long_term_dkp" / relative
        shutil.copyfile(item, case_downloads / item.name)
    groups = {
        "Overview and installation": ["docs/README", "docs/GETTING_STARTED", "docs/DAILY_WORKFLOW"],
        "Configuration": ["docs/INPUT_OUTPUT", "docs/GLOBAL_SETTINGS", "docs/HYDROLOGY_SETUP",
                          "docs/BUILD_SIMULATION", "docs/CONFIGURATION", "docs/INFORMATION", "docs/RUNNING"],
        "Case studies": ["docs/CASE_STUDIES", "examples/fe_walter/README", "tutorials/main",
                         "examples/fe_walter/operation/README"],
        "Results": ["docs/RESULTS_GUIDE", "examples/fe_walter/completed_results/README", "examples/fe_walter/results"],
        "Troubleshooting": ["docs/TROUBLESHOOTING"],
        "API and reference": ["docs/API_REFERENCE", "docs/PARAMETER_REFERENCE", "docs/REFERENCE", "docs/USER_GUIDE",
                               "docs/DAILY_EXAMPLES", "docs/MODULE_INVENTORY", "docs/VARIABLES_AND_UNITS", "docs/DAILY_QA",
                               "docs/TIME_SCALES", "docs/YAML_TIME_SCALES", "docs/HOURLY_GWLF", "docs/GWLF_GROUNDWATER",
                              "docs/CODE_STRUCTURE", "docs/PROJECT_INVENTORY", "archive/README", "repository",
                              "docs/BUILDING", "docs/auditor_plugins", "docs/LIVE_READINESS", "docs/RECORDS",
                               "docs/TEMPLATES", "docs/WEATHER_INPUTS", "docs/MODEL_PROVIDERS", "docs/LLM_MODULES",
                              "examples/fe_walter/prompt_review",
                              "examples/fe_walter/engine_comparison", "examples/fe_walter/configuration", "examples/fe_walter/hydrology",
                              "examples/fe_walter/downstream/README",
                              "examples/fe_walter/downstream/validation",
                              "examples/fe_walter/coupled/README", "examples/fe_walter/coupling", "examples/fe_walter/annual/README",
                              *[f"examples/fe_walter/{method}/README" for method in ("benchmark", "zero_shot", "dkp")],
                              "examples/fe_walter/annual/decision_2016_01_01", "examples/fe_walter/annual/results",
                              "docs/MULTI_RESERVOIR", "tutorials/advanced"],
        "Historical research": ["examples/fe_walter/results_history"],
        "繁體中文": [path.rsplit(".", 1)[0] for path in PAGES.values()
                   if "zh-TW" in path],
    }
    with (source / "index.md").open("a", encoding="utf-8") as handle:
        for caption, entries in groups.items():
            handle.write(f"\n\n```{{toctree}}\n:hidden:\n:maxdepth: 1\n:caption: {caption}\n\n"
                         + "\n".join(entries) + "\n```\n")
    shutil.copyfile(ROOT / "docs/conf.py", source / "conf.py")
    shutil.copytree(ROOT / "docs/_static", source / "_static")
    # Reuse accepted identity assets without regenerating or changing their bytes.
    for size in (32, 64):
        shutil.copyfile(ROOT / f"docs/figures/assets/branding/logo-{size}.png",
                        source / f"_static/logo-{size}.png")
    shutil.copyfile(ROOT / "docs/figures/assets/branding/hydroopslm-logo.svg",
                    source / "_static/hydroopslm-logo.svg")
    shutil.copytree(ROOT / "docs/_templates", source / "_templates")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/docs")
    parser.add_argument("--source-ref", default="main", help="Git ref used for repository source links")
    args = parser.parse_args()
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="docs-source-", dir=build) as folder:
        source = Path(folder).resolve()
        assert source.is_relative_to(build.resolve())
        prepare(source, source_ref=args.source_ref)
        # Sphinx/MyST-NB reads saved MIME outputs; execution is disabled in conf.py.
        return subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going",
                               "-b", "html", str(source), str(args.output.resolve())], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
