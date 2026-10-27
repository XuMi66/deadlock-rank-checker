# Changelog

## 1.0.1 — 2026-10-27

- Player names in the three player tables are now clickable: one click opens that player's Steam profile
- Uses the profile URL returned by the API when available, otherwise falls back to `steamcommunity.com/profiles/<steamid64>`
- Status bar confirms which profile was opened

## 1.0.0 — 2026-10-27

First public release.

- Ranked-only history (last 30 games) with damage, duration and rank points
- Frequent teammates / opponents, and players met on both sides
- Sortable, scrollable tables (games / win rate / last seen)
- Rule-based "how to play this one" notes
- First-run account setup (SteamID64, friend code or profile URL)
- English and Chinese builds, single-file executable, no install
