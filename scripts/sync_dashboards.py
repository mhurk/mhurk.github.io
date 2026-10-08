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
from datetime import date
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


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_ROOT, check=True)


def main() -> int:
    today = date.today().isoformat()
    synced = sync_ops_charts()

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
