# -*- coding: utf-8 -*-
"""Deadlock Rank Checker v2 — ranked matches only

Data: api.deadlock-api.com (community REST, no key required)
What it cannot show: who you will be matched with next — that happens on the server.
"""
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

API = "https://api.deadlock-api.com"
UA = "DeadlockCoach/2.0"
STEAM64 = 76561197960265728
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
CONF = os.path.join(HERE, "config.json")

BG = "#0f1115"
CARD = "#161a22"
CARD2 = "#1b2029"
LINE = "#242b37"
FG = "#e6e9f0"
MUTED = "#8b93a3"
GOLD = "#d8b45a"
GREEN = "#6fcf97"
RED = "#e07a7a"
BLUE = "#7fb3e8"

RANK_EN = ["Obscurus", "Initiate", "Seeker", "Alchemist", "Arcanist", "Ritualist",
           "Emissary", "Archon", "Oracle", "Phantom", "Ascendant", "Eternus"]
RANK_CN = ["Obscurus", "Initiate", "Seeker", "Alchemist", "Arcanist", "Ritualist",
           "Emissary", "Archon", "Oracle", "Phantom", "Ascendant", "Eternus"]
ROMAN = ["", "I", "II", "III", "IV", "V", "VI"]

HERO_EN = {
    1: "Infernus", 2: "Seven", 3: "Vindicta", 4: "Lady Geist", 6: "Abrams", 7: "Wraith",
    8: "McGinnis", 9: "Guardian", 10: "Paradox", 11: "Dynamo", 12: "Kelvin", 13: "Haze",
    15: "Bebop", 17: "Pocket", 18: "Talon", 19: "Ivy", 20: "Lash", 25: "Warden", 27: "Yamato",
    31: "Shiv", 35: "Viscous", 50: "Grey Talon", 52: "Mirage", 58: "Vyper", 60: "Sinclair",
    63: "Mina", 64: "Drifter", 65: "Venator", 66: "Golem", 67: "Magician", 69: "Doorman",
    72: "Billy", 76: "Ash", 77: "Apollo", 78: "Deadman Danny", 79: "Rem",
    80: "Werewolf", 81: "Celeste", 86: "Violet", 87: "Nurse Harrow",
}


# ---------------------------------------------------------------- plumbing
def load_conf():
    if os.path.exists(CONF):
        try:
            with open(CONF, "r", encoding="utf-8") as f:
                c = json.load(f)
            if c.get("account_id"):
                return c
        except Exception:
            pass
    return {"account_id": None, "recent": 30, "mates": 6, "enemies": 6, "cache_s": 180}


def save_conf(cfg):
    try:
        with open(CONF, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def http(path, ttl=0, timeout=30):
    os.makedirs(CACHE, exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9_.-]", "_", path)[:150]
    fp = os.path.join(CACHE, key + ".json")
    if ttl > 0 and os.path.exists(fp) and time.time() - os.path.getmtime(fp) < ttl:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    req = urllib.request.Request(API + path, headers={"User-Agent": UA})
    last = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError:
            raise                       # 4xx/5xx: no retry, let the caller classify
        except Exception as e:          # timeout / connection reset
            last = e
            if attempt == 0:
                time.sleep(1.5)
                continue
            raise last
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
    return data


def ts(sec):
    return time.strftime("%m-%d %H:%M", time.localtime(sec))


def dur(sec):
    sec = int(sec or 0)
    return "%d:%02d" % (sec // 60, sec % 60)


def kfmt(v):
    v = float(v or 0)
    return "%.1fk" % (v / 1000.0) if v >= 1000 else ("%.0f" % v)


def team_num(v):
    """'Team0' / 0 / '0' -> 0"""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    t = str(v if v is not None else "").strip()
    if t.lower().startswith("team"):
        t = t[4:]
    try:
        return int(t)
    except Exception:
        return -1


def parse_account(text):
    """Accept friend code / SteamID64 / profile URL; return (account_id, how)"""
    t = (text or "").strip()
    if not t:
        raise ValueError("empty input")
    m = re.search(r"steamcommunity\.com/profiles/(\d{17})", t)
    if m:
        return int(m.group(1)) - STEAM64, "SteamID64 link"
    m = re.search(r"steamcommunity\.com/id/([A-Za-z0-9_-]+)", t)
    if m:
        res = http("/v1/players/steam-search?search_query=%s&limit=5" % urllib.parse.quote(m.group(1)), 0)
        if isinstance(res, list) and res:
            for row in res:
                if str(row.get("profileurl", "")).rstrip("/").lower().endswith("/id/" + m.group(1).lower()):
                    return int(row["account_id"]), "custom URL"
            return int(res[0]["account_id"]), "custom URL (first search hit)"
        raise ValueError("no account found for that custom URL")
    digits = re.sub(r"\D", "", t)
    if not digits:
        raise ValueError("no number found in that input")
    n = int(digits)
    if n > STEAM64:
        return n - STEAM64, "SteamID64"
    if n > 2 ** 32 - 1:
        raise ValueError("that number is neither a friend code nor a SteamID64 — check the digits")
    if n >= 1000:                     # a friend code is the 32-bit account id (8-10 digits)
        return n, "friend code / SteamID3"
    raise ValueError("that number is too small to be an account ID")


def mdate(sec):
    """epoch -> Oct 26 (year added when it differs)"""
    try:
        t = time.localtime(int(sec))
    except Exception:
        return "—"
    now = time.localtime()
    if t.tm_year != now.tm_year:
        return "%s %d, %d" % (MON[t.tm_mon - 1], t.tm_mday, t.tm_year)
    return "%s %d" % (MON[t.tm_mon - 1], t.tm_mday)


# ---------------------------------------------------------------- data
class Data:
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        self.acc = int(cfg["account_id"])
        self.err = None
        self.me = {}
        self.names = {}
        self.rank = None
        self.rows = []
        self.mates = []
        self.enemies = []
        self.both = []
        self.scan = 0
        self.wins = 0
        self.empty = False
        self.heroes = {}

    def hero(self, hid):
        try:
            hid = int(hid)
        except Exception:
            return "Hero"
        return self.heroes.get(hid) or HERO_EN.get(hid) or ("Hero %d" % hid)

    def rank_text(self):
        if not self.rank:
            return "Unranked"
        r = int(self.rank.get("rank", 0) or 0)
        s = int(self.rank.get("subrank", 0) or 0)
        if r <= 0:
            return "Unranked"
        name = RANK_EN[r] if r < 12 else "?"
        cn = RANK_CN[r] if r < 12 else "?"
        tag = "%s %s" % (name, ROMAN[max(0, min(6, s))])
        if cn and cn.lower() != name.lower():
            tag += " · " + cn
        return tag

    def last_delta(self):
        lm = (self.rank or {}).get("last_match") or {}
        try:
            return int(lm.get("player_rank_desired_progress_change"))
        except Exception:
            return None

    # -------- fetch --------
    def fetch(self):
        self.err = None
        try:
            ttl = int(self.cfg.get("cache_s", 180))
            self.heroes = self._hero_table()
            self.me = self._steam_names([self.acc]).get(self.acc, {})
            try:
                self.rank = http("/v1/players/%d/rank" % self.acc, 60)
            except Exception:
                self.rank = None
            try:
                hist = http("/v1/players/%d/match-history?limit=200" % self.acc, ttl) or []
            except Exception as e:
                hist = []
                self.err = "match history API did not respond (%s), retrying once" % type(e).__name__
            ranked = [r for r in hist if int(r.get("match_mode") or 0) == 4]
            show = ranked[: int(self.cfg.get("recent", 30))]
            scan = ranked[:90]

            meta = {}
            ids = [r["match_id"] for r in scan]
            for i in range(0, len(ids), 20):
                chunk = ids[i:i + 20]
                q = ("/v1/matches/metadata?match_ids=" + ",".join(str(x) for x in chunk)
                     + "&include_player_final_stats=true&include_player_stats=false"
                     + "&extra_player_columns=mvp_rank&limit=%d" % len(chunk))
                try:
                    got = http(q, ttl)
                except Exception:
                    continue
                if isinstance(got, list):
                    for md in got:
                        meta[int(md.get("match_id"))] = md

            self.scan = len([1 for r in scan if r["match_id"] in meta])

            rows = []
            for r in show:
                md = meta.get(r["match_id"]) or {}
                players = md.get("players") or []
                my_team = team_num(r.get("player_team"))
                mine = [(p.get("final_stats") or {}).get("player_damage", 0) for p in players
                        if team_num(p.get("team")) == my_team]
                theirs = [(p.get("final_stats") or {}).get("player_damage", 0) for p in players
                          if team_num(p.get("team")) != my_team]
                me = next((p for p in players if p.get("account_id") == self.acc), None)
                fs = (me or {}).get("final_stats") or {}
                rows.append({
                    "match_id": r["match_id"],
                    "hero": self.hero(r.get("hero_id")),
                    "win": int(r.get("player_match_outcome") or 0) == 1,
                    "k": r.get("player_kills", 0), "d": r.get("player_deaths", 0),
                    "a": r.get("player_assists", 0),
                    "dmg": fs.get("player_damage", 0),
                    "dur": r.get("match_duration_s", 0),
                    "start": r.get("start_time", 0),
                    "delta": r.get("ranked_delta"),
                    "mine": (sum(mine) / len(mine)) if mine else 0,
                    "theirs": (sum(theirs) / len(theirs)) if theirs else 0,
                })
            self.rows = rows

            mates, enemies = {}, {}
            for r in scan:
                md = meta.get(r["match_id"])
                if not md:
                    continue
                my_team = team_num(r.get("player_team"))
                win = 1 if int(r.get("player_match_outcome") or 0) == 1 else 0
                for p in (md.get("players") or []):
                    aid = p.get("account_id")
                    if not aid or aid == self.acc:
                        continue
                    bucket = mates if team_num(p.get("team")) == my_team else enemies
                    e = bucket.setdefault(aid, {"n": 0, "w": 0, "last": 0})
                    e["n"] += 1
                    e["w"] += win
                    st_t = int(r.get("start_time") or 0)
                    if st_t > e["last"]:
                        e["last"] = st_t

            self.wins = sum(1 for r in rows if r["win"])
            if not rows and not self.err:
                self.err = None
                self.empty = True

            def top(d, key):
                return sorted(d.items(), key=lambda kv: (-kv[1]["n"], -kv[1]["w"]))[: int(self.cfg.get(key, 6))]

            self.mates = top(mates, "mates")
            self.enemies = top(enemies, "enemies")

            both = []
            for aid, m in mates.items():
                e = enemies.get(aid)
                if not e:
                    continue
                both.append((aid, {
                    "n": m["n"] + e["n"], "w": m["w"] + e["w"],
                    "mate_n": m["n"], "mate_w": m["w"],
                    "enemy_n": e["n"], "enemy_w": e["w"],
                    "last": max(m["last"], e["last"]),
                }))
            both.sort(key=lambda kv: (-kv[1]["n"], -kv[1]["last"]))
            self.both = both[: int(self.cfg.get("both", 8))]

            want = ([a for a, _ in self.mates] + [a for a, _ in self.enemies]
                    + [a for a, _ in self.both])
            self.names = self._steam_names(want)
        except urllib.error.HTTPError as e:
            self.err = "API %s %s" % (e.code, e.reason)
        except Exception as e:
            self.err = "%s: %s" % (type(e).__name__, e)

    def _hero_table(self):
        try:
            hs = http("/v1/assets/heroes?language=english", 86400)
            return {int(h["id"]): (h.get("name") or "") for h in hs if h.get("id")}
        except Exception:
            return {}

    def _steam_names(self, ids):
        ids = sorted({int(i) for i in ids if i})
        if not ids:
            return {}
        out = {}
        for ttl in (3600, 0):          # second pass bypasses cache to fill in missing accounts
            miss = [i for i in ids if i not in out]
            if not miss:
                break
            for k in range(0, len(miss), 100):
                chunk = miss[k:k + 100]
                q = ("/v1/players/steam?account_ids="
                     + urllib.parse.quote(",".join(str(i) for i in chunk)))
                try:
                    for p in http(q, ttl):
                        out[int(p["account_id"])] = p
                except Exception:
                    continue
        return out

    # -------- advice --------
    def advice(self):
        out = []
        n = len(self.rows)
        if n == 0:
            out.append("No ranked games for this account recently (normal games do not show up here).")
            out.append("Play one ranked game, or switch to an account with ranked history.")
            return out
        if n >= 5:
            wr = self.wins / n
            if wr >= 0.6:
                out.append("Won %d of your last %d ranked games — you are in form, good time to climb." % (self.wins, n))
            elif wr <= 0.3:
                out.append("Only %d wins in your last %d ranked games — take a break; decisions get rushed on a losing run." % (self.wins, n))
            else:
                out.append("%d W / %d L over your last %d ranked games — even stretch, farm safely and stop dying." % (self.wins, n - self.wins, n))

        streak = 0
        for r in self.rows:
            if r["win"]:
                break
            streak += 1
        if streak >= 3:
            out.append("You are on a %d game losing streak — do not queue on tilt." % streak)

        d = self.last_delta()
        if d is not None and d < 0:
            out.append("Last game: %+d pts. After a loss, take your most comfortable hero — do not practise here." % d)
        elif d is not None and d > 0:
            out.append("Last game: %+d pts. Keep the same plan that worked." % d)

        if self.mates:
            aid, st = self.mates[0]
            nm = (self.names.get(aid) or {}).get("personaname") or str(aid)
            if st["n"] >= 3:
                out.append("Most frequent teammate: %s (%d games, %.0f%% win rate)." % (nm, st["n"], 100.0 * st["w"] / st["n"]))

        if self.enemies:
            aid, st = self.enemies[0]
            nm = (self.names.get(aid) or {}).get("personaname") or str(aid)
            if st["n"] >= 3:
                out.append("Frequent opponent %s faced you %d times; you won %d." % (nm, st["n"], st["w"]))

        if self.rows:
            r = self.rows[0]
            if r["mine"] and r["theirs"]:
                ratio = r["mine"] / max(1.0, r["theirs"])
                if ratio < 0.85:
                    out.append("Last game your team dealt %.0f%% less damage — do not wait for teammates to start fights." % ((1 - ratio) * 100))
                elif ratio > 1.15:
                    out.append("Last game your team out-damaged theirs — keep the same opening tempo.")

        if not out:
            out.append("Not enough ranked games yet — play a few more and check again.")
        return out


# ---------------------------------------------------------------- ui
class App:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.data = Data(cfg)
        self.busy = False
        # per-table sort state: which -> (column, descending). default: most meetings first
        self.sort_state = {"mate": ("n", True), "enemy": ("n", True), "both": ("n", True)}

        root.title("Deadlock Rank Checker")
        root.geometry("1240x980")
        root.minsize(1120, 900)
        root.configure(bg=BG)
        self._style()

        head = tk.Frame(root, bg=BG)
        head.pack(fill="x", padx=22, pady=(18, 10))

        left = tk.Frame(head, bg=BG)
        left.pack(side="left")
        self.l_name = tk.Label(left, text="Loading…", font=("Segoe UI", 18, "bold"),
                               fg=FG, bg=BG)
        self.l_name.pack(anchor="w")
        sub = tk.Frame(left, bg=BG)
        sub.pack(anchor="w", pady=(4, 0))
        self.l_rank = tk.Label(sub, text="", font=("Segoe UI", 11), fg=GOLD, bg=BG)
        self.l_rank.pack(side="left")
        tk.Label(sub, text="  ranked only", font=("Segoe UI", 9), fg=MUTED, bg=BG).pack(side="left")

        right = tk.Frame(head, bg=BG)
        right.pack(side="right")
        self.l_wl = tk.Label(right, text="", font=("Segoe UI", 13, "bold"), fg=FG, bg=BG)
        self.l_wl.pack(anchor="e")
        self.l_sub = tk.Label(right, text="", font=("Segoe UI", 9), fg=MUTED, bg=BG)
        self.l_sub.pack(anchor="e", pady=(3, 0))

        tk.Frame(root, bg=LINE, height=1).pack(fill="x", padx=22)

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=14)

        left_card = tk.Frame(body, bg=CARD)
        left_card.pack(side="left", fill="both", expand=True)
        tk.Label(left_card, text="Recent ranked", font=("Segoe UI", 11, "bold"),
                 fg=BLUE, bg=CARD).pack(anchor="w", padx=16, pady=(14, 8))
        cols = ("time", "hero", "res", "kda", "dmg", "dur", "team", "delta")
        tv_wrap = tk.Frame(left_card, bg=CARD)
        tv_wrap.pack(fill="both", expand=True, padx=(10, 6), pady=(0, 14))
        self.tv = ttk.Treeview(tv_wrap, columns=cols, show="headings", style="Clean.Treeview")
        head_txt = {"time": "Date", "hero": "Hero", "res": "Result", "kda": "K/D/A",
                    "dmg": "Damage", "dur": "Length", "team": "Team / enemy avg dmg", "delta": "Rank pts"}
        widths = {"time": 96, "hero": 116, "res": 50, "kda": 72, "dmg": 64, "dur": 54,
                  "team": 160, "delta": 72}
        for c in cols:
            self.tv.heading(c, text=head_txt[c])
            self.tv.column(c, width=widths[c], anchor="center")
        self.tv.tag_configure("win", foreground=GREEN)
        self.tv.tag_configure("lose", foreground=RED)
        self.tv.bind("<MouseWheel>", lambda e: (self.tv.yview_scroll(int(-e.delta / 120), "units"), "break")[1])
        self.tv.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tv_wrap, orient="vertical", command=self.tv.yview)
        sb.pack(side="right", fill="y", padx=(4, 0))
        self.tv.configure(yscrollcommand=sb.set)

        right_wrap = tk.Frame(body, bg=BG, width=372)
        right_wrap.pack(side="right", fill="y", padx=(14, 0))
        right_wrap.pack_propagate(False)

        for title, color, attr_name, which in (
                ("Frequent teammates · ranked", BLUE, "tv_mate", "mate"),
                ("Frequent opponents · ranked", RED, "tv_enemy", "enemy")):
            card = tk.Frame(right_wrap, bg=CARD)
            card.pack(fill="x", pady=(0, 12))
            tk.Label(card, text=title, font=("Segoe UI", 11, "bold"),
                     fg=color, bg=CARD).pack(anchor="w", padx=16, pady=(14, 6))
            wrap = tk.Frame(card, bg=CARD)
            wrap.pack(fill="x", padx=(10, 6), pady=(0, 10))
            tv = ttk.Treeview(wrap, columns=("nm", "n", "wr", "last"), show="headings",
                              height=4, style="Clean.Treeview")
            for c, t, w in (("nm", "Player", 150), ("n", "Games", 46), ("wr", "Win %", 58),
                            ("last", "Last", 82)):
                tv.heading(c, text=t, command=lambda cc=c, wh=which: self._toggle_sort(wh, cc))
                tv.column(c, width=w, anchor="w" if c == "nm" else "center")
            tv.pack(side="left", fill="x", expand=True)
            sb = ttk.Scrollbar(wrap, orient="vertical", command=tv.yview)
            sb.pack(side="right", fill="y", padx=(4, 0))
            tv.configure(yscrollcommand=sb.set)
            setattr(self, attr_name, tv)
            setattr(self, attr_name + "_sb", sb)

        both_card = tk.Frame(root, bg=CARD)
        both_card.pack(fill="x", padx=22, pady=(0, 12))
        tk.Label(both_card, text="Teammates & opponents", font=("Segoe UI", 11, "bold"),
                 fg="#d9a441", bg=CARD).pack(anchor="w", padx=16, pady=(12, 6))
        bcols = ("nm", "n", "wl", "mate", "enemy", "last")
        bwrap = tk.Frame(both_card, bg=CARD)
        bwrap.pack(fill="x", padx=(10, 6), pady=(0, 10))
        self.tv_both = ttk.Treeview(bwrap, columns=bcols, show="headings", height=5,
                                    style="Clean.Treeview")
        bhead = {"nm": "Player", "n": "Total", "wl": "W / L", "mate": "As teammate",
                 "enemy": "As opponent", "last": "Last seen"}
        bwid = {"nm": 220, "n": 70, "wl": 80, "mate": 80, "enemy": 80, "last": 100}
        for c in bcols:
            if c in ("n", "last"):
                self.tv_both.heading(c, text=bhead[c],
                                     command=lambda cc=c: self._toggle_sort("both", cc))
            else:
                self.tv_both.heading(c, text=bhead[c])
            self.tv_both.column(c, width=bwid[c], anchor="w" if c == "nm" else "center")
        self.tv_both.pack(side="left", fill="x", expand=True)
        self.tv_both_sb = ttk.Scrollbar(bwrap, orient="vertical", command=self.tv_both.yview)
        self.tv_both_sb.pack(side="right", fill="y", padx=(4, 0))
        self.tv_both.configure(yscrollcommand=self.tv_both_sb.set)

        foot = tk.Frame(root, bg=BG)
        foot.pack(fill="x", padx=22, pady=(0, 16))

        adv = tk.Frame(foot, bg=CARD)
        adv.pack(fill="x")
        tk.Label(adv, text="How to play this one", font=("Segoe UI", 11, "bold"),
                 fg=GOLD, bg=CARD).pack(anchor="w", padx=16, pady=(12, 4))
        self.txt = tk.Text(adv, height=6, bg=CARD, fg="#dfe3ea", bd=0, highlightthickness=0,
                           font=("Segoe UI", 10), wrap="word", cursor="arrow")
        self.txt.pack(fill="x", padx=16, pady=(0, 12))

        bar = tk.Frame(foot, bg=BG)
        bar.pack(fill="x", pady=(12, 0))
        self._btn(bar, "Refresh", self.refresh, "#233044", "#2e3f5c").pack(side="left")
        self._btn(bar, "Launch Deadlock", self.launch, "#4a2530", "#64313f").pack(side="left", padx=8)
        self._btn(bar, "Switch account", self.change_account, "#222a24", "#2f3a31").pack(side="left")
        self._btn(bar, "Steam profile", self.profile, "#222a24", "#2f3a31").pack(side="left", padx=8)
        right_box = tk.Frame(bar, bg=BG)
        right_box.pack(side="right")
        self.status = tk.Label(right_box, text="", fg=MUTED, bg=BG,
                               font=("Segoe UI", 9))
        self.status.pack(anchor="e")
        self.credit = tk.Label(right_box, text="Made by 九千须弥", fg="#8b96a8", bg=BG,
                               font=("Segoe UI", 8))
        self.credit.pack(anchor="e", pady=(2, 0))

        self.refresh()

    def _style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Clean.Treeview", background=CARD, fieldbackground=CARD, foreground=FG,
                     rowheight=26, borderwidth=0, font=("Segoe UI", 10))
        st.configure("Clean.Treeview.Heading", background=CARD2, foreground=MUTED,
                     borderwidth=0, relief="flat", font=("Segoe UI", 9))
        st.map("Clean.Treeview", background=[("selected", "#2b3a55")])
        st.layout("Clean.Treeview", [("Clean.Treeview.treearea", {"sticky": "nswe"})])
        try:
            st.configure("Vertical.TScrollbar", background=CARD2, troughcolor="#0e141d",
                         bordercolor="#0e141d", arrowcolor=MUTED, relief="flat")
            st.map("Vertical.TScrollbar", background=[("active", "#3a4a63")])
        except Exception:
            pass

    def _btn(self, parent, text, cmd, bg, hover):
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg="#e9eef7", bd=0,
                         activebackground=hover, activeforeground="#ffffff", relief="flat",
                         padx=16, pady=7, cursor="hand2", font=("Segoe UI", 10))

    def launch(self):
        try:
            os.startfile("steam://rungameid/1422450")
        except Exception as e:
            messagebox.showerror("Launch failed", str(e))

    def profile(self):
        d = self.data
        url = ((d.me or {}).get("profileurl") or "").strip()
        if not url:
            url = "https://steamcommunity.com/profiles/%d" % (int(d.acc) + STEAM64)
        os.startfile(url)

    def change_account(self):
        tip = "Enter a friend code / account ID, a SteamID64, or a steamcommunity profile URL"
        val = simpledialog.askstring("Switch account", tip, parent=self.root)
        if not val:
            return
        try:
            acc, how = parse_account(val)
        except Exception as e:
            messagebox.showerror("Could not parse", str(e))
            return
        self.cfg["account_id"] = acc
        save_conf(self.cfg)
        self.data = Data(self.cfg)
        self.status.config(text="Switched to %s (%s)" % (acc, how))
        self.refresh()

    def refresh(self):
        if self.busy:
            return
        self.busy = True
        self.status.config(text="Fetching…")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        self.data.cfg = dict(self.cfg)
        self.data.acc = int(self.cfg["account_id"])
        self.data.fetch()
        self.root.after(0, self._render)

    # ---- sorting and filling ----
    HEADS = {"mate": {"nm": "Player", "n": "Games", "wr": "Win %", "last": "Last"},
             "enemy": {"nm": "Player", "n": "Games", "wr": "Win %", "last": "Last"},
             "both": {"nm": "Player", "n": "Total", "wl": "W / L", "mate": "As teammate",
                      "enemy": "As opponent", "last": "Last seen"}}

    def _toggle_sort(self, which, col):
        if col in ("nm", "wl", "mate", "enemy"):
            return
        cur, desc = self.sort_state.get(which, ("n", True))
        if cur == col:
            desc = not desc
        else:
            desc = True
        self.sort_state[which] = (col, desc)
        d = self.data
        if which == "mate":
            self._fill_people("mate", d.mates)
        elif which == "enemy":
            self._fill_people("enemy", d.enemies)
        else:
            self._fill_both()

    @staticmethod
    def _key(which, key):
        if key == "last":
            return lambda kv: kv[1].get("last", 0) or 0
        if key == "wr":
            return lambda kv: (kv[1].get("w", 0) / max(1, kv[1].get("n", 1)))
        return lambda kv: kv[1].get("n", 0)

    def _head_text(self, which, col):
        base = self.HEADS[which].get(col, col)
        cur, desc = self.sort_state.get(which, ("n", True))
        if cur == col:
            return base + (" ▼" if desc else " ▲")
        return base

    def _refresh_heads(self, which, tv):
        for c, _ in self.HEADS[which].items():
            try:
                tv.heading(c, text=self._head_text(which, c))
            except Exception:
                pass

    def _fill_people(self, which, rows):
        tv = self.tv_mate if which == "mate" else self.tv_enemy
        d = self.data
        key, desc = self.sort_state.get(which, ("n", True))
        rows = sorted(list(rows or []), key=self._key(which, key), reverse=desc)
        for i in tv.get_children():
            tv.delete(i)
        for aid, st in rows:
            nm = (d.names.get(aid) or {}).get("personaname") or ("Player %d" % aid)
            n2 = st.get("n") or 1
            tv.insert("", "end", values=(nm[:20], st.get("n", 0),
                                         "%.0f%%" % (100.0 * st.get("w", 0) / n2),
                                         mdate(st.get("last", 0))))
        self._refresh_heads(which, tv)
        try:
            tv.yview_moveto(0)
        except Exception:
            pass

    def _fill_both(self):
        d = self.data
        rows = list(getattr(d, "both", []) or [])
        key, desc = self.sort_state.get("both", ("n", True))
        if key == "wr":
            rows = sorted(rows, key=lambda kv: kv[1].get("w", 0) / max(1, kv[1].get("n", 1)),
                          reverse=desc)
        else:
            rows = sorted(rows, key=self._key("both", key), reverse=desc)
        tv = self.tv_both
        for i in tv.get_children():
            tv.delete(i)
        for aid, st in rows:
            nm = (d.names.get(aid) or {}).get("personaname") or ("Player %d" % aid)
            tv.insert("", "end", values=(
                nm[:24], st.get("n", 0),
                "%d / %d" % (st.get("w", 0), st.get("n", 0) - st.get("w", 0)),
                "%d game%s, %d W" % (st.get("mate_n", 0), "" if st.get("mate_n", 0) == 1 else "s", st.get("mate_w", 0)),
                "%d game%s, %d W" % (st.get("enemy_n", 0), "" if st.get("enemy_n", 0) == 1 else "s", st.get("enemy_w", 0)),
                mdate(st.get("last", 0)),
            ))
        self._refresh_heads("both", tv)
        try:
            tv.yview_moveto(0)
        except Exception:
            pass

    def _render(self):
        self.busy = False
        d = self.data
        if d.err:
            self.status.config(text="Failed: " + d.err)
        elif not d.rows:
            self.status.config(text="No recent ranked games · scanned %d" % d.scan)
        else:
            self.status.config(text="Updated %s · %d ranked scanned" % (time.strftime("%H:%M:%S"), d.scan))

        self.l_name.config(text=(d.me or {}).get("personaname") or ("Account %d" % d.acc))
        self.l_rank.config(text=d.rank_text())
        n = len(d.rows)
        self.l_wl.config(text=("%d W %d L" % (d.wins, n - d.wins)) if n else "—")
        dd = d.last_delta()
        self.l_sub.config(text=("Last game %+d pts" % dd) if isinstance(dd, int) else ("last %d ranked" % n))

        for i in self.tv.get_children():
            self.tv.delete(i)
        if not d.rows:
            self.tv.insert("", "end", values=("—", "No ranked games recently", "—", "—", "—", "—", "—", "—"))
        for r in d.rows:
            dl = r["delta"]
            delta = ("%+d" % int(dl)) if isinstance(dl, (int, float)) else "—"
            self.tv.insert("", "end", values=(
                ts(r["start"]), r["hero"], "W" if r["win"] else "L",
                "%d/%d/%d" % (r["k"], r["d"], r["a"]), kfmt(r["dmg"]), dur(r["dur"]),
                "%s / %s" % (kfmt(r["mine"]), kfmt(r["theirs"])), delta,
            ), tags=("win" if r["win"] else "lose",))

        self._fill_people("mate", d.mates)
        self._fill_people("enemy", d.enemies)

        self._fill_both()

        try:
            self.tv.yview_moveto(0)
        except Exception:
            pass

        self.txt.delete("1.0", "end")
        for line in d.advice():
            self.txt.insert("end", "· " + line + "\n")


def first_run(root, cfg):
    """First run: ask for the account and only continue once it parses."""
    while True:
        tip = ("Enter your friend code / account ID, SteamID64,\n"
               "or Steam profile URL:")
        val = simpledialog.askstring("Deadlock Rank Checker · first run", tip, parent=root)
        if val is None or not val.strip():
            return False
        try:
            acc, note = parse_account(val.strip())
        except Exception as e:
            msg = ("Could not read that account:\n%s\n\n"
                   "Use a SteamID64 or a Steam profile URL." % e)
            messagebox.showerror("Could not parse", msg, parent=root)
            continue
        cfg["account_id"] = acc
        messagebox.showinfo("Account set", "Using account %d (%s)" % (acc, note), parent=root)
        return True


def main():
    cfg = load_conf()
    root = tk.Tk()
    root.withdraw()
    if not cfg.get("account_id"):
        if not first_run(root, cfg):
            root.destroy()
            return
    save_conf(cfg)
    root.deiconify()
    App(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()
