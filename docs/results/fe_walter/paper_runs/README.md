# F.E. Walter paper runs: daily outputs, 2021–2025

These files hold the daily outputs behind the scores in the paper's Table 2
(daily performance, F.E. Walter Reservoir, 1 January 2021 to 31 December 2025,
1,826 days). They let a reader recompute every score from the daily values.

**Included runs.** One rule-based run (MOSART-Urban rule), five completed runs
of "LLM without operational knowledge" and five completed runs of "LLM with
operational knowledge", 11 runs in all. Five more runs per LLM agent are still
being executed and are **not included**; this folder will be extended when they
are accepted. The LLM decision records of the 10 included LLM runs are in
[`decisions/`](decisions/) (see "Decision records" below).

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
| `provenance.json` | SHA-256 and row counts of the four CSV files, SHA-256 and sizes of the decision files, and SHA-256 with base file names of the private source files they were built from. |
| `decisions/*.jsonl.gz` | One gzip-compressed JSON Lines file per LLM run, 10 files, 6.4 MB in all (see below). |

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
`tests/test_fe_walter_paper_decisions.py` checks the decision files below.

## Decision records

`decisions/<agent>_run<N>.jsonl.gz` holds the decision record of LLM run `N`
(1–5, the same numbers as in `daily_per_run.csv`) for each of the two LLM
agents. Each file is gzip-compressed JSON Lines (one JSON object per line,
UTF-8; the gzip header carries no time stamp or file name). Line 1 describes the
run and each following line is one day, 1,826 days in date order.

**Line 1, `"record": "run"`:** `agent`, `run`, `run_id`; `model` settings
(provider, model name, temperature, seed, context length, maximum tokens,
thinking switch, maximum attempts, retry delay, timeout); `system_prompt`
(full text, the same every day) and its SHA-256; `reply_schema` (the JSON schema
the model had to answer in); `operating_rules_sha256` (the operating-rules
document, with-knowledge runs only); `initial_storage_m3`; date range and record
count; and the comparison with the repository's example files (below).

**Each day, `"record": "decision"`:**

- `date`, `timestep`, `decision_id`.
- `outcome`: `accepted_first_attempt`, `accepted_after_retry` or
  `no_valid_reply` (no day in these runs used a fallback or lacked a valid reply).
- `inputs`: inflow (ft³/s), pool elevation at the start of the day (ft), storage
  at the start of the day (m³) and `target_period`.
- `user_message`: the daily prompt exactly as sent to the model.
- `attempts`: for each attempt the number, `success`, `error_class`, `refusal`,
  `truncated`, token `usage`, `done_reason` and `reply_text`, the model's reply
  text as returned (a truncated reply is kept as returned).
- `reply`: the accepted reply, parsed.
- `requested_release_cfs` and `requested_release_cms`: the release the reply
  asked for, as parsed.
- `audit`: `status` (PASS, WARN or FAIL), `warnings`, `reasons`, `hits`,
  `citations`. The audit only records its verdict.
- `implemented`: what the reservoir model then did that day: controlled release,
  spill, total outflow (m³/s), storage at the start and end of the day (m³),
  `adjustments` and `minimum_release_shortfall_cms`.

The implemented total outflow converted to ft³/s is the `water_release_cfs` of
the same run and day in `daily_per_run.csv`. Absolute paths, user and machine
names, local server addresses and the repeated run-settings block are removed.

**Prompt and rules comparison.** The system prompts and the operating-rules
document recorded in the runs are **not** byte-identical to
`examples/fe_walter/prompts/*.txt` and `examples/fe_walter/knowledge/operating_rules.md`.
The recorded prompts add one line giving the operation target in storage terms
and, for the without-knowledge agent, one sentence on the start-of-interval
storage. The recorded rules document is slightly different from the repository
copy. Each run header gives the SHA-256 values and the match result: `false`
for the system prompt in every run and for the rules document in the
with-knowledge runs, and `null` for the rules document in the
without-knowledge runs, which do not receive it.
The recorded text is what the models received.
