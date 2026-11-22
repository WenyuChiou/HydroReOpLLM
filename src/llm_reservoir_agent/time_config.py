"""Explicit simulation resolution and derived output resolution for YAML runs."""
import csv
import io
from pathlib import Path

from .time_axis import TimeAxis


def validate_time_settings(value, network, *, allow_absent=True):
    """Return a checked copy; absent settings preserve legacy run behavior."""
    if value is None and allow_absent:
        return None
    if not isinstance(value, dict) or set(value) != {"simulation_step", "output_step"}:
        raise ValueError("time requires exactly simulation_step and output_step")
    simulation = value["simulation_step"]
    output = value["output_step"]
    if simulation not in ("daily", "hourly") or output not in ("hourly", "daily", "monthly"):
        raise ValueError("simulation_step must be daily/hourly; output_step hourly/daily/monthly")
    seconds = {"daily": 86400, "hourly": 3600}[simulation]
    clock = TimeAxis.from_network(network)
    if clock.dt_seconds != seconds:
        raise ValueError("simulation_step conflicts with network/routing dt_seconds")
    if simulation == "daily" and output == "hourly":
        raise ValueError("output_step cannot be finer than simulation_step")
    for name, reservoir in network["reservoirs"].items():
        duration = reservoir["physical"].get("dt_seconds", 86400)
        if isinstance(duration, bool) or duration != seconds:
            raise ValueError("reservoir timestep conflicts with simulation_step: " + name)
    return dict(value)


def temporal_tables(output, clock, settings):
    """Recompute derived tables from preserved native CSVs, without changing them."""
    if settings is None or settings["output_step"] == settings["simulation_step"]:
        return {}
    from .temporal_output import aggregate_network_flows, aggregate_reservoir_trajectory
    frequency = settings["output_step"]
    tables = {}
    for name, aggregate in (("network_flows", aggregate_network_flows),
                            ("reservoir_trajectory", aggregate_reservoir_trajectory)):
        with (Path(output) / (name + ".csv")).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if clock.legacy_daily and name == "reservoir_trajectory":
            # Historical trajectory exports use a midnight datetime in the date
            # column. Adapt that exact suffix only; never truncate arbitrary times.
            for row in rows:
                row[clock.key] = row[clock.key].removesuffix("T00:00:00")
        tables[f"{name}_{frequency}.csv"] = aggregate(rows, time_key=clock.key,
            dt_seconds=clock.dt_seconds, frequency=frequency)
    return tables


def temporal_csv_bytes(table):
    """Canonical CSV bytes matching the existing native CSV writer."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(table[0]))
    writer.writeheader()
    writer.writerows(table)
    return stream.getvalue().encode("utf-8")
