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


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_ROOT, check=True)


def main() -> int:
    today = date.today().isoformat()
    synced = sync_ops_charts()
    synced.extend(sync_battery_heatmap())

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
