# FE Walter: Rule-based reference

> Historical reference: this page preserves earlier settings and saved decisions.
> Start new work from the [current FE Walter tutorial](../../../tutorials/README.md)
> and read the [current annual results](../results.md).


[English](README.md) | [繁體中文](README.zh-TW.md) · [FE Walter case](../README.md)

This custom daily flood-control rule requests release through the native
HydroCNHS Dam API. It follows [Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)
and the flood-control formulation in [Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).
The rule is added by HydroReOpLLM; it is not a built-in HydroCNHS policy.

Shared input and physical assumptions are defined in the [common case setup](../README.md#reservoir-experiment).

First review [the case hydrology](../hydrology.md) and [the coupled daily workflow](../coupling.md).
This method uses the same daily Dam/routing loop with precomputed inflow; the operation run does not recalculate GWLF.
Each implemented operation advances storage; LLM methods retain implemented release history.

## 1. Configure the method

Select the daily flood-control rule and historical inflow statistics from before
the demonstration period. This method needs no model or prompt and makes no model request.

[Full settings and commands are at the end](#files-and-commands). Use a new run ID and output location for a new simulation.

## 2. Understand the operation method

The rule compares capacity with mean annual inflow volume. Large reservoirs
request `k × mean inflow`; smaller reservoirs blend it with current inflow.
The environmental floor is 10% of mean inflow. The coefficient
`k = starting storage / (0.85 × capacity)` updates on the first step and each
operating-year boundary, rather than daily. The prepared climatology selects May.
This rule has no seasonal target controller. See [sources and adaptation](#sources-and-adaptation).

## 3. Run the simulation

1. **Check** the dates, reservoirs, units and planned requests. This makes no model request.
2. **Run** the rule. Shared reservoir calculations implement release and update storage and outflow.
3. **Verify** saved trajectories, water balance and execution evidence. This does not certify a passing policy audit.

[Open the execution and verification commands](#files-and-commands).

## 4. Inspect saved decisions

The saved trajectory records requested release, implemented controlled
release, spill and ending storage. Total outflow is controlled release plus spill
and enters routing once. Next-day history uses implemented release.

| Date | Inflow (m³/s) | Requested (m³/s) | Implemented (m³/s) | Spill (m³/s) | Ending storage (m³) |
|---|---:|---:|---:|---:|---:|
| 2016-01-01 | 32.125319 | 25.098588 | 25.098588 | 0.000000 | 3,064,957.78 |
| 2016-01-02 | 22.353047 | 17.490024 | 17.490024 | 0.000000 | 3,485,122.95 |
| 2016-01-03 | 14.193931 | 11.137442 | 11.137442 | 0.000000 | 3,749,203.61 |

[Historical 2016–2020 results and decision records](../results_history.md)

The table shows this method's saved three-day trajectory, not a policy-performance
assessment. Downloads retain full precision. The linked five-year results belong
to a separate retrieved-knowledge experiment, not a five-year comparison of all three methods.

The benchmark retains **3 PASS** under its release-bounds auditor. This suite
differs from the LLM operating audit, so the counts cannot rank the methods.
The [complete saved day-one rule record](../../../examples/fe_walter/reference_outputs/rule_three_day/raw/policy_a55e8402dabaa06d6127816db201078ccaff0234147efb071c505797a92cdd3a.json)
records the input, daily-rule provenance, requested release and source hashes.

[View the main tutorial](../../../tutorials/README.md) ·
[Module reference](../../../docs/LLM_MODULES.md) ·
[Multiple reservoirs](../../../tutorials/advanced.ipynb)

## Sources and adaptation

Hanasaki, N., Kanae, S., and Oki, T. (2006). “A reservoir operation scheme for
global river routing models.” *Journal of Hydrology*, 327, 22–41.
[DOI](https://doi.org/10.1016/j.jhydrol.2005.11.011).

Abeshu, G. W., et al. (2023). “Enhancing the representation of water management
in global hydrological models.” *Geoscientific Model Development*, 16, 5449–5472.
[Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).

This custom policy adapts the monthly flood-control formulation to daily steps.
It pins the [source decision function](https://github.com/DasanikBD/Delaware-Reservoir-LLM/blob/6c3dc532d712af55db1f4a1d8e018c86249ce7a8/benchmark_release.py)
at commit `6c3dc532d712af55db1f4a1d8e018c86249ce7a8` (function hash `c11a81…`).
The case rule retains that decision formulation; framework methods use the
HydroReOpLLM simulation driver. Original-program comparisons use a separately
restored source artifact. The
[workflow test source](../../../tests/test_benchmark_workflow.py)
checks statistics inputs, configuration and use of the common simulation interfaces.

## Files and commands

For a new study, use [coupled/experiment.yaml](../coupled/experiment.yaml) and follow
[the current tutorial](../../../tutorials/README.md) for checking, execution and verification.
That entry connects the common hydrology, reservoir network and Rule-based agent.

This folder retains [experiment.yaml](experiment.yaml) as a three-day offline
compatibility fixture, alongside the saved historical evidence above. Its duplicate
alias was retired with identical inputs and rule parameters. Earlier commands and
settings remain in the verified [recovery package](../../../archive/fe_walter/README.md).
