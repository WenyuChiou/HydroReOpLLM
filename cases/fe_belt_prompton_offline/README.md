# Seven-day offline three-reservoir case

2016-01-01–07, FE Walter / Beltzville / Prompton. `inflows.csv` is the frozen
upstream-routed natural inflow from the accepted 7/5/3-unit native models. Its
selected original rows and original source hashes are in `source_manifest.json`.
Only seven daily rows per reservoir were selected; no hydrology was rerun.

`responses_baseline.json` supplies synthetic pass-through actions for the two
controlled reservoirs. `responses_fe_pulse.json` adds 5 cms to FE Walter on
January 4. Neither contains real LLM output or an operating-policy audit.
Prompton has no response/backend: its discharge comes from outlet physics.

The Prompton rating is an approximate visual digitization of the included USACE
WCM Plate 7-2, physical PDF page187. The storage curve is corrected2014 Table7-2.
Below1125ft and above1200ft are outside the rating domain and cause a stop.
The chart does not establish low-flow outlet closure below1125ft. Uncertainty
is unquantified; this is not a certified current operating rating.

Initial storage uses the previous UTC daily mean as an explicit proxy. Beltzville
capacity/ceiling are numerical test settings, not approved operational bounds.
See `case.json` assumptions and [pre-live requirements](../../docs/offline_pre_live_acceptance.md).

The outlet represents managed-reservoir contributions only. The baseline UH is
transparent zero-delay; complete downstream reach data and lateral flows are
missing. No full-river gauge validation or joint LLM controller is claimed.
The artificial-delay result is a separate sensitivity test.

All hash-pinned data use `.gitattributes` to preserve exact bytes on checkout.
