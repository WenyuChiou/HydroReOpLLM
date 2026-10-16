# Code structure and the daily simulation loop

Start with the [installation](GETTING_STARTED.md), then the
[annual FE Walter walkthrough](../examples/fe_walter/annual/README.md).
You configure files; the existing experiment CLI connects the modules.

## 1. Keep three kinds of settings separate

| Settings | What you decide | FE Walter example |
|---|---|---|
| Hydrology | Weather, subcatchments, runoff parameters and upstream routing | [Accepted native YAML](../data/accepted/fe_walter_hydrology.yaml) |
| Physical case | Reservoir capacity, initial storage, release bounds and river connections | Generated `case.json` |
| Experiment | Dates, operation method, model, prompt, optional knowledge and checks | Generated `rule.yaml`, `llm_available.yaml`, `llm_knowledge.yaml` |

Changing the LLM method does not require recalibrating the hydrology. Keep the
physical case fixed when comparing the operation methods. The
[hydrology chapter](../examples/fe_walter/hydrology.md) explains the accepted
weather/GIS preparation, parameter derivation and calibration/validation periods.

## 2. Follow the entry points

```text
run_experiment.py                  check / run / resume / verify
src/
  hydrocnhs/                       Accepted hydrology, routing and Dam API
  delaware_operations/
    historical.py                  Accepted continuous weather-to-inlet calculation
  llm_reservoir_agent/
    workflow.py                    Validate YAML and choose operation backends
    experiment.py                  Run orchestration and durable result records
    network.py                     Connect native Dam agents and river routing
    agent.py                       Assemble current information and execute a decision
    physics.py                     Common storage, controlled release and spill
    reference_backend.py           Retained FE Walter LLM scenario implementation
    configured_backend.py          General prompt/provider interface and bounded retries
    auditor.py                     Record configured operating checks
    trace.py                       Connect decisions, audit and physical records
    recovery.py                    Rebuild a saved prefix without new model requests
    verification.py                Check saved execution evidence and water accounting
examples/fe_walter/
  prompt.txt                       One shared operator prompt for both LLM scenarios
  annual/prepare.py                Prepare the common year and method configurations
```

The two LLM scenarios use the retained reference implementation. For your own
reservoir, the general `configured` method supports your prompt, information and
auditors; the reference knowledge rules are specific to FE Walter.

## 3. Prepare upstream inflow

`annual/prepare.py` calls `historical.run_historical()`. The accepted continuous
1989–2025 GWLF/Lohmann simulation reads precipitation, temperature and PET for
seven hydrological units. Preparation retains the initialization/routing history
and selects all 366 days of 2016. It writes the routed inlet, shared physical case
and three experiment YAMLs. This step makes no LLM request.

The implemented demonstration is a two-stage execution: prepare the natural
inlet, then run daily coupled reservoir operation and downstream routing. It
does not yet expose a single generic weather-mode experiment command.

## 4. Choose the decision method

`workflow.load_settings()` checks files, units, dates, hashes and agent bindings.
It chooses the backend from `agents.fe_operator.strategy` and its settings:

| YAML choice | Who supplies the release request |
|---|---|
| `strategy: benchmark` | The deterministic rule-based benchmark |
| `strategy: reference_v3_7`, `reference.method: zeroshot` | LLM using available information |
| `strategy: reference_v3_7`, `reference.method: dkp` | LLM with retrieved operating guidance |

For both LLM scenarios, `reference.system_prompt` points to the same file.
The method controls whether operating guidance is retrieved into the daily
message. Model settings are separate from water-balance parameters.

## 5. Walk through one simulated day

1. **Route the water arriving at the reservoir.** Native HydroCNHS supplies the
   day's simulated inlet. The annual demonstration uses the prepared upstream
   inlet and an identity downstream reach.
2. **Build decision information.** `agent.py` supplies the date, inlet, beginning
   storage/pool and committed prior releases.
3. **Request a release.** The selected backend builds the daily prompt, optionally
   retrieves knowledge and obtains the model response.
4. **Check the response.** Parse complete JSON, required fields, units and finite
   numeric values. Bounded retries use the same information without advancing
   reservoir storage.
5. **Record operating checks.** The auditor records its verdict. A target miss or
   diagnostic audit FAIL does not resample the decision or stop the daily loop.
6. **Implement and route.** `physics.apply_transition()` calculates controlled
   release, spill and ending storage. Native routing receives controlled release
   plus spill once.
7. **Commit feedback.** The journals save the decision, audit and physical result.
   The next day begins with ending storage and the implemented release history.

Repeat this daily loop to December 31. The [captured decision example](../examples/fe_walter/annual/decision_2016_01_01.md)
shows actual inputs, full messages, response, audit and next-day feedback from
the earlier diagnostic.

## 6. Separate completion from reservoir performance

A complete annual run has 366 committed days and passes saved-evidence and
water-accounting verification. That does not establish an acceptable operating
policy. Plot **pool elevation** and **water release**, then assess seasonal
performance separately. Keep the original raw responses and audit labels.

If the process is interrupted, `resume` reconstructs the saved prefix in a new
directory. It checks request hashes and physical state before asking for a new
decision. Read the [recovery instructions](../examples/fe_walter/annual/README.md#7-continue-an-interrupted-run)
before using it.
