"""Keep private execution artifacts out of source and the file index accurate."""

from pathlib import Path
import hashlib
import json
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def source_paths():
    """Return maintained files, including a developer's pending source additions."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True,
    )
    return sorted({name for name in result.stdout.decode("utf-8").split("\0")
                   if name and (ROOT / name).is_file()})


def test_private_execution_and_model_artifacts_are_not_source():
    forbidden_parts = {".ai", ".coord", ".codebase-memory", "_qa", "__pycache__",
                       ".pytest_cache", ".ruff_cache", ".mypy_cache", "node_modules",
                       "paper", "papers", "manuscript", "manuscripts", "paper_runs"}
    protected_prefixes = (
        "data/figures/manual_map/",
        "docs/results/fe_walter/completed/",
        "docs/results/fe_walter/hydrology/climate/",
    )
    protected_files = {
        "docs/figures/FIGURE1.md",
        "docs/figures/fe-walter-catchment.png",
        "docs/figures/hydrocnhs-coupling-framework-en.png",
    }
    invalid = []
    for name in source_paths():
        p = Path(name)
        normalized = p.as_posix()
        if ({part.lower() for part in p.parts}.intersection(forbidden_parts)
                or any(part.startswith(".venv") for part in p.parts)
                or p.name.startswith(".env")
                or p.suffix.lower() in {".docx", ".tex", ".log", ".tmp", ".bkp", ".bak",
                                        ".safetensors", ".gguf"}
                or normalized in protected_files
                or normalized.startswith(protected_prefixes)
                or name.startswith(("runs/", "outputs/", "docs/plans/"))):
            invalid.append(name)
    assert invalid == []


def test_private_research_paths_are_ignored_before_they_can_be_added():
    representatives = (
        "paper/draft.pdf",
        "manuscripts/supplement.docx",
        "paper_runs/run-01/decisions.jsonl",
        "draft.tex",
        "docs/results/fe_walter/completed/result.csv",
        "docs/results/fe_walter/hydrology/climate/figure.png",
        "docs/figures/hydrocnhs-coupling-framework-en.png",
        "docs/figures/fe-walter-catchment.png",
        "data/figures/manual_map/source.zip",
    )
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--", *representatives],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    ignored = set(result.stdout.splitlines())
    assert set(representatives) <= ignored


def test_complete_file_index_matches_maintained_source():
    index = (ROOT / "docs/FILE_INDEX.txt").read_text(encoding="utf-8").splitlines()
    assert index == source_paths()


def test_module_inventory_current_hashes_match_source_and_markdown():
    inventory = json.loads((ROOT / "docs/qa/module-inventory.json").read_text(encoding="utf-8"))
    markdown = (ROOT / "docs/MODULE_INVENTORY.md").read_text(encoding="utf-8")
    displayed = dict(re.findall(r"\[Source\]\(\.\./(src/[^)]+)\) · SHA256 `([a-f0-9]{64})`", markdown))
    expected = {item["path"]: item["sha256"] for item in inventory["modules"]}
    assert displayed == expected
    assert {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in expected} == expected
