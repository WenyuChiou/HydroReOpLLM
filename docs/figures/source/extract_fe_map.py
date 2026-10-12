"""Export the formal FE Walter GIS as projected, unsimplified plotting data.

Requires Shapely, PyProj, and PyYAML. The GeoPackage is opened read-only.
The formal result layout supplies adjacent manifests/model and the project
config; --config supports another location. No input coordinates are invented.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import struct

import pyproj
import shapely
from shapely import wkb
from shapely.geometry import Point, box, mapping
from shapely.ops import unary_union
import yaml


EXPECTED_UNITS = {
    "FEW-D-01", "FEW-D-02", "FEW-X-01", "FEW-X-02", "FEW-X-03",
    "FEW-R-01", "FEW-R-02",
}
EXPECTED_BRANCH_COUNTS = {"donor": 2, "diagnostic": 3, "residual": 2}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_gpkg(blob: bytes):
    """Remove the GeoPackage binary header and decode standard WKB."""
    if blob[:2] != b"GP" or blob[2] != 0:
        raise ValueError("Unsupported GeoPackage geometry header")
    flags = blob[3]
    if flags & 0x30:
        raise ValueError("Empty or extended GeoPackage geometry is unsupported")
    envelope = (flags >> 1) & 7
    if envelope not in {0, 1, 2, 3, 4}:
        raise ValueError("Invalid GeoPackage envelope code")
    endian = "<" if flags & 1 else ">"
    if struct.unpack_from(endian + "i", blob, 4)[0] != 5070:
        raise ValueError("All exported geometry must be EPSG:5070")
    offset = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[envelope]
    geometry = wkb.loads(blob[offset:])
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("Empty or invalid source geometry")
    return geometry


def records(db, table: str, where: str = "", parameters: tuple = ()):
    # Tables/clauses are internal constants, never CLI values.
    sql = "SELECT * FROM " + table + (" WHERE " + where if where else "")
    result = []
    for row in db.execute(sql + " ORDER BY fid", parameters):
        properties = {key: row[key] for key in row.keys()
                      if key not in {"geom", "source_levelpaths"}}
        result.append((properties, decode_gpkg(row["geom"])))
    return result


def feature(properties: dict, geometry, source_layer: str) -> dict:
    return {
        "type": "Feature",
        "properties": {**properties, "source_layer": source_layer},
        "geometry": mapping(geometry),
    }


def point_candidates(geometry) -> list:
    if geometry.geom_type == "Point":
        return [geometry]
    if geometry.geom_type == "LineString":
        return [Point(geometry.coords[0]), Point(geometry.coords[-1])]
    if hasattr(geometry, "geoms"):
        return [point for child in geometry.geoms
                for point in point_candidates(child)]
    return []


def export(source: Path, output: Path, config_path: Path | None) -> dict:
    pyproj.network.set_network_enabled(False)
    source = source.resolve(strict=True)
    source_hash = sha256(source)
    result_root = source.parent.parent
    project_root = result_root.parents[2]
    config_path = (config_path or project_root / "configs/four_reservoir_semidistributed.json").resolve()
    geometry_manifest_path = result_root / "sources/geometry_manifest.json"
    gis_manifest_path = source.parent / "manifest.json"
    model_path = result_root / "models/fe_walter.yaml"
    source_paths = {
        "geopackage": source,
        "geometry_manifest": geometry_manifest_path,
        "gis_manifest": gis_manifest_path,
        "model": model_path,
        "reservoir_config": config_path,
        "formal_dam_map": project_root / "scripts/render_drb_four_reservoir_study_map.py",
        "formal_inlet_map": project_root / "scripts/render_four_reservoir_upstream_map.py",
    }
    provenance = {}
    for name, path in source_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Required provenance input missing: {path}")
        try:
            resource = path.relative_to(project_root).as_posix()
        except ValueError:
            resource = path.name
        provenance[name] = {"resource": resource, "sha256": sha256(path),
                            "bytes": path.stat().st_size}
    manifest = json.loads(geometry_manifest_path.read_text(encoding="utf-8"))
    gis_manifest = json.loads(gis_manifest_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    declared = set(model["WaterSystem"]["Outlets"]) - {"__AGGREGATION_OUTLET__"}
    aggregation = model["Routing"]["__AGGREGATION_OUTLET__"]
    routed = set(aggregation) - {"__AGGREGATION_OUTLET__"}
    if declared != EXPECTED_UNITS or routed != EXPECTED_UNITS:
        raise ValueError("Formal model outlets/aggregation differ from seven FE units")
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        units = records(db, "model_units", "reservoir = ?", ("fe_walter",))
        ids = [properties["subbasin_id"] for properties, _ in units]
        branch_counts = dict(Counter(properties["branch"] for properties, _ in units))
        if len(units) != 7 or set(ids) != EXPECTED_UNITS or branch_counts != EXPECTED_BRANCH_COUNTS:
            raise ValueError("Unexpected FE Walter identifiers or branch counts")
        waterbodies = records(db, "reservoirs", "reservoir = ?", ("fe_walter",))
        if len(waterbodies) != 1:
            raise ValueError("Expected exactly one FE Walter waterbody")
        gauges = records(db, "usgs_gauges", "usgs_id IN (?, ?)", ("01447500", "01447720"))
        if {properties["usgs_id"] for properties, _ in gauges} != {"01447500", "01447720"}:
            raise ValueError("Required FE gauges are absent")
        basins = records(db, "upstream_basins", "reservoir = ?", ("fe_walter",))
        boundary = records(db, "delaware_river_basin")
        if len(boundary) != 1:
            raise ValueError("Expected one Delaware River Basin inset boundary")
        units_union = unary_union([geometry for _, geometry in units])
        # Select complete reaches that intersect the domain bounds, with 1.5 km
        # margin. Rendering can clip to these bounds without modifying geometry.
        left, bottom, right, top = units_union.bounds
        viewport = [left - 1500, bottom - 1500, right + 1500, top + 1500]
        view_box = box(*viewport)
        river_rows = records(db, "river_network")
        rivers = [(properties, geometry) for properties, geometry in river_rows
                  if geometry.intersects(view_box)]
        crs_wkt = db.execute("SELECT definition FROM gpkg_spatial_ref_sys WHERE srs_id = 5070").fetchone()[0]
    forward = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
    reverse = pyproj.Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)
    lon_lat = config["reservoirs"]["fe_walter"]["reservoir_outlet"]
    outlet = Point(*forward.transform(*lon_lat))
    points = [feature({
        "point_id": "FE_WALTER_RECORDED_OUTLET", "role": "dam / reservoir outlet",
        "provenance_kind": "formal_project_recorded_point",
        "source_record": "reservoir_config#/reservoirs/fe_walter/reservoir_outlet",
        "source_coordinates_epsg4326": lon_lat,
        "external_point_record_provenance": "unresolved: config does not cite a primary dam survey or inventory record",
        "source_map_usage": "formal render_drb_four_reservoir_study_map.py assigns this reservoir_outlet point role dam",
    }, outlet, "reservoir_config")]
    named = [(properties, geometry) for properties, geometry in rivers
             if properties["gnis_name"] == "Lehigh River"]
    if not named:
        raise ValueError("Lehigh River geometry absent from selected reaches")
    lake = waterbodies[0][1]
    candidates = point_candidates(unary_union([geometry for _, geometry in named]).intersection(lake.boundary))
    if not candidates:
        raise ValueError("Lehigh River does not intersect the recorded reservoir boundary")
    inlet = max(candidates, key=lambda point: point.distance(outlet))
    points.append(feature({
        "point_id": "FE_WALTER_MAIN_RIVER_INLET", "role": "main river inlet",
        "provenance_kind": "derived_from_source_geometry",
        "method": "Lehigh River union intersection with waterbody boundary; choose crossing farthest from recorded outlet (formal upstream map method)",
        "intersection_candidate_count": len(candidates),
        "supporting_nhdplusids": [properties["nhdplusid"] for properties, geometry in named
                                  if geometry.distance(inlet) < 0.001],
        "coordinates_epsg4326_derived": list(reverse.transform(inlet.x, inlet.y)),
        "surveyed_inlet_record": "unresolved; this is a geometry-derived boundary crossing",
    }, inlet, "river_network+reservoirs"))
    layers = {
        "model_units": [feature(properties, geometry, "model_units") for properties, geometry in units],
        "upstream_basins": [feature(properties, geometry, "upstream_basins") for properties, geometry in basins],
        "reservoirs": [feature(properties, geometry, "reservoirs") for properties, geometry in waterbodies],
        "usgs_gauges": [feature({**properties, "point_provenance": manifest["site_sources"][properties["usgs_id"]]}, geometry, "usgs_gauges") for properties, geometry in gauges],
        "river_network": [feature(properties, geometry, "river_network") for properties, geometry in rivers],
        "delaware_river_basin": [feature(properties, geometry, "delaware_river_basin") for properties, geometry in boundary],
        "map_points": points,
    }
    payload = {
        "schema": "fe_walter.projected_map.v1",
        "crs": {"authority": "EPSG:5070", "name": "NAD83 / Conus Albers", "units": "metres", "axes": ["easting", "northing"], "wkt": crs_wkt},
        "geometry_policy": "Original source coordinates and precision; no simplification, rounding or reprojection of GeoPackage geometry. This is projected plotting JSON, not RFC7946 geographic GeoJSON.",
        "viewport_bounds_epsg5070": viewport,
        "sources": provenance,
        "upstream_source_urls": gis_manifest["sources"],
        "fe_geometry_provenance": {
            "basins": {site: manifest["basin_sources"][site] for site in ["01447500", "01447720", "01447800"]},
            "nhdplus_hr": {key: value for key, value in manifest["nhdplus_hr_sources"].items() if key.startswith("fe_walter:")},
            "routing_network": manifest["routing_network_sources"]["fe_walter"],
            "reservoir_topology": manifest["reservoir_topology_checks"]["fe_walter"],
        },
        "model_topology": {"model_outlet_count_including_dummy": model["WaterSystem"]["NumSubbasins"], "seven_model_subbasins": sorted(declared), "aggregation_flow_lengths_m": {key: aggregation[key]["Inputs"]["FlowLength"] for key in sorted(routed)}, "execution_trace_checked": False},
        "branch_counts": branch_counts,
        "selection_role_note": "The diagnostic branch is excluded from parameter selection per source attributes; all seven units are declared in formal model reservoir-flow aggregation.",
        "layer_counts": {key: len(value) for key, value in layers.items()},
        "river_selection": {"source_reach_count": len(river_rows), "method": "Complete source reaches intersecting viewport bounds; no clipping or synthetic connections"},
        "runtime": {"python": platform.python_version(), "shapely": shapely.__version__, "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str, "pyyaml": yaml.__version__, "proj_network_enabled": False},
        "generator_sha256": sha256(Path(__file__)),
        "subbasins": layers["model_units"],
        "layers": layers,
    }
    # Refuse success if any source changed while exporting.
    for name, path in source_paths.items():
        if sha256(path) != provenance[name]["sha256"]:
            raise RuntimeError(f"Source changed during export: {path}")
    if sha256(source) != source_hash:
        raise RuntimeError("GeoPackage changed during export")
    output = output.resolve()
    if output in [path.resolve() for path in source_paths.values()]:
        raise ValueError("Output must not overwrite a provenance source")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    # Re-read the saved artifact and verify its persisted identifiers/counts.
    saved = json.loads(output.read_text(encoding="utf-8"))
    if {f["properties"]["subbasin_id"] for f in saved["layers"]["model_units"]} != EXPECTED_UNITS:
        raise RuntimeError("Persisted model identifiers differ")
    return {"output": str(output), "sha256": sha256(output), "bytes": output.stat().st_size,
            "source_sha256": source_hash, "layer_counts": saved["layer_counts"],
            "branch_counts": saved["branch_counts"], "map_points": saved["layers"]["map_points"],
            "runtime": saved["runtime"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Formal four_reservoir_semidistributed.gpkg")
    parser.add_argument("--output", required=True, type=Path, help="Projected plotting JSON")
    parser.add_argument("--config", type=Path, help="Override project configs/four_reservoir_semidistributed.json")
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.output, args.config), indent=2))


if __name__ == "__main__":
    main()
