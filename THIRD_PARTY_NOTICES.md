# Source attribution

The versioned contract shape is adapted from `src/hydrocnhs/policy/contracts.py`
in WenyuChiou/HydroCNHS candidate commit `fde3baf8fb0de6bdc3650a10a490a74a327d25e1`.
The candidate extension is separate from the accepted HydroCNHS core pin.
HydroCNHS is by Chung-Yi Lin; its BSD 3-Clause notice is preserved in
`licenses/HydroCNHS-BSD-3-Clause.txt`.

The bundled HydroCNHS source retains its upstream commit in
[`third_party/hydrocnhs/SOURCE.json`](third_party/hydrocnhs/SOURCE.json).
A local patch updates five metric calls in `Visual.plot_reg` to the existing
`Indicator.get_*` methods. The manifest records both the original and installed
file hashes and the versioned
[`visual-indicator-api.patch`](third_party/hydrocnhs/patches/visual-indicator-api.patch).
This plotting correction leaves hydrological calculations unchanged.

The versioned `gwlf-groundwater-diagnostics.patch` adds explicit BF0/B0 cold-start
options and optional daily GWLF diagnostics, with worker-result collection in
`Model.run`. Original daily defaults, arithmetic and restart fields are preserved
and checked against a pre-extension numerical oracle. The source manifest retains
both upstream and installed hashes. The new `groundwater.py` and experimental
hourly kernel are local extensions, not unmodified upstream GWLF.

The internal flood-control test fixture in `tests/fixtures/examples/rules/hanasaki_flood_control/` independently implements
the reservoir equations and annual storage snapshot from RiverAI-Project/MOSART-Urban,
commit `7883c5cac62e8c0c585fbafbb1045118cad2dd42`. The implementation records
the upstream source hash.

Daily historical reservoir records and catchment-averaged rainfall for Feitsui Reservoir
and Nanshi Creek used in `examples/multi_reservoir/` are derived from Taipei Feitsui Reservoir
Administration (TFRA) / Taiwan Government Open Data dataset `145840`
(`2015-07-01` to `2025-12-31`).
Historical daily ERA5 temperature, reference evapotranspiration (`temperature_2m_mean`,
and `et0_fao_evapotranspiration`, `2015-01-01` to `2025-12-31`), and `2015-01`–`2015-06`
warm-up rainfall scaling in `examples/multi_reservoir/hydrology/forcing.csv.gz`
are derived from Copernicus ERA5 via the Open-Meteo Historical Weather API (CC BY 4.0).
