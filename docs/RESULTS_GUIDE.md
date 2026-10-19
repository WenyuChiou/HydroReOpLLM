# Read your results

The current case figure uses saved results from the **previous prompts**. The
[October request review](../examples/fe_walter/prompt_review.md) shows the proposed
seasonal addition separately; it has no new model replies.

Start with the water level and controlled release. The
[FE Walter results](../examples/fe_walter/results.md) show the current saved
2016 comparison: **Rule-based**, **LLM without additional operating knowledge**, and
**LLM with additional operating knowledge**.

## Read the operation trajectory

For your own coupled run, open `<output>/operation/summary.json`, then read:

| File | Contents | Unit |
|---|---|---|
| `reservoir_trajectory.csv` | Inflow, requested release, actual controlled release, spill and storage | m³/s; storage in m³ |
| `network_flows.csv` | Flow at reservoirs and downstream routing nodes | m³/s |
| `network_balance.csv` | Water-balance residual for the network | m³ |

The `output` in experiment YAML is the parent directory. Hydrology preparation
is saved there; daily operation is saved in its `operation/` subdirectory.
The `resume --output` option instead names the operation directory itself.

**Controlled release** is water passed through the controlled outlet. **Spill**
is overflow calculated separately. Downstream routing receives their sum.
Requested release may differ from actual controlled release when physical
limits or available water constrain the request.

Water elevation is derived from storage using a reservoir-specific curve; the
generic framework stores volumes. The current FE Walter plots use feet NGVD29 for
water level and cfs for flow; stored flow data retain m³/s. The case prompt also
expresses release in cfs before parsing. Keep the units in every figure caption.

## Verify before comparing methods

```powershell
reservoir-experiment verify <output>/operation
```

Check that dates are complete and unique, water balance is consistent, and each
method used the intended inflow, initial state and reservoir parameters.
Verification checks saved records and numerical consistency. Seasonal operation
performance must be evaluated separately; a completed run can miss a target.

The [results notebook](../tutorials/README.md) reads saved data and reproduces
one combined teaching figure without running a model or hydrology. Panel (a)
compares 2016 end-of-day water elevation in ft NGVD29, with a target pool elevation reference
that switches vertically between 1300 and 1370 ft on May 15 and October 15.
Panels (b–d) compare daily controlled release in cfs, one method per row,
with blue upstream simulated inflow, identical flow scales and no spill. All axes share dates; the
legend names **Rule-based**, **LLM without additional operating knowledge**, and **LLM with additional operating knowledge**.

## Follow one decision

To investigate a feature in a trajectory, join its decision, raw reply and
physical transition by decision ID. The [records reference](RECORDS.md) explains
these files and the distinction between response validation and operation audit.

## Read post-routing outcome checks

Optional downstream diagnostics are described in
[Decision records and audits](RECORDS.md#read-post-routing-outcome-checks).
They record conditions after routing and do not modify a release.

## Troubleshoot

Use [Troubleshooting](TROUBLESHOOTING.md) for invalid replies, incomplete runs
and target misses. Use [Run and resume](RUNNING.md) to continue interrupted work.
