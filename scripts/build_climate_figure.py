"""Build the F.E. Walter climate summary from accepted saved forcing.

This script aggregates only; it does not recalculate PET, resample weather, or
run HydroCNHS.  It verifies the accepted forcing and area-table hashes before
writing a monthly CSV, provenance JSON, and publication-size figure assets.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
import struct
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
FORCING = ROOT / "data/accepted/fe_walter_forcing_1989_2025.csv.gz"
AREAS = ROOT / "docs/results/fe_walter/hydrology/subcatchments.csv"
OUTPUT = ROOT / "docs/results/fe_walter/hydrology/climate"
MONTHLY = OUTPUT / "fe_walter_climate_monthly_1989_2025.csv"
FIGURE_STEM = OUTPUT / "fe_walter_climate_1989_2025"
PROVENANCE = OUTPUT / "provenance.json"

EXPECTED_FORCING_SHA256 = "2d030c5e53b15ba5ef7dcb0979dd223889870e6f9a41396bb3b1e2adb4e6a826"
EXPECTED_AREAS_SHA256 = "6c9fcaf49575fd2436f9157bf7e41cf603e73234211e485ee2850ce23391d919"
EXPECTED_START = date(1989, 1, 1)
EXPECTED_END = date(2025, 12, 31)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_areas() -> dict[str, float]:
    if sha256(AREAS) != EXPECTED_AREAS_SHA256:
        raise ValueError(f"Unexpected area-table bytes: {AREAS}")
    with AREAS.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    areas = {row["subcatchment"]: float(row["area_ha"]) for row in rows}
    if len(areas) != 7 or len(rows) != len(areas):
        raise ValueError("The area table must contain seven unique physical units")
    if any(not math.isfinite(value) or value <= 0 for value in areas.values()):
        raise ValueError("All physical-unit areas must be finite and positive")
    return areas


def expected_dates() -> list[date]:
    days = (EXPECTED_END - EXPECTED_START).days + 1
    return [EXPECTED_START + timedelta(days=offset) for offset in range(days)]


def aggregate(areas: dict[str, float]) -> tuple[list[dict[str, object]], dict[str, object]]:
    forcing_hash = sha256(FORCING)
    if forcing_hash != EXPECTED_FORCING_SHA256:
        raise ValueError(f"Unexpected accepted-forcing bytes: {FORCING}")

    required = {
        "date",
        "subbasin_id",
        "precipitation_mm",
        "temperature_c",
        "pet_cm",
        "forcing_source",
    }
    total_area = math.fsum(areas.values())
    weights = {unit: area / total_area for unit, area in areas.items()}
    by_day: dict[date, dict[str, tuple[float, float, float]]] = defaultdict(dict)
    source_counts: Counter[str] = Counter()
    row_count = 0

    with gzip.open(FORCING, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"Forcing columns must include {sorted(required)}")
        for row in reader:
            row_count += 1
            day = date.fromisoformat(row["date"])
            unit = row["subbasin_id"]
            if unit not in areas:
                raise ValueError(f"Unexpected forcing unit: {unit}")
            if unit in by_day[day]:
                raise ValueError(f"Duplicate forcing pair: {day}, {unit}")
            precipitation = float(row["precipitation_mm"])
            temperature = float(row["temperature_c"])
            pet_cm = float(row["pet_cm"])
            if not all(math.isfinite(v) for v in (precipitation, temperature, pet_cm)):
                raise ValueError(f"Non-finite forcing value: {day}, {unit}")
            if precipitation < 0 or pet_cm < 0:
                raise ValueError(f"Negative precipitation or PET: {day}, {unit}")
            by_day[day][unit] = (precipitation, pet_cm * 10.0, temperature)
            source_counts[row["forcing_source"]] += 1

    dates = expected_dates()
    if sorted(by_day) != dates:
        raise ValueError("Forcing dates do not exactly cover 1989-01-01 through 2025-12-31")
    units = set(areas)
    for day in dates:
        if set(by_day[day]) != units:
            missing = sorted(units - set(by_day[day]))
            extra = sorted(set(by_day[day]) - units)
            raise ValueError(f"Incomplete unit coverage on {day}: missing={missing}, extra={extra}")

    monthly_values: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"precipitation": [], "pet": [], "temperature": []}
    )
    monthly_days: Counter[str] = Counter()
    for day in dates:
        key = day.strftime("%Y-%m")
        daily_precipitation = math.fsum(
            weights[unit] * by_day[day][unit][0] for unit in sorted(units)
        )
        daily_pet = math.fsum(weights[unit] * by_day[day][unit][1] for unit in sorted(units))
        daily_temperature = math.fsum(
            weights[unit] * by_day[day][unit][2] for unit in sorted(units)
        )
        monthly_values[key]["precipitation"].append(daily_precipitation)
        monthly_values[key]["pet"].append(daily_pet)
        monthly_values[key]["temperature"].append(daily_temperature)
        monthly_days[key] += 1

    rows: list[dict[str, object]] = []
    for month in sorted(monthly_values):
        values = monthly_values[month]
        rows.append(
            {
                "month": month,
                "days": monthly_days[month],
                "precipitation_mm": math.fsum(values["precipitation"]),
                "pet_mm": math.fsum(values["pet"]),
                "temperature_c": math.fsum(values["temperature"]) / monthly_days[month],
            }
        )

    leap_days = sum(1 for day in dates if day.month == 2 and day.day == 29)
    if len(rows) != 444 or len(dates) != 13_514 or leap_days != 9:
        raise ValueError("Unexpected calendar coverage")
    if row_count != len(dates) * len(units):
        raise ValueError("Unexpected forcing row count")

    checks = {
        "forcing_rows": row_count,
        "physical_units": len(units),
        "days_per_unit": len(dates),
        "start_date": dates[0].isoformat(),
        "end_date": dates[-1].isoformat(),
        "leap_days": leap_days,
        "months": len(rows),
        "area_ha": total_area,
        "area_km2": total_area / 100.0,
        "unit_areas_ha": {unit: areas[unit] for unit in sorted(units)},
        "forcing_source_label_counts": dict(sorted(source_counts.items())),
    }
    return rows, checks


def write_monthly(rows: list[dict[str, object]]) -> None:
    with MONTHLY.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["month", "days", "precipitation_mm", "pet_mm", "temperature_c"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "month": row["month"],
                    "days": row["days"],
                    "precipitation_mm": f"{float(row['precipitation_mm']):.10f}",
                    "pet_mm": f"{float(row['pet_mm']):.10f}",
                    "temperature_c": f"{float(row['temperature_c']):.10f}",
                }
            )


def draw(rows: list[dict[str, object]]) -> None:
    font_path = mpl.font_manager.findfont("Arial", fallback_to_default=False)
    if not font_path:
        raise RuntimeError("Arial is required for this figure")
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "fe-walter-climate-1989-2025",
        }
    )
    dates = [date.fromisoformat(f"{row['month']}-01") for row in rows]
    precipitation = [float(row["precipitation_mm"]) for row in rows]
    pet = [float(row["pet_mm"]) for row in rows]
    temperature = [float(row["temperature_c"]) for row in rows]

    width_in = 180.0 / 25.4
    fig, axes = plt.subplots(3, 1, figsize=(width_in, 6.7), sharex=True)
    colors = {"precipitation": "#2166AC", "pet": "#D97706", "temperature": "#B2182B"}
    axes[0].plot(dates, precipitation, color=colors["precipitation"], linewidth=0.8)
    axes[0].set_ylabel("Precipitation\n(mm/month)")
    axes[0].set_title("F.E. Walter catchment climate forcing, 1989–2025", loc="left", weight="bold")
    axes[1].plot(dates, pet, color=colors["pet"], linewidth=0.8)
    axes[1].set_ylabel("PET\n(mm/month)")
    axes[2].plot(dates, temperature, color=colors["temperature"], linewidth=0.8)
    axes[2].axhline(0, color="#777777", linewidth=0.6, zorder=0)
    axes[2].set_ylabel("Temperature\n(°C)")
    axes[2].set_xlabel("Year")
    axes[2].xaxis.set_major_locator(mdates.YearLocator(5))
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for axis in axes:
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.5)
        axis.spines[["top", "right"]].set_visible(False)
        axis.margins(x=0)
    fig.align_ylabels(axes)
    fig.tight_layout(h_pad=0.9)
    fig.savefig(FIGURE_STEM.with_suffix(".png"), dpi=600, metadata={"Software": f"Matplotlib {mpl.__version__}"})
    fig.savefig(
        FIGURE_STEM.with_suffix(".pdf"),
        metadata={"Title": "F.E. Walter catchment climate forcing, 1989-2025", "CreationDate": None, "ModDate": None},
    )
    fig.savefig(
        FIGURE_STEM.with_suffix(".svg"),
        metadata={"Title": "F.E. Walter catchment climate forcing, 1989-2025", "Date": None},
    )
    svg_path = FIGURE_STEM.with_suffix(".svg")
    svg_path.write_bytes(("\n".join(line.rstrip() for line in
                         svg_path.read_text(encoding="utf-8").splitlines()) + "\n").encode("utf-8"))
    plt.close(fig)


def verify_outputs() -> dict[str, object]:
    with MONTHLY.open(encoding="utf-8", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    if len(csv_rows) != 444:
        raise ValueError("Monthly CSV must contain 444 data rows")

    png = FIGURE_STEM.with_suffix(".png").read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG signature is invalid")
    png_width, png_height = struct.unpack(">II", png[16:24])
    if png_width not in {4251, 4252} or png_height != 4020:
        raise ValueError(f"Unexpected 600 dpi PNG dimensions: {png_width}x{png_height}")

    svg = FIGURE_STEM.with_suffix(".svg").read_text(encoding="utf-8")
    width_match = re.search(r'<svg[^>]+width="([0-9.]+)pt"', svg)
    if width_match is None:
        raise ValueError("SVG width is unavailable")
    svg_width_mm = float(width_match.group(1)) * 25.4 / 72.0
    if not math.isclose(svg_width_mm, 180.0, abs_tol=0.01):
        raise ValueError(f"Unexpected SVG width: {svg_width_mm} mm")
    if "<text" not in svg or "Arial" not in svg:
        raise ValueError("SVG must retain editable Arial text")

    pdf = FIGURE_STEM.with_suffix(".pdf").read_bytes()
    if not pdf.startswith(b"%PDF-") or b"/Type /Page" not in pdf:
        raise ValueError("PDF output is invalid")
    return {
        "monthly_csv_rows": len(csv_rows),
        "png_pixels": [png_width, png_height],
        "png_dpi": 600,
        "svg_width_mm": svg_width_mm,
        "svg_text_editable": True,
        "minimum_font_points": 9,
        "pdf_header": pdf[:8].decode("ascii"),
    }


def write_provenance(
    rows: list[dict[str, object]], checks: dict[str, object], output_checks: dict[str, object]
) -> None:
    outputs = [MONTHLY, FIGURE_STEM.with_suffix(".png"), FIGURE_STEM.with_suffix(".pdf"), FIGURE_STEM.with_suffix(".svg")]
    payload = {
        "schema_version": "fe-walter-climate-figure.v1",
        "purpose": "Display-only aggregation of accepted saved forcing; no PET recalculation, weather resampling, download, calibration, or hydrological/reservoir simulation.",
        "aggregation": {
            "spatial": "For each day and variable, sum the seven physical-unit values multiplied by unit area / total physical-unit area.",
            "monthly_precipitation": "Sum area-weighted daily precipitation; mm/month.",
            "monthly_pet": "Convert saved PET from cm/day to mm/day by multiplying by 10, then sum area-weighted daily values; mm/month.",
            "monthly_temperature": "Arithmetic mean of area-weighted daily mean temperature; degree C.",
            "rounding": "Calculations use binary64 and math.fsum; the CSV writes 10 decimal places.",
        },
        "coverage_checks": checks,
        "output_checks": output_checks,
        "numeric_summary": {
            "precipitation_mm_total": math.fsum(float(row["precipitation_mm"]) for row in rows),
            "pet_mm_total": math.fsum(float(row["pet_mm"]) for row in rows),
            "temperature_c_monthly_mean": math.fsum(float(row["temperature_c"]) for row in rows) / len(rows),
            "first_month": rows[0],
            "last_month": rows[-1],
        },
        "inputs": {
            str(FORCING.relative_to(ROOT)).replace("\\", "/"): {
                "bytes": FORCING.stat().st_size,
                "sha256": sha256(FORCING),
            },
            str(AREAS.relative_to(ROOT)).replace("\\", "/"): {
                "bytes": AREAS.stat().st_size,
                "sha256": sha256(AREAS),
            },
        },
        "builder": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(Path(__file__).resolve()),
            "matplotlib": mpl.__version__,
            "font": "Arial",
            "figure_width_mm": 180,
            "png_dpi": 600,
        },
        "outputs": {
            str(path.relative_to(ROOT)).replace("\\", "/"): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in outputs
        },
    }
    with PROVENANCE.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    areas = read_areas()
    rows, checks = aggregate(areas)
    write_monthly(rows)
    draw(rows)
    output_checks = verify_outputs()
    write_provenance(rows, checks, output_checks)
    print(
        json.dumps(
            {"outputs": 5, "coverage_checks": checks, "output_checks": output_checks},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
