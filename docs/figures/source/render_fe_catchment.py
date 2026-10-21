"""Export the F. E. Walter manual map from its portable ArcGIS Pro package."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

def _export_project(project_file: Path, root: Path, output: Path, resolution: int) -> None:
    """Export in a short-lived ArcPy process so Windows releases layer locks."""
    import arcpy

    project = arcpy.mp.ArcGISProject(str(project_file))
    layouts = project.listLayouts()
    if len(layouts) != 1:
        raise RuntimeError(f"expected one layout, found {len(layouts)}")
    for map_layout in layouts:
        for picture in map_layout.listElements("PICTURE_ELEMENT"):
            source = Path(picture.sourceImage)
            if not source.is_absolute():
                source = (project_file.parent / source).resolve()
            if not source.is_relative_to(root) or not source.is_file():
                raise RuntimeError(f"picture source outside package: {source}")
            picture.sourceImage = str(source)
    broken = [
        layer.longName
        for map_obj in project.listMaps()
        for layer in map_obj.listLayers()
        if layer.isBroken
    ]
    if broken:
        raise RuntimeError(f"broken packaged layers: {broken}")
    output.parent.mkdir(parents=True, exist_ok=True)
    layout = layouts[0]
    layout.exportToPNG(str(output.with_suffix(".png")), resolution=resolution)
    layout.exportToSVG(
        str(output.with_suffix(".svg")), resolution=resolution,
        embed_fonts=True, convert_markers=False,
    )
    layout.exportToPDF(
        str(output.with_suffix(".pdf")), resolution=resolution,
        image_quality="BEST", embed_fonts=True,
    )


def export_map(package: Path, output: Path, resolution: int) -> None:
    """Extract, export, then clean up after the ArcPy child releases its locks."""
    if not package.is_file():
        raise FileNotFoundError(f"ArcGIS source package not found: {package}")
    with tempfile.TemporaryDirectory(prefix="fe-walter-arcgis-") as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(package) as archive:
            archive.extractall(extracted)
        projects = sorted(extracted.rglob("*.aprx"))
        if len(projects) != 1:
            raise RuntimeError(f"expected one packaged APRX, found {len(projects)}")
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()),
             "--project", str(projects[0]), "--output", str(output),
             "--resolution", str(resolution)],
            check=True,
            cwd=projects[0].parent,
        )


def main() -> None:
    repository = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=repository / "data/figures/manual_map/fe-walter-arcgis-source.zip",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repository / "docs/figures/fe-walter-catchment",
    )
    parser.add_argument("--resolution", type=int, default=240)
    parser.add_argument("--project", type=Path, help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.project is not None:
        project_file = arguments.project.resolve()
        _export_project(project_file, project_file.parent.parent,
                        arguments.output.resolve(), arguments.resolution)
        return
    export_map(
        arguments.package.resolve(),
        arguments.output.resolve(),
        arguments.resolution,
    )


if __name__ == "__main__":
    main()
