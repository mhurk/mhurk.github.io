# mhurk.github.io

Personal homepage: **https://mhurk.github.io/**

A single static page (no build step) styled as a terminal window — black
background, monospace type — charting heat pump operational data (defrost
cycles binned by outdoor temperature and by relative humidity, a defrost
density map across both, and compressor RPM binned by outdoor temperature),
home battery data (state of charge by hour and date), and solar production
(weekly/monthly radar plots, one line per year).

## Structure

- `index.html` — the markup.
- `css/site.css` — all styling, reusable by future pages.
- `js/charts.js` — fetches the JSON files below and draws the charts
  client-side (plain SVG, no charting library), also reusable by future pages.
- `data/defrost_vs_temp.json`, `data/defrost_vs_humidity.json`,
  `data/defrost_heatmap.json`, `data/compressor_rpm.json` — binned
  aggregates, not time series, sourced from the sibling `Weheat_history`
  project's own `export_ops_report_data.py` output.
- `data/battery_heatmap.json` — mean state of charge per (date, hour) cell,
  sourced from the sibling `AlphaESS_history` project's `sizing.load()`.
- `data/solar_weekly.json`, `data/solar_monthly.json` — solar production
  grouped by year, read straight from the `solar_production_weekly/monthly.csv`
  exports on `\\BigStation`. Years that predate the panels (all-zero) are
  left out.
- `scripts/sync_dashboards.py` — run weekly from home: republishes all of
  the above (stripping the Weheat export's approximate home location), then
  commits and pushes anything changed in the working tree. See
  `scripts/run_sync.bat` for the Windows Task Scheduler entry point.

## Deploying

This branch (`gh-pages`) is what GitHub Pages serves directly — pushing
here is the deploy.

## Running locally

Double-clicking `index.html` (a `file:// URL`) won't show the charts, because the page fetches the JSON data files (data/*.json) with fetch(), and browsers block fetch() of local files for security reasons under `file://`. It needs an actual HTTP server, even a trivial local one.

Open a terminal in the repo folder and run: 

<code>python -m http.server 8000</code>

then open `http://localhost:8000/index.html` in your browser. That serves the folder over real HTTP, so the fetch() calls succeed and you'll see the charts exactly as they render on the live site. Any port number works; just pick one that's free. Stop the server afterward with Ctrl+C (or close the terminal).