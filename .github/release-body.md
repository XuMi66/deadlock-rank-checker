## Downloads

| File | Language | Contents |
|---|---|---|
| `DeadlockRankChecker-win64.zip` | English | `DeadlockRankChecker.exe`, `README.txt`, `screenshot.png` |
| `DeadlockRankChecker-win64-zh.zip` | 中文 | `死锁排位查询.exe`, `使用说明.txt`, `界面预览.png` |

Single-file executables, no installer. Extract to any normal folder (not `Program Files` — the app writes `config.json` and `cache\` next to the exe) and run.

## What it does

- Last **30 ranked games**: date, hero, W/L, K/D/A, hero damage, length, team vs enemy average damage, rank points
- **Frequent teammates / opponents**: how many games together, win rate, last meeting date
- **Teammates & opponents**: people you met on both sides, with the split
- Rule-based notes on the current run (streak, last points swing, most frequent teammate, damage gap)
- Sortable and scrollable tables; first-run account setup via SteamID64, friend code or profile URL

## Not included

It **cannot** predict your next teammates — matchmaking is server-side and not exposed by any public API. Ranked matches only. Data from [api.deadlock-api.com](https://api.deadlock-api.com).

Windows 10/11 x64, internet required, no Steam login.
