# mhurk.github.io

Personal homepage: **https://mhurk.github.io/**

A single static page (no build step) styled as a terminal window — black
background, monospace type — charting heat pump operational data: defrost
cycles binned by outdoor temperature and by relative humidity, a defrost
density map across both, and compressor RPM binned by outdoor temperature.

## Structure

- `index.html` — the markup.
- `css/site.css` — all styling, reusable by future pages.
- `js/charts.js` — fetches the four JSON files below and draws the charts
  client-side (plain SVG, no charting library), also reusable by future pages.
- `data/defrost_vs_temp.json`, `data/defrost_vs_humidity.json`,
  `data/defrost_heatmap.json`, `data/compressor_rpm.json` — binned
  aggregates, not time series. Each one is overwritten wholesale by the sync
  script below, sourced from the sibling `Weheat_history` project's own
  `export_ops_report_data.py` output.
- `scripts/sync_dashboards.py` — run weekly from home: reads
  `D:\Projects\Weheat_history\data\ops_report_data.json` and republishes the
  four chart snapshots (stripping that file's approximate home location),
  then commits and pushes anything changed in the working tree. See
  `scripts/run_sync.bat` for the Windows Task Scheduler entry point.

## Deploying

This branch (`gh-pages`) is what GitHub Pages serves directly — pushing
here is the deploy.
