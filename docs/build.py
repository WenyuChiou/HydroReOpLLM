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
REMOTE = "https://github.com/WenyuChiou/LLM_reservoir_agent"
PAGES = {
    "README.md": "index.md",
    "README.zh-TW.md": "index.zh-TW.md",
    "examples/fe_walter/README.md": "examples/fe_walter/README.md",
    "examples/fe_walter/README.zh-TW.md": "examples/fe_walter/README.zh-TW.md",
    "tutorials/README.md": "tutorials/README.md",
    "tutorials/README.zh-TW.md": "tutorials/README.zh-TW.md",
    "tutorials/main.ipynb": "tutorials/main.ipynb",
    "tutorials/advanced.ipynb": "tutorials/advanced.ipynb",
    "archive/README.md": "archive/README.md",
    **{f"docs/{name}": f"docs/{name}" for name in (
        "README.md", "README.zh-TW.md", "LLM_MODULES.md", "LLM_MODULES.zh-TW.md",
        "USER_GUIDE.md", "USER_GUIDE.zh-TW.md", "HYDROLOGY_SETUP.md",
        "LIVE_READINESS.md", "auditor_plugins.md", "PROJECT_INVENTORY.md", "BUILDING.md",
    )},
}
LINK = re.compile(r"(!?\[[^\]]*\]\()([^\s)]+)(\))")


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
            target.write_text(rewrite((ROOT / original).read_text(encoding="utf-8"), original, destination), encoding="utf-8")
    entries = [path.rsplit(".", 1)[0] for path in PAGES.values() if path != "index.md"]
    with (source / "index.md").open("a", encoding="utf-8") as handle:
        handle.write("\n\n```{toctree}\n:hidden:\n\n" + "\n".join(entries) + "\n```\n")
    shutil.copyfile(ROOT / "docs/conf.py", source / "conf.py")
    shutil.copytree(ROOT / "docs/_static", source / "_static")


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
