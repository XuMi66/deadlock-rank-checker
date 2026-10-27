Deadlock Rank Checker 1.0.0
================================

A ranked-only viewer for your Deadlock match history:
last 30 ranked games, frequent teammates, frequent opponents,
and the players you have met on both sides.

GETTING STARTED
1. Extract this folder anywhere except Program Files
   (the app writes config.json and cache\ next to the exe).
2. Run DeadlockRankChecker.exe
3. First launch asks for your account. Any of these works:
       76561198208137931                  SteamID64
       247872203                          friend code / SteamID3 (8-10 digits)
       https://steamcommunity.com/id/xxx  profile URL
4. Done. Data loads in a few seconds.

WHAT YOU ARE LOOKING AT
- Header: Steam name, rank badge, W/L in the scanned window, points of the last game
- Recent ranked: 30 games with K/D/A, hero damage, duration, team vs enemy average damage, rank points
- Frequent teammates / opponents: games together, win rate, last meeting
- Teammates & opponents: people met on both sides, with the 3/2 style split
- How to play this one: rule-based notes from the numbers above
- Click any column header to sort; click again to reverse. Tables scroll.

THINGS TO KNOW
- It cannot predict who you will be matched with next. Matchmaking is server-side.
- Ranked only. An account without ranked games shows an empty state.
- Data comes from api.deadlock-api.com (community API, no key). A game that just
  ended needs a few minutes to appear; rate limits are reported as HTTP status.
- Needs internet. No Steam login, no game files touched.
- "Switch account" changes the player; "Steam profile" opens the profile in a browser.
- To reset: delete config.json and the cache folder.

Not affiliated with Valve. Deadlock belongs to Valve Corporation.
Made by 九千须弥

Tip: click any player name to open their Steam profile.
