"""Build the public documentation from an explicit safe-file allowlist."""

from __future__ import annotations

import html
import os
import re
import shutil
import tempfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from babel.support import Translations
from mkdocs.commands.build import build
from mkdocs.config import load_config
from mkdocs.plugins import BasePlugin


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
REPOSITORY_BLOB = "https://github.com/WenyuChiou/HydroReOpLLM/blob/main/"
PUBLIC_SITE = "https://wenyuchiou.github.io/HydroReOpLLM/"

# Destination paths are site source paths. Only invented, public teaching
# material is included; scientific outputs, working notes, and manuscripts are
# excluded by construction.
ENGLISH_FILES = {
    "docs/README.md": "index.md",
    "docs/assets/branding/cover.png": "assets/branding/cover.png",
    "docs/assets/branding/logo.svg": "assets/branding/logo.svg",
    "docs/assets/branding/favicon.ico": "img/favicon.ico",
    "docs/assets/branding/docs-badge-en.svg": "assets/branding/docs-badge-en.svg",
    "docs/assets/branding/docs-badge-zh-TW.svg": "assets/branding/docs-badge-zh-TW.svg",
    "docs/assets/branding/branding.css": "assets/branding/branding.css",
    "docs/GETTING_STARTED.md": "GETTING_STARTED.md",
    "docs/CONFIGURATION.md": "CONFIGURATION.md",
    "docs/INFORMATION.md": "INFORMATION.md",
    "docs/RESULTS_GUIDE.md": "RESULTS_GUIDE.md",
    "docs/assets/simulation-stages.png": "assets/simulation-stages.png",
    "docs/assets/copy-code.js": "assets/copy-code.js",
    "docs/assets/search-zh-TW.js": "assets/search-zh-TW.js",
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

# Keep the original public URLs for the homepage and two renamed chapters.
ZH_NAMES = {
    "MULTI_RESERVOIR.md": "BUILD_SIMULATION.zh-TW.md",
    "MODEL_PROVIDERS.md": "LLM_MODULES.zh-TW.md",
}


def _translated(path: str) -> str:
    file = PurePosixPath(path)
    if path == "index.md":
        return "zh-TW.md"
    return str(file.with_name(ZH_NAMES.get(file.name, f"{file.stem}.zh-TW.md")))


SAFE_FILES = dict(ENGLISH_FILES)
CHAPTER_PAIRS = {}
for source, destination in ENGLISH_FILES.items():
    if source.endswith(".md"):
        translated = _translated(destination)
        SAFE_FILES[_translated(source)] = translated
        CHAPTER_PAIRS[destination] = translated

PUBLISHED_CHAPTERS = {
    PUBLIC_SITE + path.removesuffix(".md") + ".html": path
    for pair in CHAPTER_PAIRS.items()
    for path in pair
}
MARKDOWN_LINK = re.compile(r"(\[[^\]]*\]\()([^)\s]+)([^)]*\))")


def _repo_path(source: str, target: str) -> str:
    return os.path.normpath(str(PurePosixPath(source).parent / target)).replace("\\", "/")


def _rewrite_links(text: str, source: str, destination: str) -> str:
    def replace(match: re.Match[str]) -> str:
        raw_target = match.group(2)
        parsed = urlsplit(raw_target)
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        if parsed.scheme or parsed.netloc:
            # Source READMEs also ship with the wheel, where hosted links are needed.
            staged_target = PUBLISHED_CHAPTERS.get(raw_target.split("#", 1)[0])
            if staged_target is None:
                return match.group(0)
        elif raw_target.startswith("#"):
            return match.group(0)
        else:
            resolved = _repo_path(source, parsed.path)
            staged_target = SAFE_FILES.get(resolved)
            if staged_target is None:
                target = REPOSITORY_BLOB + resolved + fragment if (ROOT / resolved).is_file() else raw_target
                return match.group(1) + target + match.group(3)
        relative = os.path.relpath(
            staged_target, PurePosixPath(destination).parent
        ).replace("\\", "/")
        return match.group(1) + relative + fragment + match.group(3)

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
        if tag in {"img", "script"} and values.get("src"):
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


class BilingualManual(BasePlugin):
    """Pair the two navigation trees and render each page in its reader's language."""

    def on_nav(self, nav, *, config, files):
        english, chinese = nav.items
        self.alternates = {}

        def pair(left, right):
            if left.is_section and right.is_section:
                for first, second in zip(left.children, right.children, strict=True):
                    pair(first, second)
                return
            if left.is_page and right.is_page:
                en, zh = left.file.src_uri, right.file.src_uri
                if CHAPTER_PAIRS.get(en) == zh and en not in self.alternates:
                    self.alternates[en] = right
                    self.alternates[zh] = left
                    return
            raise ValueError(f"Unpaired or duplicate manual chapters: {left.title} / {right.title}")

        pair(english, chinese)
        if len(self.alternates) != 2 * len(CHAPTER_PAIRS):
            raise ValueError("Every allowlisted manual chapter must appear once in each language")
        locales = next(
            Path(d) / "locales" for d in config.theme.dirs
            if (Path(d) / "locales/zh_TW/LC_MESSAGES/messages.mo").is_file()
        )
        self.translations = Translations.load(str(locales), ["zh_TW"])
        return nav

    def on_page_content(self, page_html, *, page, config, files):
        if not (page.toc and page.toc.items and page.toc.items[0].children):
            return page_html
        chinese = page.file.src_uri.endswith("zh-TW.md")
        label = "本頁段落" if chinese else "In this chapter"
        links = "".join(
            f'<a href="{html.escape(heading.url, quote=True)}">{html.escape(heading.title)}</a>'
            for heading in page.toc.items[0].children
        )
        toc_block = f'<details class="on-this-page"><summary>{label}</summary>{links}</details>'
        if "</h1>" in page_html:
            return page_html.replace("</h1>", f"</h1>\n{toc_block}", 1)
        return toc_block + "\n" + page_html

    def on_page_context(self, context, *, page, config, nav):
        source = page.file.src_uri
        chinese = source.endswith("zh-TW.md")
        context.update(
            chinese=chinese,
            english_url=self.alternates[source].url if chinese else page.url,
            chinese_url=page.url if chinese else self.alternates[source].url,
            chapters=nav.items[1 if chinese else 0].children,
        )
        if chinese:
            # Keep the shared build config immutable while the theme renders this page.
            context["config"] = {
                **config,
                "theme": {**config.theme, "locale": "zh-Hant"},
                "extra_javascript": [
                    "assets/search-zh-TW.js" if str(script) == "search/main.js" else script
                    for script in config.extra_javascript
                ],
            }
            context["gettext"] = self.translations.gettext
            context["ngettext"] = self.translations.ngettext
        return context


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
        config.plugins["bilingual-manual"] = BilingualManual()
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
