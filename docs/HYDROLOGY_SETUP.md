# Native HydroCNHS and GWLF setup

HydroReOpLLM includes pinned HydroCNHS source for study-specific coupled work.
Configure the native model and forcing in `hydrology.yaml`, then bind routed or
constant model flows to network nodes. The public starting cases use prepared
inflows, so a coupled study must supply and validate its own hydrology files.

For daily GWLF forcing, provide a continuous date range for every modeled
subbasin and declare the expected columns and units. Basin construction,
parameter calibration, and observational validation remain study-specific;
synthetic examples only establish software behavior.

GWLF initialization includes soil, shallow groundwater, snow, and deep/baseflow
state. A daily legacy baseflow value is a discharge depth, not automatically an
hourly deep-storage state. When transferring or restarting a state, preserve
the configuration, time step, timestamp continuity, and the serialized state's
fingerprint. Do not silently fill, overlap, or reorder forcing intervals.

Enable available hydrology diagnostics when mass-balance evidence matters, and
inspect the saved residuals yourself. A finite engineering residual does not
establish calibrated runoff or operational performance. For interval semantics,
see [time scales and units](TIME_SCALES.md).
