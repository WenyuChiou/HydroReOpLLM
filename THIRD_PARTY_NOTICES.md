# Source attribution

The versioned contract shape is adapted from `src/hydrocnhs/policy/contracts.py`
in WenyuChiou/HydroCNHS candidate commit `fde3baf8fb0de6bdc3650a10a490a74a327d25e1`.
The candidate extension is separate from the accepted HydroCNHS core pin.
HydroCNHS is by Chung-Yi Lin; its BSD 3-Clause notice is preserved in
`licenses/HydroCNHS-BSD-3-Clause.txt`.

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
