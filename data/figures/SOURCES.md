# FE Walter plotting geometry

`fe_walter_map.json` exports the formal project's
`results/current/four_reservoir_hydrocnhs_native/gis/four_reservoir_semidistributed.gpkg`.
The GeoPackage SHA256 is
`6eeac6d43823b32d61c710c81740f9912e9e6b351198d6d6e4bf14357952d381`.
Each supporting manifest, model, config and source map has its resource name,
byte count and SHA256 recorded in the JSON. The source remains read-only.

All geometry uses **EPSG:5070, NAD83 / Conus Albers**, with easting/northing in
metres. Coordinates retain the GeoPackage's original double precision; nothing
is simplified or rounded. Although features use GeoJSON-style geometry objects,
this projected plotting JSON is not RFC7946 geographic GeoJSON.

The export includes seven model units, three branch basin outlines, one
reservoir waterbody, two USGS gauges, 299 complete river reaches intersecting
the model-unit bounds plus 1.5 km, and the Delaware River Basin boundary for an
inset. River coordinates are neither clipped nor synthetically connected.
The seven identifiers are `FEW-D-01`, `FEW-D-02`, `FEW-X-01`, `FEW-X-02`,
`FEW-X-03`, `FEW-R-01`, and `FEW-R-02`: two donor, three diagnostic and two
residual units. The diagnostic branch is excluded from parameter selection
according to source attributes. All seven are present in the formal model's
reservoir-flow aggregation; the model's eighth outlet is an aggregation dummy.
This export checks declared topology and does not execute the inflow model.

USGS gauges `01447500` and `01447720` are copied from the GeoPackage point
records. Their original NLDI response URLs and snapshot hashes come from the
formal geometry manifest. Polygon and river provenance follows the formal
NLDI, NHDPlus HR and WBD manifests; no upstream download was repeated.

The dam/outlet point is the **formal project-recorded reservoir outlet**, not a
centroid: config `reservoirs.fe_walter.reservoir_outlet` gives longitude/latitude
`[-75.72047, 41.11258]` in EPSG:4326, and the formal study map labels that record
as a dam. Its EPSG:5070 location is `[1676720.841012826, 2191179.562269703]`.
**Unresolved:** the config does not cite a primary dam survey/inventory record.

The main Lehigh River inlet is **derived from source geometry**, not surveyed.
Following the formal upstream map, it is the Lehigh River–waterbody boundary
crossing farthest from the recorded outlet, selected from two crossings. Its
EPSG:5070 location is `[1678199.1338914689, 2193382.9364154125]`, on source reach
NHDPlus ID `10000200619815`. The JSON preserves the method and evidence kind.

Reproduce from the operations repository, using a Python environment with
Shapely, PyProj and PyYAML:

```sh
python docs/figures/source/extract_fe_map.py \
  --source /path/to/formal-project/results/current/four_reservoir_hydrocnhs_native/gis/four_reservoir_semidistributed.gpkg \
  --output data/figures/fe_walter_map.json
```

The formal project tree must also contain its source manifests, model, config
and map scripts. `--config` may override the config location. The verified
runtime was Python 3.14.0, Shapely 2.1.2, PyProj 3.7.2 (PROJ 9.5.1), and PyYAML
6.0.3. PROJ network access is disabled during export.
