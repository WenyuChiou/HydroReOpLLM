# F.E. Walter manuscript results, 2021–2025

The study compares daily operations under a seasonal target alone and the same target with a Dam Knowledge Package (DKP). Each LLM setting has ten runs, seeds 1–10. One MOSART-Urban run supplies the deterministic baseline. All 21 runs cover the same 1,826 dates.

| Pool elevation | MOSART-Urban | Seasonal target | Seasonal target + DKP |
|---|---:|---:|---:|
| Table 2 KGE, median | 0.077 | 0.806 | 0.858 |
| KGE range across seeds | — | 0.781–0.838 | 0.787–0.878 |
| Table 2 RMSE, median (ft) | 96.21 | 20.85 | 16.07 |

The arithmetic mean pool-elevation KGE across the DKP runs is 0.849. Table 2 reports the median of the per-run scores. Both LLM settings used daily consultation. The rule-based run starts at 4,287,715 m³ and the LLM runs at 4,337,391 m³.

## Recompute Table 2

From this directory, run the following command with Python 3.12.

```shell
python verify.py
```

The check uses saved daily values and observations. It runs offline and requires only the Python standard library.

| Download | Use |
|---|---|
| [Daily simulations](daily_simulations.csv.gz) and [observations](observations.csv.gz) | Compare each run with the paired dates. Pool elevation uses USGS 01447780. Total release includes controlled release and spill and is compared with the near-dam discharge proxy at White Haven (01447800). Downstream flow uses Lehighton (01449000). |
| [Per-run scores](scores_per_run.csv) | Inspect KGE, its components and RMSE for each run and variable. |
| [Table 2 medians and ranges](table2_median_range.csv) and [printed reference values](manuscript_table2_reference.csv) | Compare full-precision summaries against the reported table. |
| [Offline verifier](verify.py) and [source manifest](provenance.json) | Verify the distributed data and identify the accepted source records by SHA-256. |

## Figures 3 and 4

| Figure | Published figure | Numeric series |
|---|---|---|
| Figure 3. Daily elevation and total release | [PDF](Figure_3_daily_2021_2025.pdf) | [Daily seed medians](figure3_daily_seed_medians.csv) |
| Figure 4. Annual cycle of elevation and total release | [PDF](Figure_4_annual_cycle.pdf) | [Calendar-day medians and interquartile ranges](figure4_calendar_medians_and_across_year_iqr.csv) |

Figure 3 shows the median across the ten seeds on each date for each LLM setting. On January 1, 2021 at 00:00, the elevation starts at 1312.4274106596197 ft for MOSART-Urban and 1312.717496583342 ft for both LLM settings. Plot each CSV row's simulated end-of-day elevation at 00:00 the following day, ending on January 1, 2026. Plot the observed elevation and all daily releases at 12:00 on the row date. Plot the [illustrative target](illustrative_target_full_calendar.csv) at 00:00 on each listed date.

Figure 4 summarizes those daily values across years by calendar day. The target line follows the 2023 dates in the illustrative target file. The annual-cycle plot omits February 29. Table 2 includes it.

## Identify the paper model

The runs used `gemma4:12b` with Ollama 0.40.6, temperature 0.7 and a 16,384-token context. The [model lock](paper-model-lock.json) identifies the original model manifest, all five blobs, the runtime download and the inference settings. It also records the SHA-256 of the DKP document and both system prompts. The [DKP system prompt](system_prompt_dkp.txt) and [seasonal-target system prompt](system_prompt_seasonal_target.txt) preserve the text used in the study. The historical 2014 reference is part of the archived DKP prompt.

To verify an existing Ollama model store, use your store's own manifest and blobs directory. The example uses the default Windows location. The optional server check reads the version and the digest of the tag from the running local server.

```powershell
$modelStore = Join-Path $env:USERPROFILE '.ollama/models'
python verify_paper_model.py "$modelStore/manifests/registry.ollama.ai/library/gemma4/12b" "$modelStore/blobs" --server-port 11434
```

For an offline archive, pass its manifest and blobs directory and omit `--server-port`. The [original raw manifest](ollama-manifest.json) can be used to verify a saved set of blobs. The [verifier](verify_paper_model.py) also accepts `--rules PATH` to check an author-supplied copy of the paper's operating knowledge.

Recomputing the results uses the files above. Generating new LLM decisions additionally requires the original model blobs, the paper DKP for the knowledge arm, and the author-supplied `reference_v3_7` backend and case inputs. Those dependencies are external to the Python distribution.
