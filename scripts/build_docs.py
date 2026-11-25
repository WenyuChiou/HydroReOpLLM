"""Build the public documentation from an explicit safe-file allowlist."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from mkdocs.commands.build import build
from mkdocs.config import load_config


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
REPOSITORY_BLOB = "https://github.com/WenyuChiou/HydroReOpLLM/blob/main/"

# Destination paths are site source paths. Only invented, public teaching
# material is included; scientific outputs, working notes, and manuscripts are
# excluded by construction.
SAFE_FILES = {
    "docs/README.md": "index.md",
    "docs/assets/branding/cover.png": "assets/branding/cover.png",
    "docs/assets/branding/logo.svg": "assets/branding/logo.svg",
    "docs/assets/branding/favicon.ico": "img/favicon.ico",
    "docs/assets/branding/docs-badge-en.svg": "assets/branding/docs-badge-en.svg",
    "docs/assets/branding/docs-badge-zh-TW.svg": "assets/branding/docs-badge-zh-TW.svg",
    "docs/assets/branding/branding.css": "assets/branding/branding.css",
    "docs/BUILD_SIMULATION.zh-TW.md": "BUILD_SIMULATION.zh-TW.md",
    "docs/LLM_MODULES.zh-TW.md": "LLM_MODULES.zh-TW.md",
    "docs/INFORMATION.zh-TW.md": "INFORMATION.zh-TW.md",
    "docs/RESULTS_GUIDE.zh-TW.md": "RESULTS_GUIDE.zh-TW.md",
    "docs/README.zh-TW.md": "zh-TW.md",
    "docs/GETTING_STARTED.md": "GETTING_STARTED.md",
    "docs/CONFIGURATION.md": "CONFIGURATION.md",
    "docs/INFORMATION.md": "INFORMATION.md",
    "docs/RESULTS_GUIDE.md": "RESULTS_GUIDE.md",
    "docs/assets/simulation-stages.png": "assets/simulation-stages.png",
    "docs/RUNNING.md": "RUNNING.md",
    "docs/MODEL_PROVIDERS.md": "MODEL_PROVIDERS.md",
    "docs/MULTI_RESERVOIR.md": "MULTI_RESERVOIR.md",
    "docs/TIME_SCALES.md": "TIME_SCALES.md",
    "docs/HYDROLOGY_SETUP.md": "HYDROLOGY_SETUP.md",
    "docs/HOURLY_GWLF.md": "HOURLY_GWLF.md",
    "docs/TROUBLESHOOTING.md": "TROUBLESHOOTING.md",
    "tutorials/README.md": "tutorials/index.md",
    "examples/daily_offline/README.md": "examples/daily_offline/index.md",
    "examples/multiple_reservoirs/README.md": "examples/multiple_reservoirs/index.md",
    "examples/time_scales/README.md": "examples/time_scales/index.md",
    "examples/rules/mosart_urban/README.md": "examples/rules/mosart_urban/index.md",
    "templates/prepared/README.md": "starters/prepared/index.md",
    "templates/coupled/README.md": "starters/coupled/index.md",
    "templates/coupled/hydrology.yaml": "assets/templates/coupled/hydrology.yaml",
    "templates/coupled/models.yaml": "assets/templates/coupled/models.yaml",
}

MARKDOWN_LINK = re.compile(r"(\[[^\]]*\]\()([^)\s]+)([^)]*\))")


def _repo_path(source: str, target: str) -> str:
    return os.path.normpath(str(PurePosixPath(source).parent / target)).replace("\\", "/")


def _rewrite_links(text: str, source: str, destination: str) -> str:
    def replace(match: re.Match[str]) -> str:
        raw_target = match.group(2)
        parsed = urlsplit(raw_target)
        if parsed.scheme or parsed.netloc or raw_target.startswith("#"):
            return match.group(0)

        resolved = _repo_path(source, parsed.path)
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        if resolved in SAFE_FILES:
            staged_target = SAFE_FILES[resolved]
            relative = os.path.relpath(
                staged_target, PurePosixPath(destination).parent
            ).replace("\\", "/")
            target = relative + fragment
        elif (ROOT / resolved).is_file():
            target = REPOSITORY_BLOB + resolved + fragment
        else:
            target = raw_target
        return match.group(1) + target + match.group(3)

    return MARKDOWN_LINK.sub(replace, text)


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.anchors.add(values["id"] or "")
        if tag == "img" and values.get("src"):
            self.hrefs.append(values["src"] or "")
        if tag in {"a", "link"} and values.get("href"):
            self.hrefs.append(values["href"] or "")


def _validate_site() -> None:
    parsed_pages: dict[Path, _LinkCollector] = {}
    for page in SITE.rglob("*.html"):
        collector = _LinkCollector()
        collector.feed(page.read_text(encoding="utf-8"))
        parsed_pages[page.resolve()] = collector

    failures: list[str] = []
    for page, collector in parsed_pages.items():
        for href in collector.hrefs:
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or href.startswith(("mailto:", "tel:")):
                continue
            target = (page.parent / unquote(parsed.path)).resolve() if parsed.path else page
            if not target.is_file():
                failures.append(f"{page.relative_to(SITE)} -> missing {href}")
                continue
            if parsed.fragment and target.suffix.lower() == ".html":
                target_page = parsed_pages.get(target)
                if target_page is None or unquote(parsed.fragment) not in target_page.anchors:
                    failures.append(f"{page.relative_to(SITE)} -> missing anchor {href}")
    if failures:
        raise RuntimeError("Broken generated links:\n" + "\n".join(failures))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="hydroreopllm-docs-") as temporary:
        temporary_root = Path(temporary)
        stage = temporary_root / "input"
        for source, destination in SAFE_FILES.items():
            source_path = ROOT / source
            if not source_path.is_file():
                raise FileNotFoundError(f"allowlisted documentation file is missing: {source}")
            destination_path = stage / destination
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if source_path.suffix.lower() == ".md":
                text = source_path.read_text(encoding="utf-8")
                destination_path.write_text(
                    _rewrite_links(text, source, destination), encoding="utf-8"
                )
            else:
                shutil.copyfile(source_path, destination_path)

        config = load_config(
            config_file=str(ROOT / "mkdocs.yml"), docs_dir=str(stage), site_dir=str(SITE)
        )
        build(config)
        # MkDocs' optional 404 page uses site-root navigation, which is wrong for
        # both file:// use and a GitHub Pages project subpath. Pages supplies its
        # own 404 response; omit this generated page from the portable artifact.
        (SITE / "404.html").unlink(missing_ok=True)
        _validate_site()
        print(f"Built and link-checked documentation: {SITE / 'index.html'}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
