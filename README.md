# mhurk.github.io

Personal homepage: **https://mhurk.github.io/**

A single static page (no build step) styled as a terminal window — black
background, monospace type — showing three weekly charts pulled from the
house: heat pump performance (WeHeat), battery state of charge, and grid
energy import.

## Structure

- `index.html` — the page. Fetches the three JSON files below and draws the
  charts client-side.
- `data/weheat.json`, `data/battery.json`, `data/energy.json` — one data
  point per week per series (`{"date": "YYYY-MM-DD", "value": ...}`),
  currently seeded with placeholder numbers.
- `scripts/sync_dashboards.py` — run weekly from home to append real data
  and push it here. The three `fetch_*` functions still need to be wired up
  to the real WeHeat / battery / grid sources. See `scripts/run_sync.bat`
  for the Windows Task Scheduler entry point.

## Deploying

This branch (`gh-pages`) is what GitHub Pages serves directly — pushing
here is the deploy.
