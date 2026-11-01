#!/usr/bin/env python3
"""Weekly sync: republish the heat pump charts and push the site.

Run this once a week (see run_sync.bat for wiring it up to Windows Task
Scheduler). Pulls the latest binned aggregates from the house_monitor
dashboard (the consolidated home-server app that replaced the separate
Weheat_history/AlphaESS_history/Solaredge_history per-project dashboards)
and overwrites data/*.json, then commits and pushes to origin/gh-pages. Any
other change sitting in the working tree (e.g. an edit to index.html) is
committed and pushed along with it, not just the data files.
"""
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# house_monitor is a home-server app on the local network that now holds all
# the source data this page charts (it replaced the separate Weheat_history/
# AlphaESS_history/Solaredge_history dashboards). Each of its report pages
# bakes its own data into an inline <script id="report-data"
# type="application/json"> payload, same convention as this repo's own
# sibling projects used before the migration - we just read that payload
# instead of loading a local JSON file or querying a local sqlite db.
HOUSE_MONITOR_BASE_URL = "http://192.168.5.6"
REPORT_DATA_RE = re.compile(
    r'<script id="report-data" type="application/json">(.*?)</script>', re.S
)

_report_cache: dict[str, dict] = {}


def fetch_report_data(path: str) -> dict | None:
    """Fetch and parse one house_monitor report page's embedded JSON.

    Cached per path within a run, since solar/ops_report.html is read by
    both sync_temp_power_chart() and sync_inverter_mode_chart(). Returns
    None (logging to stderr) rather than raising, so one unreachable report
    doesn't abort the other syncs - same "skip and carry on" behaviour as
    the old missing-local-file checks.
    """
    if path in _report_cache:
        return _report_cache[path]

    url = f"{HOUSE_MONITOR_BASE_URL}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            html = resp.read().decode("utf-8")
    except (OSError, urllib.error.URLError) as exc:
        print(f"skipping {path}: {url} unreachable ({exc})", file=sys.stderr)
        return None

    match = REPORT_DATA_RE.search(html)
    if not match:
        print(f"skipping {path}: no report-data payload found at {url}", file=sys.stderr)
        return None

    data = json.loads(match.group(1))
    _report_cache[path] = data
    return data


# report-data key -> homepage data file. Each one is overwritten wholesale (a
# binned snapshot, not a weekly time series).
OPS_CHART_SNAPSHOTS = {
    "defrost_by_temp": "defrost_vs_temp.json",
    "defrost_by_humidity": "defrost_vs_humidity.json",
    "defrost_heatmap": "defrost_heatmap.json",
    "rpm_by_temp": "compressor_rpm.json",
}

BATTERY_HEATMAP_DAYS = 75  # ~3 months — keeps this repo's copy a stable size as the source grows


def sync_ops_charts() -> list[str]:
    """Republish the defrost/compressor-RPM characterization charts.

    Reads the already-computed binned aggregates straight out of
    house_monitor's heatpump/ops_report.html - same keys this repo used to
    read from Weheat_history's own ops_report_data.json export, now served
    over HTTP instead. Deliberately leaves out that payload's
    `headline.weather_location` (approximate home coordinates) - only the
    binned aggregates get published.
    """
    ops = fetch_report_data("heatpump/ops_report.html")
    if ops is None:
        return []

    written = []
    for ops_key, filename in OPS_CHART_SNAPSHOTS.items():
        path = DATA_DIR / filename
        path.write_text(json.dumps(ops[ops_key], indent=2) + "\n", encoding="utf-8")
        written.append(f"data/{filename}")
    return written


def sync_battery_heatmap() -> list[str]:
    """Republish the battery state-of-charge heatmap (hour x date).

    house_monitor's battery/sizing_report.html publishes its own heatmap as
    {date: {hour: soc}}; only the last ~2 months get republished here since
    the server's own window already runs several months back and the source
    keeps growing, but this repo's copy should stay a stable size.
    """
    sizing = fetch_report_data("battery/sizing_report.html")
    if sizing is None:
        return []

    cutoff = date.today() - timedelta(days=BATTERY_HEATMAP_DAYS)
    cells = []
    for day_str, hours in sizing["heatmap"].items():
        d = date.fromisoformat(day_str)
        if d < cutoff:
            continue
        for hour_str, soc in hours.items():
            cells.append({"date": day_str, "hour": int(hour_str), "soc": round(soc, 1)})
    cells.sort(key=lambda c: (c["date"], c["hour"]))

    path = DATA_DIR / "battery_heatmap.json"
    path.write_text(json.dumps(cells, indent=2) + "\n", encoding="utf-8")
    return ["data/battery_heatmap.json"]


def sync_solar_charts() -> list[str]:
    """Republish monthly solar production, grouped by year.

    house_monitor's solar/performance_report.html already buckets daily
    production into a monthly_by_year matrix (null for months not yet
    elapsed in the current year). Years that are all-zero/null are left out
    entirely (defensive; shouldn't happen with this source).
    """
    perf = fetch_report_data("solar/performance_report.html")
    if perf is None:
        return []

    mby = perf["monthly_by_year"]
    years = {
        y: [round(v, 2) if v is not None else None for v in mby["matrix"][y]]
        for y in mby["years"]
        if any(v for v in mby["matrix"][y])
    }

    path = DATA_DIR / "solar_monthly.json"
    path.write_text(json.dumps({
        "periods": mby["month_labels"],
        "years": years,
    }, indent=2) + "\n", encoding="utf-8")
    return ["data/solar_monthly.json"]


def sync_inverter_mode_chart() -> list[str]:
    """Republish the inverter operating-state split (MPPT/STARTING/THROTTLED/...).

    Reads house_monitor's solar/ops_report.html `mode` breakdown (same
    labels/counts/pct this repo used to compute from solaredge.db's own
    inverterMode telemetry) and derives the MPPT share of awake time
    (excluding SLEEPING), same "awake" definition as before.
    """
    ops = fetch_report_data("solar/ops_report.html")
    if ops is None:
        return []

    mode = ops["mode"]
    labels, counts, pct = mode["labels"], mode["counts"], mode["pct"]
    total = mode["total"]
    sleeping = counts[labels.index("SLEEPING")] if "SLEEPING" in labels else 0
    mppt = counts[labels.index("MPPT")] if "MPPT" in labels else 0
    awake = total - sleeping

    path = DATA_DIR / "inverter_mode.json"
    path.write_text(json.dumps({
        "states": [
            {"state": label, "count": count, "pct": round(p, 2)}
            for label, count, p in zip(labels, counts, pct)
        ],
        "total_samples": total,
        "mppt_pct_awake": round(mppt / awake * 100, 2) if awake else None,
    }, indent=2) + "\n", encoding="utf-8")
    return ["data/inverter_mode.json"]


def sync_temp_power_chart() -> list[str]:
    """Republish the inverter temperature-vs-power chart (THROTTLED highlighted).

    house_monitor's solar/ops_report.html already carries the sparse MPPT
    density grid and the list of individual THROTTLED samples (its own
    nx/ny resolution, not this repo's former coarser rebuild), plus the
    inverter's nameplate AC rating - no local regex-on-model-string parsing
    needed any more since the server already resolved it to a number.
    """
    ops = fetch_report_data("solar/ops_report.html")
    if ops is None:
        return []

    tp = ops["temp_power"]
    nameplate_w = ops["equipment"][0]["nameplate_w"] if ops.get("equipment") else None

    path = DATA_DIR / "temp_power.json"
    path.write_text(json.dumps({
        "nx": tp["nx"], "ny": tp["ny"],
        "tmax": round(tp["tmax"], 1), "pmax": round(tp["pmax"], 1),
        "maxcount": tp["maxcount"], "cells": tp["cells"],
        "throttled_points": [[round(t, 1), round(p, 1)] for t, p in tp["throttled_points"]],
        "n_mppt": tp["n_mppt"], "n_throttled": tp["n_throttled"],
        "nameplate_w": nameplate_w,
    }, indent=2) + "\n", encoding="utf-8")
    return ["data/temp_power.json"]


def update_last_updated(today: str) -> None:
    """Stamp the footer's last-updated date with today's sync date."""
    path = REPO_ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    html = re.sub(
        r'(<span id="last-updated">)[^<]*(</span>)',
        rf"\g<1>{today}\g<2>",
        html,
    )
    path.write_text(html, encoding="utf-8")


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_ROOT, check=True)


def main() -> int:
    today = date.today().isoformat()
    update_last_updated(today)
    synced = sync_ops_charts()
    synced.extend(sync_battery_heatmap())
    synced.extend(sync_solar_charts())
    synced.extend(sync_temp_power_chart())
    synced.extend(sync_inverter_mode_chart())

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
