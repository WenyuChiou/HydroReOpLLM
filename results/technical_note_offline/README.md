# Offline Technical Note evidence

**Software acceptance: PASS. Model/provider calls: 0. Operating-policy acceptance: unset.**

| Saved run | Days / reservoir-days | Maximum reservoir residual (m³) | Maximum system residual (m³) | Audit |
|---|---:|---:|---:|---|
| Hanasaki-based flood-control benchmark | 3 / 3 | 2.3283e-10 | 2.3283e-10 | PASS 3 |
| Zero-shot, synthetic replies | 3 / 3 | 0 | 0 | PASS 3 |
| DKP, synthetic replies | 3 / 3 | 0 | 0 | PASS 3 |
| FE Walter + Beltzville + passive Prompton | 31 / 93 | 3.0268e-9 | 3.7253e-9 | PASS 62; UNKNOWN 31 |

All stored routing outputs matched independent reconstruction (maximum difference
0 m³/s). The passive-outlet UNKNOWN records retain their original meaning; they
are not evaluations of Prompton's operating strategy. These fixture results do
not compare LLM policy performance.

The four outputs were generated in a fresh source snapshot and new Python 3.12.14
venv with an offline editable install. Existing scientific/build dependencies were
reused through `.pth` paths; a network dependency installation was not tested.
All 23 pure-Python cells in eight notebooks executed successfully; this was not a
Jupyter-kernel test. Provider requests were forbidden in the notebook runner.

- [final_validation.json](final_validation.json): final checks after review corrections, source scope and captured command hashes.
- [offline_runs_final.zip](offline_runs_final.zip): complete four-run records, including raw prompt/retrieval/audit evidence; 221 files.
- [run_files_final.json](run_files_final.json): byte lengths and SHA256 for each final bundle member.
- [execution_sources_final.json](execution_sources_final.json): source snapshot at execution, including documentation. [delivery_changes.json](delivery_changes.json) records two later documentation-only source-version notes and their delivery hashes; the execution record is preserved.
- [preserved_files.json](preserved_files.json): all 691 existing protected files verified unchanged.
- [clean_environment_final.json](clean_environment_final.json): final reproduction setup and delivered notebook hashes.
- [logs](logs): complete selected stdout/stderr and command receipts. Paths in receipts identify the original local execution; copies here have the same hashes.
- [archive_validation.json](archive_validation.json): Git archive checks with Windows and LF checkout settings. All 691 protected working files retain their hashes. Five legacy Git blobs now store the already accepted working bytes; only CRLF/LF representation changes, with no parameter/data changes.

Final test evidence: 472 tests and 395 subtests passed; the affected suite passed
114 tests and 60 subtests. A separate captured comparison covers 162 exact
numerical vectors against the pinned GitHub benchmark function (`c11a81…`).
The earlier [acceptance](acceptance.json), [bundle](offline_runs.zip), source pins
and environment receipt remain as evidence before the review corrections.
No recalibration, accepted multi-year replay or real LLM call was performed.

Reference source: [captured GitHub source](logs/20261012T135754708459Z-stdout.log)
and [comparison output](logs/20261012T145323522501Z-stdout.log), with recipes in
the matching command receipts. The later benchmark source is distinct from the
unchanged V3.7 vendor used for LLM prompt, retrieval and audit compatibility.

The [full acceptance report](../../archive/README.md) records compatibility,
documentation/figure checks and boundaries. [Live preparation](../../docs/LIVE_READINESS.md)
lists the remaining experiment conditions. Historical five-year diagnostics,
policy failures and unknown request costs remain unchanged.
