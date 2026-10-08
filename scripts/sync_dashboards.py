#!/usr/bin/env python3
"""Weekly sync: pull WeHeat / battery / grid numbers and publish them to the site.

Run this once a week (see run_sync.bat for wiring it up to Windows Task
Scheduler). Each run appends one data point per series to data/*.json, then
commits and pushes to origin/gh-pages.
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
MAX_POINTS = 52  # keep roughly a year of weekly points


def fetch_weheat_cop() -> float:
    """Return this week's average heat pump coefficient of performance.

    TODO: replace with a real call to the WeHeat data source once you've
    picked one (their API, a local export, or a Home Assistant integration).
    """
    raise NotImplementedError("wire up the real WeHeat data source")


def fetch_battery_soc() -> float:
    """Return this week's average battery state of charge, in percent.

    TODO: replace with a real call to your battery monitoring source.
    """
    raise NotImplementedError("wire up the real battery data source")


def fetch_grid_import_kwh() -> float:
    """Return this week's total grid import, in kWh.

    TODO: replace with a real call to your energy monitoring source.
    """
    raise NotImplementedError("wire up the real grid import data source")


SERIES = {
    "weheat.json": fetch_weheat_cop,
    "battery.json": fetch_battery_soc,
    "energy.json": fetch_grid_import_kwh,
}


def append_point(path: Path, value: float, today: str) -> None:
    points = json.loads(path.read_text(encoding="utf-8"))
    if points and points[-1]["date"] == today:
        points[-1]["value"] = value  # re-run same day: overwrite, don't duplicate
    else:
        points.append({"date": today, "value": value})
    points = points[-MAX_POINTS:]
    path.write_text(json.dumps(points, indent=2) + "\n", encoding="utf-8")


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_ROOT, check=True)


def main() -> int:
    today = date.today().isoformat()
    changed = []

    for filename, fetch in SERIES.items():
        path = DATA_DIR / filename
        try:
            value = fetch()
        except NotImplementedError as exc:
            print(f"skipping {filename}: {exc}", file=sys.stderr)
            continue
        append_point(path, value, today)
        changed.append(f"data/{filename}")

    if not changed:
        print("nothing to sync (no data sources wired up yet)")
        return 0

    git("add", *changed)
    staged_clean = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT
    )
    if staged_clean.returncode == 0:
        print("no new data this week")
        return 0

    git("commit", "-m", f"Weekly data sync: {today}")
    git("push")
    print(f"synced and pushed: {', '.join(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
