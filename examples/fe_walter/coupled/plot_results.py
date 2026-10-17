"""Plot the selected daily teaching table; never run hydrology or an LLM."""
import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New figure directory")
    args = parser.parse_args()
    table = pd.read_csv(Path(__file__).parent / "outputs/daily.csv", parse_dates=["date"])
    args.output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "pdf.fonttype": 42})
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, layout="constrained")
    methods = [("rule", "Rule-based", "#687C87"),
               ("llm_available", "LLM with available information", "#C17852"),
               ("llm_knowledge", "LLM with retrieved knowledge", "#2D8679")]
    for method, label, color in methods:
        daily = table[table.method == method]
        axes[0].plot(daily.date, daily.pool_elevation_end_ft, label=label, color=color, lw=1.35)
        axes[1].plot(daily.date, daily.controlled_release_cms, color=color, lw=1.15)
    for level in (1300, 1370):
        axes[0].axhline(level, color="#9AA29D", lw=.75, ls="--", zorder=0)
    axes[0].set_ylabel("End-of-day pool elevation\n(ft NGVD 29)")
    axes[1].set_ylabel("Controlled release\n(m³/s)")
    axes[1].set_ylim(bottom=0)
    for axis, label in zip(axes, ["a", "b"]):
        axis.text(.01, .96, label, transform=axis.transAxes, va="top", fontweight="bold")
        axis.grid(axis="y", color="#DDE4E0", lw=.6)
        axis.margins(x=.01)
    axes[0].legend(loc="upper center", bbox_to_anchor=(.5, 1.19), ncol=3, frameon=False, fontsize=9)
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[1].set_xlabel("2016")
    for extension in ("png", "svg", "pdf"):
        target = args.output / ("pool_release." + extension)
        fig.savefig(target, dpi=300, facecolor="white")
        if extension == "svg":
            target.write_bytes(b"\n".join(line.rstrip() for line in target.read_bytes().splitlines()) + b"\n")
    plt.close(fig)


if __name__ == "__main__":
    main()
