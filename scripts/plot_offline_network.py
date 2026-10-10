"""Plot saved offline daily flows; no model or provider is executed."""
import argparse
import csv
from datetime import date
import json
from pathlib import Path


def read_flows(folder):
    flows = {}
    with (folder / "network_flows.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            flows.setdefault(row["node"], []).append((date.fromisoformat(row["date"]), float(row["routed_flow_cms"])))
    return flows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("--pulse", type=Path)
    parser.add_argument("--delayed", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Output stem for PNG/PDF/SVG")
    args = parser.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    config = json.loads((args.baseline / "experiment.json").read_text(encoding="utf-8"))["network"]
    base = read_flows(args.baseline)
    count = 1 + len(config["reservoirs"])
    rows = (count + 1) // 2
    plt.rcParams.update({"font.family": "Arial", "font.size": 11})
    fig, axes = plt.subplots(rows, 2, figsize=(12, rows*3.6), squeeze=False, constrained_layout=True)
    axes = list(axes.flat)
    outlet = config["outlet"]
    for label, folder, style in (("Baseline", args.baseline, "-"), ("Release pulse", args.pulse, "--"), ("Artificial 1-day delay", args.delayed, ":")):
        if folder is not None:
            flow = base if folder == args.baseline else read_flows(folder)
            x, y = zip(*flow[outlet])
            axes[0].plot(x, y, style, label=label, linewidth=2, marker="o", markersize=4)
    axes[0].set_title("Managed reservoir contribution outlet")
    axes[0].legend(fontsize=9)
    for ax, (name, spec) in zip(axes[1:], config["reservoirs"].items()):
        x, inflow = zip(*base[spec["inflow_node"]])
        y = [q for _, q in base[name]]
        ax.plot(x, inflow, "--", label="Natural inflow", color="#86939f", linewidth=2)
        ax.plot(x, y, "-", label="Baseline outflow", color="#1b7080", linewidth=2, marker="o", markersize=4)
        if args.pulse is not None and spec.get("operation_mode", "controlled") == "controlled":
            pulse = read_flows(args.pulse)
            ax.plot(x, [q for _, q in pulse[name]], ":", label="Pulse scenario outflow", color="#cb7433", linewidth=2)
        ax.set_title(name + (" — passive outlet" if spec.get("operation_mode") == "passive_outlet" else " — offline actions"))
        ax.legend(fontsize=9)
    for ax in axes[:count]:
        ax.set_ylabel("Daily flow (m³/s)")
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.tick_params(axis="x", labelsize=9)
        ax.grid(axis="y", color="#d9dfe4", linewidth=.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(bottom=0)
    for ax in axes[count:]:
        ax.set_visible(False)
    dates = [day for day, _ in base[outlet]]
    fig.suptitle(f"{len(dates)}-day offline network · {dates[0]} to {dates[-1]}", fontsize=17)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".pdf", ".svg"):
        path = args.output.with_suffix(suffix)
        fig.savefig(path, dpi=200)
        print(path)
    plt.close(fig)


if __name__ == "__main__":
    main()
