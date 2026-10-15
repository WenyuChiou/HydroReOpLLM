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
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "https://github.com/WenyuChiou/HydroOpsLM"
MAP_DOWNLOADS = {
    **{f"docs/figures/fe-walter-catchment.{ext}": f"fe-walter-catchment.{ext}"
       for ext in ("png", "svg", "pdf")},
    "data/figures/manual_map/fe-walter-arcgis-source.zip": "fe-walter-arcgis-source.zip",
}
PAGES = {
    "docs/index.md": "index.md",
    "docs/index.zh-TW.md": "index.zh-TW.md",
    "README.md": "repository.md",
    "README.zh-TW.md": "repository.zh-TW.md",
    "examples/fe_walter/README.md": "examples/fe_walter/README.md",
    "examples/fe_walter/README.zh-TW.md": "examples/fe_walter/README.zh-TW.md",
    "examples/fe_walter/results.md": "examples/fe_walter/results.md",
    "examples/fe_walter/results.zh-TW.md": "examples/fe_walter/results.zh-TW.md",
    **{f"examples/fe_walter/{method}/{name}": f"examples/fe_walter/{method}/{name}"
       for method in ("benchmark", "zero_shot", "dkp")
       for name in ("README.md", "README.zh-TW.md")},
    "tutorials/README.md": "tutorials/README.md",
    "tutorials/README.zh-TW.md": "tutorials/README.zh-TW.md",
    "tutorials/main.ipynb": "tutorials/main.ipynb",
    "tutorials/advanced.ipynb": "tutorials/advanced.ipynb",
    "archive/README.md": "archive/README.md",
    "paper/technical_note.md": "paper/technical_note.md",
    **{f"docs/{name}": f"docs/{name}" for name in (
        "README.md", "README.zh-TW.md", "LLM_MODULES.md", "LLM_MODULES.zh-TW.md",
        "USER_GUIDE.md", "USER_GUIDE.zh-TW.md", "HYDROLOGY_SETUP.md",
        "LIVE_READINESS.md", "auditor_plugins.md", "PROJECT_INVENTORY.md", "BUILDING.md",
        "GETTING_STARTED.md", "BUILD_SIMULATION.md", "BUILD_SIMULATION.zh-TW.md", "FIRST_DECISION.md", "INFORMATION.md", "INFORMATION.zh-TW.md",
        "PARAMETER_REFERENCE.md", "RESULTS_GUIDE.md", "REFERENCE.md", "RUNNING.md",
    )},
}
# Match the inner image in a linked badge before its enclosing Markdown link.
LINK = re.compile(r"(!?\[[^\[\]]*\]\()([^\s)]+)(\))")


def prepare(source: Path) -> None:
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
            elif not match[1].startswith("!") and relative in MAP_DOWNLOADS:
                import os
                output = source / "_map_downloads" / MAP_DOWNLOADS[relative]
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            elif match[1].startswith("!"):
                output = source / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target, output)
                import os
                value = Path(os.path.relpath(output, (source / destination).parent)).as_posix()
            else:
                kind = "tree" if target.is_dir() else "blob"
                value = f"{REMOTE}/{kind}/main/{relative}"
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
    # Keep a readable manual hierarchy; notebooks are also downloadable as original bytes.
    downloads = source / "_notebook_downloads"
    downloads.mkdir()
    for name in ("main", "advanced"):
        shutil.copyfile(ROOT / f"tutorials/{name}.ipynb", downloads / f"{name}.ipynb")
    # Only the named map exports and editable project are downloadable; no service reads.
    map_downloads = source / "_map_downloads"
    map_downloads.mkdir()
    for relative, name in MAP_DOWNLOADS.items():
        shutil.copyfile(ROOT / relative, map_downloads / name)
    # Publish selected original-byte case evidence for local viewing and downloads.
    case_downloads = source / "_case_downloads/dkp_2016_2020"
    case_downloads.mkdir(parents=True)
    # Explicit publication list: never sweep future raw logs or configuration into the public site.
    selected = ["plotted_daily.csv", "trajectory.csv", "annual_summary.csv", "source_manifest.json",
                *[f"{kind}_{day}.json" for kind in ("trace", "operation") for day in ("2020-05-02", "2020-06-15")]]
    selected += [f"figures/fe_walter_{figure}.{ext}" for figure in ("2016_2020_daily", "2020_detail", "audit_by_year") for ext in ("pdf", "svg")]
    for relative in selected:
        item = ROOT / "results/fe_walter_dkp_2016_2020" / relative
        shutil.copyfile(item, case_downloads / item.name)
    groups = {
        "Overview": ["docs/README"],
        "Build a simulation": ["docs/GETTING_STARTED", "docs/BUILD_SIMULATION", "docs/USER_GUIDE", "docs/INFORMATION", "docs/LLM_MODULES"],
        "FE Walter case study": ["examples/fe_walter/README", *[f"examples/fe_walter/{method}/README" for method in ("benchmark", "zero_shot", "dkp")], "examples/fe_walter/results"],
        "Further configuration": ["tutorials/advanced", "docs/RESULTS_GUIDE", "docs/RUNNING"],
        "Reference": ["docs/PARAMETER_REFERENCE", "docs/REFERENCE", "docs/FIRST_DECISION", "docs/HYDROLOGY_SETUP",
                      "tutorials/README", "tutorials/main", "paper/technical_note",
                                    "docs/PROJECT_INVENTORY", "archive/README", "repository",
                                    "docs/BUILDING", "docs/auditor_plugins", "docs/LIVE_READINESS"],
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
    args = parser.parse_args()
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="docs-source-", dir=build) as folder:
        source = Path(folder).resolve()
        assert source.is_relative_to(build.resolve())
        prepare(source)
        # Sphinx/MyST-NB reads saved MIME outputs; execution is disabled in conf.py.
        return subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going",
                               "-b", "html", str(source), str(args.output.resolve())], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
