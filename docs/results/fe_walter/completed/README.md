# F.E. Walter results

## Daily performance against observations

**Table 3. Daily simulation performance against observations, 2021–2025.**

| Agent type | Reservoir level KGE | Reservoir level RMSE | Water release KGE | Water release RMSE | Downstream flow KGE | Downstream flow RMSE |
|---|---:|---:|---:|---:|---:|---:|
| Rule-based (MOSART-Urban) | 0.077 | 96.21 | 0.640 | 598.47 | 0.815 | 706.19 |
| LLM without operational knowledge | 0.817 (0.793–0.838) | 20.38 (19.27–22.15) | 0.695 (0.683–0.716) | 581.30 (561.91–592.14) | 0.830 (0.826–0.833) | 706.91 (689.86–716.50) |
| LLM with operational knowledge | 0.847 (0.787–0.878) | 16.71 (14.86–19.67) | 0.619 (0.607–0.641) | 671.01 (647.53–684.99) | 0.832 (0.828–0.841) | 754.68 (728.36–769.09) |

KGE (2009) is dimensionless. RMSE is in ft for reservoir level and ft³/s for
flows. All scores use the same 1,826 paired daily dates. Level uses USGS
01447780. Water release includes controlled release and spill and is compared
with the USGS 01447800 near-dam discharge proxy. Downstream flow uses USGS
01449000 at Lehighton.

The deterministic MOSART-Urban run uses the
[paper baseline](../../../../examples/fe_walter/operation/README.md#paper-baseline-with-mosart-urban).
Each LLM row shows the mean and minimum–maximum across five separately scored
seeds. The MOSART-Urban run and the saved LLM campaign use different initial
storage and release constraints. The scores describe agreement with observations
under their respective configurations.

[Download Table 3 KGE and RMSE values](table3_daily_kge_rmse.csv)

## Historical comparison figures and scores

The archived figures and scores preserve the original Hanasaki comparator and
three seeds per LLM setting. The Daily and Hourly comparisons retain their
original input and initialization records.

### Daily water elevation and release, 2021–2025

![Daily water elevation and water release, complete chronological series](daily_2021_2025.png)

The two panels show (a) water elevation and (b) total reservoir outflow
(controlled release plus spill). Each LLM line is the per-date median of three
runs. The 1,826 Daily decisions cover 1 January 2021 through 31 December 2025;
they are not folded into an annual cycle. The end-of-2025 state is plotted at
the 1 January 2026 boundary, without adding a decision. Pool observations are
daily means. The release observation is the USGS 01447800 White Haven near-dam
proxy, not an independent direct measurement of gate release.

The dashed target elevation is the original **illustrative seasonal display
reference**, not the Hanasaki comparator's actual control target or an official
operating schedule. All seven runs share initial storage 4,337,390.926410141 m³.
This completed research campaign has its own pinned configuration; the separate
[executable Rule-based lesson](../../../../examples/fe_walter/operation/README.md) retains its own inputs and
initialization and must not be relabeled as the producer of these results.

[High-resolution PNG](daily_2021_2025.png) · [PDF](daily_2021_2025.pdf) ·
[Target reference](daily_target_reference.csv)

The companion version below shows the pointwise **minimum–maximum range across
three runs**. This is neither an across-year IQR nor a confidence interval.
Rule-based operation has one deterministic run and no synthetic uncertainty band.

![Daily comparison with three-run ranges](daily_2021_2025_range.png)

[PNG with ranges](daily_2021_2025_range.png) · [PDF](daily_2021_2025_range.pdf) ·

### Historical daily performance with Hanasaki

The earlier Table 3 used KGE and NSE with three LLM seeds per setting.

| Agent type | Reservoir level KGE | Reservoir level NSE | Water release KGE | Water release NSE | Downstream flow KGE | Downstream flow NSE |
|---|---:|---:|---:|---:|---:|---:|
| Rule-based | 0.092 | -9.560 | 0.622 | 0.364 | 0.802 | 0.722 |
| LLM | 0.818 | 0.534 | 0.692 | 0.387 | 0.830 | 0.723 |
| LLM+K | 0.832 | 0.657 | 0.626 | 0.209 | 0.833 | 0.691 |

Here LLM means **LLM w/o additional knowledge** and LLM+K means **LLM w/
additional knowledge**. Each LLM row is the arithmetic mean of metrics computed
separately for its three seeds; it is not a metric computed from the median
line. All 1,826 date pairs are retained. Release is total reservoir outflow
compared with the unchanged White Haven observation proxy. Downstream flow
refers to Lehighton. These definitions differ from the separate retained
Rule-only lesson's primary-score masks and routed-station metric definitions.

[Historical KGE/NSE table PNG](table3_daily_simulation_performance.png) ·
[Historical table PDF](table3_daily_simulation_performance.pdf) ·
[Historical summary CSV](table3_summary.csv) · [Historical per-seed metrics](table3_metrics_per_seed.csv)

### Hourly downstream event comparison

![Hourly Lehighton flow for Ida and the 2023 rain event](hourly_events_AB.png)

Panel A is Hurricane Ida: **30 August 2021 04:00 UTC to 13 September 2021
04:00 UTC**, end exclusive, 336 hourly decisions. Panel B is the 2023 rain event:
**16 December 2023 05:00 UTC to 26 December 2023 05:00 UTC**, end exclusive,
240 hourly decisions. Both scenarios include all three accepted seeds. These
are native Hourly results, not Daily values drawn on an hourly axis. The shared
reference prehistory and numerical routing tail are outside the decision and
plot windows. Each strategy's own controlled release plus spill is routed to
Lehighton; observed White Haven flow is not substituted for strategy output.

[High-resolution PNG](hourly_events_AB.png) · [PDF](hourly_events_AB.pdf) ·

Similar downstream curves do not demonstrate equivalent reservoir behavior or
improved operating skill. Common downstream runoff and similar release choices
can conceal differences. Missing control-station observations remain a limitation
of the knowledge-dependent decisions. The Hourly C&V and events are retrospective;
the event comparison is not a blind independent flood forecast.

The [historical file inventory](provenance.json) records accepted source identities
and SHA256 for the archived plots and numeric exports. Full raw decisions, reasons,
requests, responses and failure history remain in the experiment handover archive.

[Daily workflow](../../../DAILY_WORKFLOW.md) · [Historical 2016 results](../../../../examples/fe_walter/results.md)
