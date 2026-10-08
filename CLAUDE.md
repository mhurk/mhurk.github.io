# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`mhurk.github.io` — a personal homepage served directly by GitHub Pages:
https://mhurk.github.io/. Single static page, no framework, no build step,
no package manager. Styled as a terminal window (black background,
monospace type) and shows three weekly line charts — heat pump performance
(WeHeat), battery state of charge, and grid energy import — rendered
client-side from JSON data files.

## Branch layout (important)

- **`gh-pages`** is the branch actually served by GitHub Pages, and the one
  this working tree is normally checked out to. Everything lives here:
  `index.html`, `css/`, `data/`, `scripts/`.
- **`main`** holds only `README.md` and `.gitignore`; its README just points
  readers to the `gh-pages` branch. There is no separate source/build
  branch — `gh-pages` content is edited directly and pushed, and that push
  *is* the deploy.

## Commands

No install, build, lint, or test step — it's plain HTML/CSS/JS plus a
stdlib-only Python script.

- **Preview locally**: `python -m http.server <port>` from the repo root,
  then open `http://localhost:<port>/index.html`. A plain `file://` open
  won't work — the page `fetch()`s `data/*.json`, which requires HTTP.
- **Run the weekly sync**: `python scripts/sync_dashboards.py`, or
  double-click `scripts/run_sync.bat` (used by the Windows Task Scheduler
  entry that runs it weekly).

## Architecture

- **`index.html`** — the whole page. Links `css/site.css` and a Google Fonts
  stylesheet (JetBrains Mono) in `<head>`; markup is the terminal-window
  chrome plus three `.card` blocks (`#card-weheat`, `#card-battery`,
  `#card-energy`). A single inline `<script>` at the bottom holds a `CARDS`
  config (per-card id, JSON file, accent colour, value formatter), fetches
  each `data/*.json`, and hand-rolls an SVG line chart per card — no
  charting library. Each chart draws its own gradient-filled area, gridlines,
  endpoint dot, and a hover crosshair/tooltip computed from pointer position
  against the SVG viewBox.
- **`css/site.css`** — all styling, token-based (CSS custom properties on
  `:root`: `--bg`, `--surface`, `--ink-1/2/3`, and one accent colour per
  metric — `--weheat`, `--battery`, `--energy`). Deliberately factored out
  of `index.html` so a future second page can link the same stylesheet and
  inherit the look.
- **`data/weheat.json`, `data/battery.json`, `data/energy.json`** — each an
  array of `{"date": "YYYY-MM-DD", "value": number}`, one point per week.
  `scripts/sync_dashboards.py` caps each file at the most recent 52 points.
- **`scripts/sync_dashboards.py`** — the one automation entry point. Three
  `fetch_*` functions (`fetch_weheat_cop`, `fetch_battery_soc`,
  `fetch_grid_import_kwh`) currently `raise NotImplementedError` — the real
  WeHeat/battery/grid data sources haven't been picked yet, so don't invent
  a fake integration for them. **Important behaviour**: the script always
  runs `git add -A` (not just the data files) and, if anything is staged,
  commits and pushes to `origin/gh-pages` — so running it, even manually to
  test, publishes whatever else is sitting uncommitted in the working tree.
- **`scripts/run_sync.bat`** — `cd`s to the repo root and runs the script
  above; this is what's wired into Windows Task Scheduler for the weekly
  run, and ends with `pause` so a manual double-click leaves the window open.

## Conventions

- Page copy is British English (`<html lang="en-GB">`) — match that
  spelling in any visible text added to the page.
