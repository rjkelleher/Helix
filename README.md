# HELIX — Biotech & Pharma Terminal

A self-contained, installable web dashboard for the biotech/pharma universe we built.
Sortable + filterable table, and a Yahoo-style detail view per stock with price chart,
key data, fundamentals, and news.

## Add it to your iPhone home screen
1. Put these files on any static host (GitHub Pages, Netlify, Cloudflare Pages, or your own server).
   They must be served together from the same folder.
2. Open the page in **Safari** on iPhone.
3. Tap **Share → Add to Home Screen**. It launches full-screen with its own icon — like an app.

> Opening `index.html` directly from Files (file://) works for a quick look, but the
> service worker (offline) and `data.json` auto-loading need it served over http(s).

## Two data modes
- **DEMO (default):** real tickers, names, regions, and market-cap tiers from our universe;
  prices/returns/volumes/fundamentals are deterministically simulated and badged **DEMO DATA**.
  Nothing fabricated is presented as a real quote.
- **LIVE snapshot:** run the included script to generate real numbers:
  ```
  pip install yfinance pandas
  python build_dashboard_data.py        # reads tickers.csv -> writes data.json
  ```
  Reload the page: the badge turns green ("LIVE · <timestamp>") and every figure,
  chart, and news item is real. Re-run (or schedule) to refresh.

## Optional live quotes/news in the detail view
Tap the gear → paste a free [Finnhub](https://finnhub.io) API key. The open stock's
current price and (where available) news refresh live client-side. US names are most reliable.

## Expand the universe
`tickers.csv` (symbol, company, region) is the universe. Add rows — US bare (e.g. `PFE`),
ex-US with a Yahoo suffix (e.g. `AZN.L`, `4519.T`, `1801.HK`) — and re-run the script.

## Files
- `index.html` — the app (open this)
- `build_dashboard_data.py` — yfinance → `data.json` (history, fundamentals, news)
- `tickers.csv` — the universe (edit to add names)
- `manifest.json`, `sw.js`, `icon-180.png`, `icon-512.png` — PWA install + offline

## Notes
- History closes and market-cap fields are normalized to USD so a global list is comparable.
- Returns: Day / 1W / 1M / YTD / 1Y in the grid; 1W–MAX in the detail view.
- Volume: latest-session in the grid's "Vol D"; the rest are **average daily volume** per window.
