#!/usr/bin/env python3
"""Weekly sync: republish the heat pump charts and push the site.

Run this once a week (see run_sync.bat for wiring it up to Windows Task
Scheduler). Pulls the latest binned aggregates from the sibling
Weheat_history project and overwrites data/*.json, then commits and pushes
to origin/gh-pages. Any other change sitting in the working tree (e.g. an
edit to index.html) is committed and pushed along with it, not just the
data files.
"""
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Sibling project that already computes these as binned aggregates from the
# heat pump's own history (data/weheat.db) — see its export_ops_report_data.py.
WEHEAT_OPS_REPORT = Path(r"D:\Projects\Weheat_history\data\ops_report_data.json")

# ops_report_data.json key -> homepage data file. Each one is overwritten
# wholesale (a binned snapshot, not a weekly time series), and deliberately
# excludes that file's `headline.weather_location` (approximate home
# coordinates) — only the binned aggregates get published.
OPS_CHART_SNAPSHOTS = {
    "defrost_by_temp": "defrost_vs_temp.json",
    "defrost_by_humidity": "defrost_vs_humidity.json",
    "defrost_heatmap": "defrost_heatmap.json",
    "rpm_by_temp": "compressor_rpm.json",
}

# Sibling project for the home battery. It has no export-to-JSON step of its
# own (sizing_report.html bakes the heatmap straight into inline SVG), so this
# reuses its sizing.load() — same hourly-mean-SoC-by-(date, hour) aggregation
# its own report charts — rather than re-deriving the local-time bucketing.
ALPHAESS_SRC = Path(r"D:\Projects\AlphaESS_history\src")
ALPHAESS_DB = Path(r"D:\Projects\AlphaESS_history\data\alphaess.db")
BATTERY_HEATMAP_DAYS = 75  # ~3 months — keeps this repo's copy a stable size as the source grows

# Sibling project for solar production. Its own export_performance_data.py
# computes a monthly_by_year aggregate, so this queries solaredge.db
# directly — same SQL its fetch_daily() uses (sum of the 'Production' meter
# per day) — just bucketed by month here. Replaced the earlier \\BigStation
# Home Assistant CSV export, which wasn't accurate/complete enough (HA's own
# solar_production history).
SOLAREDGE_DB = Path(r"D:\Projects\Solaredge_history\solaredge.db")
MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# Grid resolution for the temperature-vs-power density chart (same sparse
# [xi,yi,count] shape as the sibling project's own ops_analysis.py/
# fetch_temp_power(), just a coarser grid sized for a small card).
TEMP_POWER_NX = 60
TEMP_POWER_NY = 50


def sync_ops_charts() -> list[str]:
    """Republish the defrost/compressor-RPM characterization charts.

    Reads the already-computed binned aggregates from the sibling
    Weheat_history project's ops report export. Does not trigger that
    project's own data refresh — run its update_weheat_data.bat first if you
    want fresher numbers.
    """
    if not WEHEAT_OPS_REPORT.exists():
        print(f"skipping ops charts: {WEHEAT_OPS_REPORT} not found", file=sys.stderr)
        return []

    ops = json.loads(WEHEAT_OPS_REPORT.read_text(encoding="utf-8"))
    written = []
    for ops_key, filename in OPS_CHART_SNAPSHOTS.items():
        path = DATA_DIR / filename
        path.write_text(json.dumps(ops[ops_key], indent=2) + "\n", encoding="utf-8")
        written.append(f"data/{filename}")
    return written


def sync_battery_heatmap() -> list[str]:
    """Republish the battery state-of-charge heatmap (hour x date).

    Calls the sibling AlphaESS_history project's own sizing.load() against
    its data/alphaess.db, then republishes just the heatmap (not the
    full/empty-day stats sizing_report.html also computes).
    """
    if not ALPHAESS_DB.exists() or not ALPHAESS_SRC.exists():
        print(f"skipping battery heatmap: {ALPHAESS_DB} or {ALPHAESS_SRC} not found", file=sys.stderr)
        return []

    sys.path.insert(0, str(ALPHAESS_SRC))
    import sqlite3
    from alphaess_history import sizing  # type: ignore

    conn = sqlite3.connect(ALPHAESS_DB)
    try:
        _, heatmap = sizing.load(conn)
    finally:
        conn.close()

    # Only publish the last ~2 months here — the source db keeps growing, but
    # this repo's copy should stay a stable size.
    cutoff = date.today() - timedelta(days=BATTERY_HEATMAP_DAYS)
    heatmap = {(d, h): v for (d, h), v in heatmap.items() if d >= cutoff}

    cells = [
        {"date": d.isoformat(), "hour": h, "soc": round(v, 1)}
        for (d, h), v in sorted(heatmap.items())
    ]
    path = DATA_DIR / "battery_heatmap.json"
    path.write_text(json.dumps(cells, indent=2) + "\n", encoding="utf-8")
    return ["data/battery_heatmap.json"]


def sync_solar_charts() -> list[str]:
    """Republish monthly solar production, grouped by year.

    Queries solaredge.db directly for daily production (same SQL as the
    sibling project's own fetch_daily()), then buckets those daily kWh
    figures into calendar months here. Years that are all-zero are left out
    entirely (defensive; shouldn't happen with this source, unlike the old
    CSV one).
    """
    if not SOLAREDGE_DB.exists():
        print(f"skipping solar charts: {SOLAREDGE_DB} not found", file=sys.stderr)
        return []

    import sqlite3
    conn = sqlite3.connect(SOLAREDGE_DB)
    try:
        daily = conn.execute(
            "SELECT substr(timestamp,1,10) AS day, SUM(value)/1000.0 AS kwh "
            "FROM energy_details WHERE meter_type='Production' GROUP BY day ORDER BY day"
        ).fetchall()
    finally:
        conn.close()

    monthly_by_year: dict[str, list[float | None]] = {}

    for day_str, kwh in daily:
        d = date.fromisoformat(day_str)
        month_year = str(d.year)
        row = monthly_by_year.setdefault(month_year, [None] * 12)
        row[d.month - 1] = (row[d.month - 1] or 0) + kwh

    monthly_years = sorted(y for y, vals in monthly_by_year.items()
                            if any(v is not None and v > 0 for v in vals))
    path = DATA_DIR / "solar_monthly.json"
    path.write_text(json.dumps({
        "periods": MONTH_LABELS,
        "years": {y: [round(v, 2) if v is not None else None for v in monthly_by_year[y]]
                  for y in monthly_years},
    }, indent=2) + "\n", encoding="utf-8")
    return ["data/solar_monthly.json"]


def sync_temp_power_chart() -> list[str]:
    """Republish the inverter temperature-vs-power chart (THROTTLED highlighted).

    Queries solaredge.db directly — same joins as the sibling project's own
    ops_analysis.py/fetch_temp_power(), which has no standalone JSON export
    of its own (baked straight into ops_report.html's inline <script>
    payload) — rebuilding the sparse MPPT density grid and the list of
    individual THROTTLED samples here, at a coarser resolution sized for a
    small card rather than that report's full-width chart.
    """
    if not SOLAREDGE_DB.exists():
        print(f"skipping temp/power chart: {SOLAREDGE_DB} not found", file=sys.stderr)
        return []

    import re
    import sqlite3
    conn = sqlite3.connect(SOLAREDGE_DB)
    try:
        mppt_rows = conn.execute("""
            SELECT t.value, p.value
            FROM equipment_telemetry m
            JOIN equipment_telemetry t ON t.timestamp=m.timestamp AND t.serial_number=m.serial_number AND t.field='temperature'
            JOIN equipment_telemetry p ON p.timestamp=m.timestamp AND p.serial_number=m.serial_number AND p.field='totalActivePower'
            WHERE m.field='inverterMode' AND m.value='MPPT'
        """).fetchall()
        throttled_rows = conn.execute("""
            SELECT t.value, p.value
            FROM equipment_telemetry m
            JOIN equipment_telemetry t ON t.timestamp=m.timestamp AND t.serial_number=m.serial_number AND t.field='temperature'
            JOIN equipment_telemetry p ON p.timestamp=m.timestamp AND p.serial_number=m.serial_number AND p.field='totalActivePower'
            WHERE m.field='inverterMode' AND m.value='THROTTLED'
        """).fetchall()
        model_row = conn.execute(
            "SELECT model FROM equipment WHERE equipment_type='inverters' LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    if not mppt_rows:
        print("skipping temp/power chart: no MPPT telemetry found", file=sys.stderr)
        return []

    nameplate_match = re.match(r"SE(\d+)", model_row[0]) if model_row and model_row[0] else None
    nameplate_w = int(nameplate_match.group(1)) if nameplate_match else None

    nx, ny = TEMP_POWER_NX, TEMP_POWER_NY
    all_rows = mppt_rows + throttled_rows
    tmax = max(r[0] for r in all_rows) * 1.05
    pmax = max(r[1] for r in all_rows) * 1.05
    grid: dict[tuple[int, int], int] = {}
    for t, p in mppt_rows:
        xi = min(nx - 1, int(t / tmax * nx))
        yi = min(ny - 1, int(p / pmax * ny))
        grid[(xi, yi)] = grid.get((xi, yi), 0) + 1
    cells = [[xi, yi, c] for (xi, yi), c in grid.items()]
    maxcount = max(c for _, _, c in cells) if cells else 0

    path = DATA_DIR / "temp_power.json"
    path.write_text(json.dumps({
        "nx": nx, "ny": ny,
        "tmax": round(tmax, 1), "pmax": round(pmax, 1),
        "maxcount": maxcount, "cells": cells,
        "throttled_points": [[round(t, 1), round(p, 1)] for t, p in throttled_rows],
        "n_mppt": len(mppt_rows), "n_throttled": len(throttled_rows),
        "nameplate_w": nameplate_w,
    }, indent=2) + "\n", encoding="utf-8")
    return ["data/temp_power.json"]


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_ROOT, check=True)


def main() -> int:
    today = date.today().isoformat()
    synced = sync_ops_charts()
    synced.extend(sync_battery_heatmap())
    synced.extend(sync_solar_charts())
    synced.extend(sync_temp_power_chart())

    # Stage everything, not just the data files — picks up any other edits
    # (index.html, scripts, etc.) sitting in the working tree.
    git("add", "-A")
    staged_clean = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT
    )
    if staged_clean.returncode == 0:
        print("nothing to sync (no data updates and no other changes)")
        return 0

    if synced:
        message = f"Weekly sync: {today} ({', '.join(synced)})"
    else:
        message = f"Weekly sync: {today} (site changes only)"

    git("commit", "-m", message)
    git("push")
    print(f"committed and pushed changes as of {today}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
