F.E. Walter - code V3.7 + DKP v1.2 (7 October 2026)
===================================================
V3.7 = V3.6 using DKP v1.2 (Prof. Yang's approved version) instead of v1.4.
V3.6 = V3.5 plus two zero-shot knowledge versions (item 9).
V3.5 = V3.4 plus temperature and seed options (item 8). V3.4 = V3.3 plus the
DKP release-category option (item 7). Prompts are unchanged from V3.3.

Built on the frozen 2026-10-03 baseline. Implements the changes agreed with
Prof. Yang: nothing about downstream gauges or missing information reaches the
LLM, and the "maximum release" number is no longer shown.

WHAT IS DIFFERENT FROM THE BASELINE (new defaults)
1. Prompt item 6 ("Maximum release given the water available...") is not shown,
   in either arm. It is not Wikipedia-level information, and the model copied
   it (every near-empty month in the baseline). Python still enforces the same
   limit on the water available, the audit and the water balance.
   Files tagged noAvailLine.
2. DKP: no missing_inputs answer field, no missing-information fallback mode,
   no fallback instructions; one neutral line instead: "This model represents
   the reservoir only: storage, inflow and release. Apply the storage, inflow,
   seasonal and release-limit rules. Do not invent an observation or rule."
   Files tagged noMissingInputs.
3. DKP v1.2 (data/DKP_FEWalter_Dam_v1.2.md) - the version Prof. Yang approved.
   ONE small text edit, keeping the name v1.2: in R-PLAN only, the downstream
   control-gage thresholds, the gage-triggered Plan C and the sentence on
   downstream stage trends were removed (16 lines removed, 3 added: a dated
   note at the top of the file and one simplified line); a pool between the
   seasonal target and 1450 ft is Plan B. Nothing else in the file changed.
   The untouched original is archived separately (DKP_FEWalter_Dam_v1.2_original.md,
   not in this package): the run folder holds ONE DKP file, the one the code reads.
   The code (not the file) splits v1.2's Decision Rules section into its
   individual rules and retrieves them with the same conditions as before:
     every month:          R-RELEASE, R-MINNORM, R-ATSITE, R-ZONE
     pool above target:    R-PLAN
     Apr-Oct, no flood:    R-RECREATION
   and NEVER retrieves the Fallback Policy, R-DOWNSTREAM, the Downstream
   Station Ratings or the Time of Travel sections.
   Still visible, by agreement (other rules left unedited): R-RELEASE keeps its
   Plan C branch ("store all inflow"), "stages" and "R-DOWNSTREAM limit"
   wording; R-ATSITE keeps a falling-stage exception and a White Haven
   equivalence; R-MINNORM names the White Haven outflow gage.
4. Results files are written at full precision (a hand recalculation of the
   water balance from any column reproduces Python exactly).
5. Provenance: Ollama version and model digest logged in every run.
6. New option --consult-every-day (daily runs): ask the LLM every day. Without
   it, a daily run reuses the previous decision when inflow changes <=10%.
7. New DKP option --release-categories N (category mode). Ranges are built
   ONLY from the manual's minimum and maximum release (50 and 10,000 cfs),
   spaced evenly on a logarithmic scale (equal-width ranges would put every
   observed monthly release in the lowest range). With N = 8:
     A 50-97 | B 97-188 | C 188-365 | D 365-707 | E 707-1,371
     F 1,371-2,659 | G 2,659-5,157 | H 5,157-10,000 cfs
   The LLM reasons first, then picks a category, then gives release_cfs inside
   it; Python only checks the release lies inside the chosen range (outside =
   audit failure, retried under self-correction). Option --category-value
   midpoint makes Python apply the range's geometric midpoint instead.
   Zero-shot is refused (it has no manual release limits) and stays numerical.
   Files tagged cat8 (or cat8mid).
8. Temperature: by DEFAULT no temperature is sent, so Ollama uses gemma4's own
   default (Prof. Yang's instruction for the final Monte Carlo runs). Every run
   records the model's default parameters and the effective temperature in the
   trace header, prompt-samples header and run summary. --temperature N sets a
   value (--temperature 0 = the earlier deterministic runs, request identical
   to the baseline). --seed N makes a run repeatable on the same computer: use
   one seed per Monte Carlo replicate. Files tagged tempDefault / tempN, seedN.
   To see gemma4's defaults directly:  ollama show gemma4:12b --parameters
9. Two zero-shot versions (option --zeroshot-knowledge):
   target (default): public facts PLUS the 1300/1370 ft operation target
                     (as in all earlier zero-shot runs).
   wiki:             public (Wikipedia-level) facts ONLY - the target sentence
                     and its storage equivalents are removed; the model states
                     the level it is aiming for itself. Files tagged wikiOnly.
   In the wiki version the audit judges the model against the target IT
   states (same checks, same rating curve); a difference from the official
   target is recorded as a note, not a failure. Verified: on identical
   decisions the two versions give identical audit results (24/24 months).
   Metrics against observations and the official target are unchanged.
   DKP is unaffected (it always has the target); the option is refused for DKP.

VERIFIED (replaying the baseline's recorded answers, no LLM)
- DKP with v1.2, all 24 months: 4-5 rule excerpts per month (the previous
  code found none in v1.2); never the Fallback Policy, R-DOWNSTREAM or the
  downstream tables; no Lehighton, Walnutport, Bethlehem, "control gage",
  "Plan C", "missing" or "fallback" in any prompt.
- Zero-shot prompts unchanged; with the v1.3 or v1.4 files the same code
  gives byte-identical prompts to before (24/24).
- Restoring the old settings (--show-availability-line,
  --dkp-include-missing-inputs, DKP v1.3) reproduces the baseline prompts
  byte for byte (24/24, both arms).
- Daily runs work in both arms; water-balance residual 0.

SET-UP - use a NEW folder (keep the baseline folder untouched)
  the four .py files
  data\DKP_FEWalter_Dam_v1.2.md   (the ONLY DKP file the code reads; keep no other
                                   DKP copies in the run folder)
  data\dailystreamflow\fe_walter_simulated_reservoir_inflow_daily.csv

RUNS REQUESTED FOR FRIDAY (single pass; add --seed N, see Monte Carlo below)
Monthly, numerical, 2016-2017:
  python .\reservoir_model.py --reservoir "F.E. Walter Dam" --method zeroshot --llm gemma4 --timestep monthly --start-date 2016-01-01 --end-date 2017-12-31 --run-mode final --llm-failure-action stop --zeroshot-audit-action record --prompt-storage on --initial-storage-af 2310.94
  python .\reservoir_model.py --reservoir "F.E. Walter Dam" --method dkp --llm gemma4 --timestep monthly --start-date 2016-01-01 --end-date 2017-12-31 --run-mode final --llm-failure-action stop --dkp-audit-action record --prompt-storage on --initial-storage-af 2310.94
Zero-shot, Wikipedia-only version (same as the zero-shot line above plus):
  --zeroshot-knowledge wiki
Daily, numerical, one year (2016), the LLM deciding every day:
  python .\reservoir_model.py --reservoir "F.E. Walter Dam" --method zeroshot --llm gemma4 --timestep daily --start-date 2016-01-01 --end-date 2016-12-31 --run-mode final --llm-failure-action stop --zeroshot-audit-action record --prompt-storage on --initial-storage-af 2310.94 --consult-every-day
  python .\reservoir_model.py --reservoir "F.E. Walter Dam" --method dkp --llm gemma4 --timestep daily --start-date 2016-01-01 --end-date 2016-12-31 --run-mode final --llm-failure-action stop --dkp-audit-action record --prompt-storage on --initial-storage-af 2310.94 --consult-every-day
  (366 decisions each: roughly 1 h zero-shot, 3 h DKP at the current per-call times.)

DKP category runs (same periods; add --consult-every-day for daily):
  python .\reservoir_model.py --reservoir "F.E. Walter Dam" --method dkp --llm gemma4 --timestep monthly --start-date 2016-01-01 --end-date 2017-12-31 --run-mode final --llm-failure-action stop --dkp-audit-action record --prompt-storage on --initial-storage-af 2310.94 --release-categories 8
  python .\reservoir_model.py --reservoir "F.E. Walter Dam" --method dkp --llm gemma4 --timestep daily --start-date 2016-01-01 --end-date 2016-12-31 --run-mode final --llm-failure-action stop --dkp-audit-action record --prompt-storage on --initial-storage-af 2310.94 --release-categories 8 --consult-every-day

MONTE CARLO (model-default temperature, one seed per replicate), e.g. 10 runs:
  1..10 | ForEach-Object { python .\reservoir_model.py --reservoir "F.E. Walter Dam" --method zeroshot --llm gemma4 --timestep monthly --start-date 2016-01-01 --end-date 2017-12-31 --run-mode final --llm-failure-action stop --zeroshot-audit-action record --prompt-storage on --initial-storage-af 2310.94 --seed $_ }
  (Same pattern for DKP. Each seed writes its own files, tagged seed1 ... seed10.
   At default temperature a single run is ONE sample: compare conditions with
   the spread over seeds, not with one run.)

CHECK WHICH DKP A RUN USED: the first lines of every DKP prompt_samples file
show the DKP file path and its SHA256. For this package it must start with
7fb3b9e75c1d6a52.

To reproduce the baseline exactly, use the frozen baseline package.

SHA256
    f47500e3ccad55929d4069a6800ee24cb50e7605641c9ec8f03c4767d2cafc0a  benchmark_release.py
    f75f73c0e2463335619a9892bb5d44f66481f76b341a6358537e0cf30a59a0ed  dkp_llm_release.py
    4837b396dd9266241c6d2077a4f1c79e54a11d7d05149e6387ac6858ac7e3bbd  reservoir_model.py
    e17ce6310b20902c0f6f4e11bce877e90a1ddd9bf128a7ecc0e50b5d18481dff  zeroshot_llm_release.py
    7fb3b9e75c1d6a52168049afa80c527a49e606f1c0889e5d14b31f874502b206  data/DKP_FEWalter_Dam_v1.2.md
