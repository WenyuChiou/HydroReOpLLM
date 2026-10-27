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

The physical separation and source data follow the accepted
HydroCNHS-Delaware-Demo commit `8d59dcac2f9d06fe16030f68826b425d492c9529`.
Selected source hashes and explicit prototype assumptions are recorded in
`data/accepted/manifest.json`.

The supplied Anik V3.7 program is preserved byte for byte in an external recovery
package and is not distributed in the current source tree or wheel. Optional
comparisons load hash-verified sources through `HYDROOPS_ANIK_SOURCE_DIR`; see the
[recovery index](archive/fe_walter/README.md). Its
[source manifest](archive/fe_walter/original_source_manifest.json) records the
attachment hashes and discrepancies with README-declared hashes. No license was
included in that attachment; no redistribution right is claimed. The case's
operating reference is preserved in
[`examples/fe_walter/knowledge/operating_rules.md`](examples/fe_walter/knowledge/operating_rules.md).
