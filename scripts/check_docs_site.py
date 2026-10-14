"""Validate a static manual before publication; never execute a notebook or model."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    """Collect local navigation and image references from rendered HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        key = "href" if tag == "a" else "src" if tag == "img" else None
        if key and values.get(key):
            self.references.append(values[key])


def validate(site: Path) -> dict[str, int]:
    """Reject missing/escaping targets and modified original notebook downloads."""
    site = site.resolve()
    if not (site / "index.html").is_file():
        raise ValueError(f"Missing site entry: {site / 'index.html'}")
    pages: dict[Path, Page] = {}
    for file in site.rglob("*"):
        if file.is_symlink():
            raise ValueError(f"Pages artifact must not contain symlinks: {file}")
        if file.suffix == ".html" and file.is_file():
            page = Page()
            page.feed(file.read_text(encoding="utf-8"))
            pages[file.resolve()] = page
    count = 0
    for file, page in pages.items():
        for href in page.references:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                continue  # External sources are not part of this static artifact.
            target = (file.parent / unquote(url.path)).resolve() if url.path else file
            if not target.is_relative_to(site) or not target.exists():
                raise ValueError(f"Missing or escaping target in {file}: {href}")
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError(f"Missing HTML anchor in {file}: {href}")
            count += 1
    downloads = list((site / "_downloads").rglob("*.ipynb"))
    if len(downloads) != 2:
        raise ValueError(f"Expected two original notebook downloads, found {len(downloads)}")
    root = Path(__file__).resolve().parents[1]
    for name in ("main.ipynb", "advanced.ipynb"):
        matches = [file for file in downloads if file.name == name]
        if len(matches) != 1 or matches[0].read_bytes() != (root / "tutorials" / name).read_bytes():
            raise ValueError(f"Notebook download differs from committed source: {name}")
    return {"html_pages": len(pages), "local_references": count, "notebook_downloads": 2}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.site)))


if __name__ == "__main__":
    main()
