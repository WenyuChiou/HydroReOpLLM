# F.E. Walter paper runs: daily outputs, 2021–2025

These files hold the daily outputs behind the scores in the paper's Table 2
(daily performance, F.E. Walter Reservoir, 1 January 2021 to 31 December 2025,
1,826 days). They let a reader recompute every score from the daily values.

**Included runs.** One rule-based run (MOSART-Urban rule), five completed runs
of "LLM without operational knowledge" and five completed runs of "LLM with
operational knowledge", 11 runs in all. Five more runs per LLM agent are still
being executed and are **not included**; this folder will be extended when they
are accepted. The full LLM decision records (requests, replies, reasons) are
not included either.

**Starting storage.** The rule-based run starts from 4,287,715 m³. The LLM runs
start from 4,337,391 m³. The scores describe agreement with observations under
each configuration.

**How this differs from [`../completed/`](../completed/README.md).** The daily
files there (`daily_chart_data.csv`, `daily_run_range.csv`,
`table3_metrics_per_seed.csv`) are an earlier three-run comparison with a
different rule-based comparator. This folder is the paper's own set.

## Files

| File | Content |
|---|---|
| `daily_per_run.csv` | 20,086 rows (11 runs × 1,826 days): `date`, `agent`, `run`, `water_elevation_ft`, `water_release_cfs`, `downstream_flow_cfs`. `agent` is `rule_based` (run 0), `llm_without_operational_knowledge` or `llm_with_operational_knowledge` (runs 1–5). |
| `observations.csv` | 1,826 rows: `date`, observed pool elevation (ft, USGS 01447780), White Haven discharge (cfs, USGS 01447800), Lehighton discharge (cfs, USGS 01449000). |
| `scores_per_run.csv` | KGE and RMSE for each run and each of the three quantities (33 rows). |
| `scores_summary.csv` | Median, minimum and maximum of KGE and RMSE per agent and quantity. |
| `provenance.json` | SHA-256 and row counts of the four CSV files, and SHA-256 with base file names of the private source files they were built from. |

## Definitions

- **Water elevation** (ft, NGVD29): pool elevation at the end of each day.
  LLM runs convert simulated end-of-day storage to elevation with the
  storage–elevation curve; the rule-based run reports elevation directly.
- **Water release** (ft³/s): controlled release plus spill. Observations use
  the USGS 01447800 White Haven discharge, a proxy for the release; it is not a
  direct measurement of gate release.
- **Downstream flow** (ft³/s): routed flow at Lehighton (USGS 01449000).
- **KGE** is the Gupta et al. (2009) Kling-Gupta efficiency, with the
  population standard deviation. **RMSE** is in ft for elevation and ft³/s for
  flows. Every score pairs the same 1,826 dates.

`tests/test_fe_walter_paper_runs.py` recomputes all scores from
`daily_per_run.csv` and `observations.csv` and checks them against Table 2.
