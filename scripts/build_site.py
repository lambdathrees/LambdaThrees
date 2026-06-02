"""
Lambda 3s League - Static Site Builder
Reads processed CSV data and generates HTML pages into docs/

Usage:
    python scripts/build_site.py
"""

import csv, json, os, re
from html import escape as h
from itertools import groupby

BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT         = os.path.join(BASE, "docs")
LEAGUE_NAME = "Lambda 3s"

# ── Team name normalisation ──────────────────────────────────────────────────

_ALIASES = {
    "hall": "Team Grit", "team hall": "Team Grit", "team grit": "Team Grit",
    "grit": "Team Grit",
    "team flannel bong": "Team Flannel Bong", "team flannel": "Team Flannel Bong",
    "flannel bong": "Team Flannel Bong", "flannel": "Team Flannel Bong",
    "team young": "Team Young", "young": "Team Young",
    "goybeam": "Team Young", "team goybeam": "Team Young",
    "team dirty": "Team Dirty", "dirty": "Team Dirty",
    "team new o": "Team New O", "new o": "Team New O",
    "team tinkler": "Team Tinkler", "team tink": "Team Tinkler",
    "tink": "Team Tinkler", "tinkler": "Team Tinkler",
    "team laub": "Team Laub", "laub": "Team Laub",
    "team dom": "Team Dom", "dom": "Team Dom",
    "team nasty": "Team Nasty", "nasty": "Team Nasty",
    "team big o": "Team Big O", "big o": "Team Big O",
}
_KNOWN_TEAMS = set(_ALIASES.values())

def normalize_team(raw: str) -> str:
    if not raw:
        return raw
    # strip trailing score like "Team Laub 16" or "Team Dirty 4"
    cleaned = re.sub(r'\s+\d+$', '', raw.strip())
    return _ALIASES.get(cleaned.lower(), cleaned.title())


# ── CSV loading ──────────────────────────────────────────────────────────────

def load_csv(rel_path: str) -> list:
    path = os.path.join(BASE, rel_path)
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


# ── Parser: team code → name ─────────────────────────────────────────────────

def parse_team_key(rows: list) -> dict:
    """
    The averages section has a Team Key lookup: col[18]=team_name, col[19]=code.
    Build code→name mapping from those rows.
    """
    key = {}
    for row in rows:
        name = row[18].strip() if len(row) > 18 else ""
        code = row[19].strip() if len(row) > 19 else ""
        if name.startswith("Team ") and len(code) == 1 and code.isalpha():
            key[code] = name
    return key


# ── Parser: standings ────────────────────────────────────────────────────────

def parse_standings(rows: list) -> list:
    """
    Standings are in cols 14-17 of Spring_26-style CSVs.
    Row with 'Actual Standings' in col[14] is the section header.
    Data rows follow: col[14]=team, col[15]=wins, col[16]=losses, col[17]=point_margin.
    Only collects rows whose col[14] normalises to a known team name.
    """
    results = []
    for row in rows:
        if len(row) < 18:
            continue
        raw = row[14].strip()
        if not raw:
            continue
        try:
            w  = float(row[15])
            l  = float(row[16])
            pm = float(row[17])
        except ValueError:
            continue
        team = normalize_team(raw)
        if team not in _KNOWN_TEAMS:
            continue
        results.append({"team": team, "w": int(w), "l": int(l), "pm": pm})
    results.sort(key=lambda x: (-x["w"], -x["pm"]))
    return results


# ── Parser: awards ───────────────────────────────────────────────────────────

_AWARD_KW = ["mvp", "roty", "first team", "award", "fourth man"]

def parse_awards(rows: list) -> list:
    """
    Scan every cell for award keywords; collect winners from cells to the right.
    Returns list of (award_name, winner_string) pairs, deduped.
    """
    awards, seen = [], set()
    for row in rows:
        for i, cell in enumerate(row):
            text = cell.strip()
            if not text or text.lower() in seen:
                continue
            if any(kw in text.lower() for kw in _AWARD_KW):
                rest = [c.strip() for c in row[i + 1:] if c.strip()]
                winners = [v for v in rest if v != "N/A"]
                if winners:
                    entry = (text, " / ".join(winners[:3]))
                elif any(v == "N/A" for v in rest[:4]):
                    entry = (text, "—")   # em dash
                else:
                    continue
                if text not in seen:
                    seen.add(text)
                    awards.append(entry)

    # Remove any award whose name is a plain substring of a longer award already
    # collected (e.g. bare "MVP" is redundant once "MVP(reg season)" exists).
    all_names = [a[0].lower() for a in awards]
    return [
        a for a in awards
        if not any(
            a[0].lower() != other and a[0].lower() in other
            for other in all_names
        )
    ]


# ── Parser: player stats ─────────────────────────────────────────────────────

def parse_player_stats(rows: list, team_key: dict) -> list:
    """
    Read from the pre-computed per-player averages table.
    Header row: col[1]='Player', col[7]='Games Played'  (distinguishes it from
    the per-game box-score headers which have col[7]='Showed up').
    Data rows are offset +1: col[2]=name, col[3]=pts … col[8]=gp, col[9]=team_code.

    Note: Team Dom and Team Laub's Week-1 game only recorded points (reb/ast/stl/blk
    were not tracked). The spreadsheet averages already reflect this — their non-scoring
    stats use the number of games where those stats were actually recorded.
    """
    # Averages table header: col[9]="Player", col[15]="Games Played"
    # (data rows: col[9]=name, col[10]=pts, col[11]=reb, col[12]=ast,
    #  col[13]=stl, col[14]=blk, col[15]=gp, col[16]=team_code)
    header = None
    for i, row in enumerate(rows):
        if (len(row) > 15
                and row[9].strip() == "Player"
                and row[15].strip() == "Games Played"):
            header = i
            break
    if header is None:
        return []

    players = []
    for row in rows[header + 1:]:
        name = row[9].strip() if len(row) > 9 else ""
        if not name or name == "Total":
            continue
        if not any(row):
            break
        try:
            pts  = float(row[10]) if len(row) > 10 and row[10].strip() else 0.0
            reb  = float(row[11]) if len(row) > 11 and row[11].strip() else 0.0
            ast  = float(row[12]) if len(row) > 12 and row[12].strip() else 0.0
            stl  = float(row[13]) if len(row) > 13 and row[13].strip() else 0.0
            blk  = float(row[14]) if len(row) > 14 and row[14].strip() else 0.0
            gp   = float(row[15]) if len(row) > 15 and row[15].strip() else 0.0
            code = row[16].strip() if len(row) > 16 else ""
        except ValueError:
            continue
        if gp == 0:
            continue
        team = team_key.get(code, code)
        players.append({
            "name":     name,
            "team":     team,
            "gp":       int(gp),
            "pts":      round(pts, 1),
            "reb":      round(reb, 1),
            "ast":      round(ast, 1),
            "stl":      round(stl, 1),
            "blk":      round(blk, 1),
            # season totals (avg × GP, rounded to nearest whole number)
            "pts_tot":  int(round(pts * gp)),
            "reb_tot":  int(round(reb * gp)),
            "ast_tot":  int(round(ast * gp)),
            "stl_tot":  int(round(stl * gp)),
            "blk_tot":  int(round(blk * gp)),
        })
    players.sort(key=lambda x: -x["pts"])
    return players


# ── Parser: game results ─────────────────────────────────────────────────────

_ROUND_MAP = {
    "week one": "Week 1",  "week 1":   "Week 1",
    "week two": "Week 2",  "week 2":   "Week 2",
    "week three": "Week 3","week 3":   "Week 3",
    "play in":  "Play-In", "play-in":  "Play-In",
    "play offs start": "Playoffs",
}

def parse_games(rows: list) -> list:
    """
    Game results are stored implicitly in box score data throughout the file.
    Strategy: detect team section headers in col[0], accumulate player points
    from that section, derive score + winner from totals.
    - Round markers in col[0] reset the current round label.
    - 'Game N' markers in col[0] flush the current game pair.
    - Two consecutive team sections = one game.
    """
    games         = []
    current_round = "Week 1"
    game_teams    = []
    cur_team      = None
    cur_pts       = 0.0
    cur_players   = []   # individual player rows for current team

    def _flush_team():
        nonlocal cur_team, cur_pts, cur_players
        if cur_team:
            game_teams.append({
                "name":    cur_team,
                "score":   int(round(cur_pts)),
                "players": cur_players[:],
            })
        cur_team    = None
        cur_pts     = 0.0
        cur_players = []

    def _flush_game():
        if len(game_teams) >= 2:
            t1, t2 = game_teams[0], game_teams[1]
            winner = t1["name"] if t1["score"] > t2["score"] else t2["name"]
            games.append({
                "round":    current_round,
                "team1":    t1["name"], "score1": str(t1["score"]),
                "team2":    t2["name"], "score2": str(t2["score"]),
                "winner":   winner,
                "boxscore": {t1["name"]: t1["players"],
                             t2["name"]: t2["players"]},
            })
        game_teams.clear()

    for row in rows:
        c0       = row[0].strip()
        c0_lower = c0.lower()

        # Round / section markers
        matched_round = False
        for marker, label in _ROUND_MAP.items():
            if marker in c0_lower:
                _flush_team(); _flush_game()
                current_round = label
                matched_round = True
                break
        if matched_round:
            continue

        # "Game N" markers separate games within a round
        if re.match(r"game\s*\d", c0_lower):
            _flush_team(); _flush_game()
            continue

        # New team section — col[0] normalises to a known team name
        norm = normalize_team(c0)
        if norm in _KNOWN_TEAMS:
            _flush_team()
            if len(game_teams) >= 2:
                _flush_game()
            cur_team    = norm
            cur_pts     = 0.0
            cur_players = []
            continue

        # Player stat rows — accumulate points and capture individual stats
        if cur_team and len(row) > 2:
            name_cell = row[1].strip()
            pts_cell  = row[2].strip()
            if name_cell and name_cell not in ("Player", "Total") and pts_cell:
                try:
                    pts = float(pts_cell)
                    reb = float(row[3]) if len(row) > 3 and row[3].strip() else 0.0
                    ast = float(row[4]) if len(row) > 4 and row[4].strip() else 0.0
                    stl = float(row[5]) if len(row) > 5 and row[5].strip() else 0.0
                    blk = float(row[6]) if len(row) > 6 and row[6].strip() else 0.0
                    cur_pts += pts
                    cur_players.append({
                        "name": name_cell,
                        "pts":  int(round(pts)),
                        "reb":  int(round(reb)),
                        "ast":  int(round(ast)),
                        "stl":  int(round(stl)),
                        "blk":  int(round(blk)),
                    })
                except ValueError:
                    pass

    # Flush anything remaining at end of file
    _flush_team()
    _flush_game()
    return games


# ── HTML helpers ─────────────────────────────────────────────────────────────

_NAV = [
    ("index.html",     "Home"),
    ("standings.html", "Standings"),
    ("stats.html",     "Stats"),
    ("leaders.html",   "Leaders"),
    ("games.html",     "Games"),
    ("awards.html",    "Awards"),
    ("career.html",    "Career"),
    ("history.html",   "History"),
]

def html_page(title: str, body: str, active: str = "") -> str:
    nav = "\n  ".join(
        f'<a href="{href}" class="{"active" if active == href else ""}">{label}</a>'
        for href, label in _NAV
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{h(title)} — {LEAGUE_NAME}</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
<nav>
  <span class="league-name">{LEAGUE_NAME}</span>
  {nav}
</nav>
<div class="page">
{body}
</div>
<footer>{LEAGUE_NAME} &middot; Stats site updated from season data</footer>
<script src="assets/sort.js?v=3"></script>
</body>
</html>"""


def fmt(val, d=1):
    if isinstance(val, (int, float)):
        return f"{val:.{d}f}"
    return str(val)


# ── Page: index ──────────────────────────────────────────────────────────────

def gen_index(std, players, games, awards, season):
    champ        = std[0]["team"] if std else "TBD"
    champ_record = f"{std[0]['w']}–0" if std else ""

    def mini_table(headers, rows_html):
        ths = "".join(f"<th>{c}</th>" for c in headers)
        return f'<div class="table-wrap"><table><thead><tr>{ths}</tr></thead><tbody>{rows_html}</tbody></table></div>'

    # top-3 standings
    std_rows = "".join(
        f'<tr><td class="num">{i+1}</td><td class="highlight">{h(t["team"])}</td>'
        f'<td class="num">{t["w"]}</td><td class="num">{t["l"]}</td>'
        f'<td class="num">{t["pm"]:+.0f}</td></tr>'
        for i, t in enumerate(std[:3])
    )

    # top-3 scorers
    sc_rows = "".join(
        f'<tr><td class="highlight">{h(p["name"])}</td>'
        f'<td class="team-tag">{h(p["team"])}</td>'
        f'<td class="num">{fmt(p["pts"])}</td></tr>'
        for p in sorted(players, key=lambda x: -x["pts"])[:3]
    )

    # top-3 rebounders
    rb_rows = "".join(
        f'<tr><td class="highlight">{h(p["name"])}</td>'
        f'<td class="team-tag">{h(p["team"])}</td>'
        f'<td class="num">{fmt(p["reb"])}</td></tr>'
        for p in sorted(players, key=lambda x: -x["reb"])[:3]
    )

    # last 5 results
    last5 = games[-5:][::-1]
    g_rows = "".join(
        f'<tr><td>{h(g["round"])}</td>'
        f'<td class="{"winner" if g["winner"]==g["team1"] else "highlight"}">{h(g["team1"])}</td>'
        f'<td class="num">{h(g["score1"])}</td>'
        f'<td class="{"winner" if g["winner"]==g["team2"] else "highlight"}">{h(g["team2"])}</td>'
        f'<td class="num">{h(g["score2"])}</td></tr>'
        for g in last5
    )

    mvp  = next((w for n, w in awards if "mvp(reg" in n.lower()), "—")
    pmvp = next((w for n, w in awards if "pmvp"   in n.lower()), "—")

    return f"""
<h1>{LEAGUE_NAME}</h1>
<p class="subtitle">{h(season)}</p>

<div class="champ-banner">
  <span class="trophy">&#9733;</span>
  <div class="champ-info">
    <h2>{h(champ)}</h2>
    <p>{h(season)} Champions &middot; {champ_record} regular season &middot; MVP: {h(mvp)} &middot; Finals MVP: {h(pmvp)}</p>
  </div>
</div>

<div class="hero-grid">
  <div class="hero-panel">
    <h3>Standings</h3>
    {mini_table(["#","Team","W","L","+/-"], std_rows)}
    <p style="margin-top:.5rem;font-size:.8rem"><a href="standings.html" style="color:#1e90ff">Full standings &rarr;</a></p>
  </div>
  <div class="hero-panel">
    <h3>Scoring Leaders</h3>
    {mini_table(["Player","Team","PPG"], sc_rows)}
    <p style="margin-top:.5rem;font-size:.8rem"><a href="leaders.html" style="color:#1e90ff">All leaders &rarr;</a></p>
  </div>
  <div class="hero-panel">
    <h3>Rebounding Leaders</h3>
    {mini_table(["Player","Team","RPG"], rb_rows)}
  </div>
  <div class="hero-panel">
    <h3>Recent Results</h3>
    {mini_table(["Round","Team","Pts","Team","Pts"], g_rows)}
    <p style="margin-top:.5rem;font-size:.8rem"><a href="games.html" style="color:#1e90ff">Full results &rarr;</a></p>
  </div>
</div>"""


# ── Page: standings ──────────────────────────────────────────────────────────

def gen_standings(std, season):
    rows = "".join(
        f'<tr><td class="num">{i+1}</td>'
        f'<td class="highlight">{h(t["team"])}</td>'
        f'<td class="num">{t["w"]}</td>'
        f'<td class="num">{t["l"]}</td>'
        f'<td class="num">{t["w"]/(t["w"]+t["l"]):.3f}</td>'
        f'<td class="num">{t["pm"]:+.0f}</td></tr>'
        if (t["w"] + t["l"]) > 0 else
        f'<tr><td class="num">{i+1}</td>'
        f'<td class="highlight">{h(t["team"])}</td>'
        f'<td class="num">{t["w"]}</td>'
        f'<td class="num">{t["l"]}</td>'
        f'<td class="num">.000</td>'
        f'<td class="num">{t["pm"]:+.0f}</td></tr>'
        for i, t in enumerate(std)
    )
    return f"""
<h1>Standings</h1>
<p class="subtitle">{h(season)} — Regular Season Final</p>
<div class="table-wrap">
  <table>
    <thead><tr><th>#</th><th>Team</th><th>W</th><th>L</th><th>PCT</th><th>+/- Pts</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""


# ── Page: stats ──────────────────────────────────────────────────────────────

def _stats_table(players, mode="avg"):
    """Render a sortable stats table. mode='avg' or 'tot'."""
    if mode == "avg":
        headers = ["Player", "Team", "GP", "PTS", "REB", "AST", "STL", "BLK"]
        rows = "".join(
            f'<tr><td class="highlight">{h(p["name"])}</td>'
            f'<td class="team-tag">{h(p["team"])}</td>'
            f'<td class="num">{p["gp"]}</td>'
            f'<td class="num">{fmt(p["pts"])}</td>'
            f'<td class="num">{fmt(p["reb"])}</td>'
            f'<td class="num">{fmt(p["ast"])}</td>'
            f'<td class="num">{fmt(p["stl"])}</td>'
            f'<td class="num">{fmt(p["blk"])}</td></tr>'
            for p in players
        )
    else:
        headers = ["Player", "Team", "GP", "PTS", "REB", "AST", "STL", "BLK"]
        rows = "".join(
            f'<tr><td class="highlight">{h(p["name"])}</td>'
            f'<td class="team-tag">{h(p["team"])}</td>'
            f'<td class="num">{p["gp"]}</td>'
            f'<td class="num">{p["pts_tot"]}</td>'
            f'<td class="num">{p["reb_tot"]}</td>'
            f'<td class="num">{p["ast_tot"]}</td>'
            f'<td class="num">{p["stl_tot"]}</td>'
            f'<td class="num">{p["blk_tot"]}</td></tr>'
            for p in players
        )
    ths = "".join(f"<th>{c}</th>" for c in headers)
    return (
        f'<div class="table-wrap">'
        f'<table class="sortable">'
        f'<thead><tr>{ths}</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table></div>'
    )


def gen_stats(players, season):
    avg_table = _stats_table(players, "avg")
    tot_table = _stats_table(sorted(players, key=lambda x: -x["pts_tot"]), "tot")
    return f"""
<h1>Player Stats</h1>
<p class="subtitle">{h(season)} &middot; Click any column header to sort</p>
<div class="view-toggle">
  <button class="vtog active" data-view-show="avg-view">Per Game</button>
  <button class="vtog" data-view-show="tot-view">Season Totals</button>
</div>
<div id="avg-view">{avg_table}</div>
<div id="tot-view" style="display:none">{tot_table}</div>"""


# ── Page: leaders ────────────────────────────────────────────────────────────

def gen_leaders(players, season):
    cats = [
        ("Points",   "pts", "PPG"),
        ("Rebounds", "reb", "RPG"),
        ("Assists",  "ast", "APG"),
        ("Steals",   "stl", "SPG"),
        ("Blocks",   "blk", "BPG"),
    ]
    cards = ""
    for label, key, unit in cats:
        top5 = sorted(players, key=lambda x: -x[key])[:5]
        entries = "".join(
            f'<div class="leader-row">'
            f'<span class="rank">{i+1}</span>'
            f'<span class="name">{h(p["name"])}'
            f'<br><span style="font-size:.73rem;color:#78909c">{h(p["team"])}</span></span>'
            f'<span class="val">{fmt(p[key])}</span>'
            f'</div>'
            for i, p in enumerate(top5)
        )
        cards += (
            f'<div class="leader-card">'
            f'<h3>{label} <span style="color:#546e7a;font-size:.7rem">({unit})</span></h3>'
            f'{entries}</div>'
        )
    return f"""
<h1>League Leaders</h1>
<p class="subtitle">{h(season)} — Per-Game Averages, Top 5 Per Category</p>
<div class="leaders-grid">{cards}</div>"""


# ── Bracket helpers ──────────────────────────────────────────────────────────

def _annotate_playoff_rounds(playoff_games: list) -> list:
    """
    Tag each playoff game with its bracket round (Quarter / Semi / Final)
    by tracking which teams have already won a game as we go chronologically.
    """
    won_so_far = set()
    out = []
    for g in playoff_games:
        t1_won = g["team1"] in won_so_far
        t2_won = g["team2"] in won_so_far
        if t1_won and t2_won and len([x for x in out if x["bracket_round"] in ("Semi", "Final")]) >= 2:
            bracket_round = "Final"
        elif t1_won and t2_won:
            bracket_round = "Semi"
        else:
            bracket_round = "Quarter"
        out.append({**g, "bracket_round": bracket_round})
        won_so_far.add(g["winner"])
    return out


def _matchup_card(g: dict) -> str:
    c1 = "b-winner" if g["winner"] == g["team1"] else "b-loser"
    c2 = "b-winner" if g["winner"] == g["team2"] else "b-loser"
    champ = " &#9733;" if g.get("bracket_round") == "Final" and g["winner"] == g["winner"] else ""
    champ_tag = f'<span class="b-champ">{champ}</span>' if g.get("bracket_round") == "Final" else ""
    return (
        f'<div class="bracket-matchup">'
        f'<div class="b-team {c1}">'
        f'<span class="b-name">{h(g["team1"])}</span>'
        f'<span class="b-score">{h(g["score1"])}</span>'
        f'{"&#9733;" if c1 == "b-winner" and g.get("bracket_round") == "Final" else ""}'
        f'</div>'
        f'<div class="b-team {c2}">'
        f'<span class="b-name">{h(g["team2"])}</span>'
        f'<span class="b-score">{h(g["score2"])}</span>'
        f'{"&#9733;" if c2 == "b-winner" and g.get("bracket_round") == "Final" else ""}'
        f'</div>'
        f'</div>'
    )


def gen_bracket(games: list) -> str:
    """
    Build a bracket visual for Play-In + Playoff games.
    Returns empty string if no playoff data is present.
    """
    playin   = [g for g in games if g["round"] == "Play-In"]
    playoffs = [g for g in games if g["round"] == "Playoffs"]
    if not playoffs:
        return ""

    annotated = _annotate_playoff_rounds(playoffs)
    quarters  = [g for g in annotated if g["bracket_round"] == "Quarter"]
    semis     = [g for g in annotated if g["bracket_round"] == "Semi"]
    final     = next((g for g in annotated if g["bracket_round"] == "Final"), None)

    stages = []
    if playin:
        stages.append(("Play-In", [dict(g, bracket_round="PlayIn") for g in playin]))
    if quarters:
        stages.append(("Round 1", quarters))
    if semis:
        stages.append(("Semifinals", semis))
    if final:
        stages.append(("Championship", [final]))

    html = '<h2>Playoff Bracket</h2><div class="playoff-bracket">'
    for i, (label, stage_games) in enumerate(stages):
        if i > 0:
            html += '<div class="bracket-arrow">&#10142;</div>'
        cards = "".join(_matchup_card(g) for g in stage_games)
        html += (
            f'<div class="bracket-stage">'
            f'<div class="stage-label">{label}</div>'
            f'<div class="stage-games">{cards}</div>'
            f'</div>'
        )
    html += "</div>"
    return html


# ── Page: games ──────────────────────────────────────────────────────────────

def _box_table(players: list) -> str:
    """Render one team's box score as a compact table."""
    rows = "".join(
        f'<tr><td>{h(p["name"])}</td>'
        f'<td class="num">{p["pts"]}</td>'
        f'<td class="num">{p["reb"]}</td>'
        f'<td class="num">{p["ast"]}</td>'
        f'<td class="num">{p["stl"]}</td>'
        f'<td class="num">{p["blk"]}</td></tr>'
        for p in players if p["pts"] > 0 or p["reb"] > 0 or p["ast"] > 0
    )
    # always show non-contributors too
    zeros = "".join(
        f'<tr class="box-dnp"><td>{h(p["name"])}</td>'
        f'<td class="num">0</td><td class="num">0</td>'
        f'<td class="num">0</td><td class="num">0</td><td class="num">0</td></tr>'
        for p in players if p["pts"] == 0 and p["reb"] == 0 and p["ast"] == 0
    )
    return (
        '<table class="box-table">'
        '<thead><tr><th>Player</th><th>PTS</th><th>REB</th>'
        '<th>AST</th><th>STL</th><th>BLK</th></tr></thead>'
        f'<tbody>{rows}{zeros}</tbody>'
        '</table>'
    )


def _game_rows(g: dict, gid: int) -> str:
    """Render a clickable game summary row + hidden box score row."""
    c1 = "winner" if g["winner"] == g["team1"] else "highlight"
    c2 = "winner" if g["winner"] == g["team2"] else "highlight"
    bs  = g.get("boxscore", {})
    t1_box = _box_table(bs.get(g["team1"], []))
    t2_box = _box_table(bs.get(g["team2"], []))
    box_html = (
        f'<div class="boxscore-grid">'
        f'<div class="box-team">'
        f'<div class="box-team-hdr {c1}">{h(g["team1"])} &mdash; {h(g["score1"])}</div>'
        f'{t1_box}</div>'
        f'<div class="box-team">'
        f'<div class="box-team-hdr {c2}">{h(g["team2"])} &mdash; {h(g["score2"])}</div>'
        f'{t2_box}</div>'
        f'</div>'
    )
    return (
        f'<tr class="game-summary-row" data-box="box-{gid}">'
        f'<td class="{c1}">{h(g["team1"])}</td>'
        f'<td class="num">{h(g["score1"])}</td>'
        f'<td class="vs-cell">vs</td>'
        f'<td class="{c2}">{h(g["team2"])}</td>'
        f'<td class="num">{h(g["score2"])}'
        f'<span class="expand-icon">&#9660;</span></td>'
        f'</tr>'
        f'<tr class="box-score-row" id="box-{gid}" style="display:none">'
        f'<td colspan="5">{box_html}</td>'
        f'</tr>'
    )


def gen_games(games, season):
    bracket_html = gen_bracket(games)

    reg_games = [g for g in games if g["round"] not in ("Play-In", "Playoffs")]
    gid = 0
    body = ""
    for round_name, group in groupby(reg_games, key=lambda g: g["round"]):
        body += f'<tr><td colspan="5" class="round-header">{h(round_name)}</td></tr>'
        for g in group:
            body += _game_rows(g, gid)
            gid += 1

    return f"""
<h1>Game Results</h1>
<p class="subtitle">{h(season)} &middot; Click any game to see the box score</p>

{bracket_html}

<h2>Regular Season</h2>
<div class="table-wrap">
  <table class="games-table">
    <thead><tr><th>Team</th><th>Pts</th><th></th><th>Team</th><th>Pts</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</div>"""


# ── Page: awards ─────────────────────────────────────────────────────────────

def gen_awards(awards, season):
    cards = "".join(
        f'<div class="award-card">'
        f'<span class="award-name">{h(name)}</span>'
        f'<span class="award-winner">{h(winner)}</span>'
        f'</div>'
        for name, winner in awards
    )
    return f"""
<h1>Awards</h1>
<p class="subtitle">{h(season)}</p>
<div class="awards-grid">{cards}</div>"""


# ── Page: history ────────────────────────────────────────────────────────────

def gen_history(all_data):
    tabs = ""
    sections = ""
    for i, (name, data) in enumerate(all_data):
        sid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        active_cls = "active" if i == 0 else ""
        tabs += f'<button class="season-tab {active_cls}" data-target="s-{sid}">{h(name)}</button>\n'

        std_rows = "".join(
            f'<tr><td class="num">{j+1}</td><td class="highlight">{h(t["team"])}</td>'
            f'<td class="num">{t["w"]}</td><td class="num">{t["l"]}</td>'
            f'<td class="num">{t["pm"]:+.0f}</td></tr>'
            for j, t in enumerate(data["standings"])
        )
        # mini leaders (pts / reb / ast)
        cards = ""
        for label, key, unit in [("Points","pts","PPG"),("Rebounds","reb","RPG"),("Assists","ast","APG")]:
            entries = "".join(
                f'<div class="leader-row"><span class="rank">{k+1}</span>'
                f'<span class="name">{h(p["name"])}'
                f'<br><span style="font-size:.73rem;color:#78909c">{h(p["team"])}</span></span>'
                f'<span class="val">{fmt(p[key])}</span></div>'
                for k, p in enumerate(sorted(data["players"], key=lambda x: -x[key])[:3])
            )
            cards += f'<div class="leader-card"><h3>{label}</h3>{entries}</div>'

        visible_cls = "visible" if i == 0 else ""
        sections += f"""
<div class="season-section {visible_cls}" id="s-{sid}">
  <h2>Standings</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>#</th><th>Team</th><th>W</th><th>L</th><th>+/-</th></tr></thead>
      <tbody>{std_rows}</tbody>
    </table>
  </div>
  <h2>Stat Leaders</h2>
  <div class="leaders-grid">{cards}</div>
</div>"""

    return f"""
<h1>Season History</h1>
<p class="subtitle">Select a season to view standings and leaders</p>
<div class="season-tabs">{tabs}</div>
{sections}"""


# ── Career stats ─────────────────────────────────────────────────────────────

def compute_career_stats(all_data: list) -> list:
    """
    Aggregate per-season player stats across all loaded seasons.
    Returns list of player dicts with career totals and averages.
    """
    career = {}
    for season_name, data in all_data:
        for p in data["players"]:
            name = p["name"]
            if name not in career:
                career[name] = {
                    "gp": 0, "pts": 0.0, "reb": 0.0,
                    "ast": 0.0, "stl": 0.0, "blk": 0.0,
                    "seasons": 0, "teams": set(),
                }
            gp = p["gp"]
            c  = career[name]
            c["gp"]      += gp
            c["pts"]     += p["pts"] * gp
            c["reb"]     += p["reb"] * gp
            c["ast"]     += p["ast"] * gp
            c["stl"]     += p["stl"] * gp
            c["blk"]     += p["blk"] * gp
            c["seasons"] += 1
            c["teams"].add(p["team"])

    result = []
    for name, c in career.items():
        gp = c["gp"]
        if gp == 0:
            continue
        result.append({
            "name":     name,
            "seasons":  c["seasons"],
            "teams":    ", ".join(sorted(c["teams"])),
            "gp":       gp,
            "pts":      round(c["pts"] / gp, 1),
            "reb":      round(c["reb"] / gp, 1),
            "ast":      round(c["ast"] / gp, 1),
            "stl":      round(c["stl"] / gp, 1),
            "blk":      round(c["blk"] / gp, 1),
            "pts_tot":  int(round(c["pts"])),
            "reb_tot":  int(round(c["reb"])),
            "ast_tot":  int(round(c["ast"])),
            "stl_tot":  int(round(c["stl"])),
            "blk_tot":  int(round(c["blk"])),
        })
    result.sort(key=lambda x: -x["pts"])
    return result


def gen_career(career_players: list) -> str:
    avg_rows = "".join(
        f'<tr><td class="highlight">{h(p["name"])}</td>'
        f'<td class="num">{p["seasons"]}</td>'
        f'<td class="num">{p["gp"]}</td>'
        f'<td class="num">{fmt(p["pts"])}</td>'
        f'<td class="num">{fmt(p["reb"])}</td>'
        f'<td class="num">{fmt(p["ast"])}</td>'
        f'<td class="num">{fmt(p["stl"])}</td>'
        f'<td class="num">{fmt(p["blk"])}</td>'
        f'<td class="team-tag" style="font-size:.75rem">{h(p["teams"])}</td></tr>'
        for p in career_players
    )
    tot_rows = "".join(
        f'<tr><td class="highlight">{h(p["name"])}</td>'
        f'<td class="num">{p["seasons"]}</td>'
        f'<td class="num">{p["gp"]}</td>'
        f'<td class="num">{p["pts_tot"]}</td>'
        f'<td class="num">{p["reb_tot"]}</td>'
        f'<td class="num">{p["ast_tot"]}</td>'
        f'<td class="num">{p["stl_tot"]}</td>'
        f'<td class="num">{p["blk_tot"]}</td>'
        f'<td class="team-tag" style="font-size:.75rem">{h(p["teams"])}</td></tr>'
        for p in sorted(career_players, key=lambda x: -x["pts_tot"])
    )
    avg_table = (
        '<div class="table-wrap"><table class="sortable">'
        '<thead><tr><th>Player</th><th>Seasons</th><th>GP</th>'
        '<th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>Team(s)</th>'
        '</tr></thead>'
        f'<tbody>{avg_rows}</tbody></table></div>'
    )
    tot_table = (
        '<div class="table-wrap"><table class="sortable">'
        '<thead><tr><th>Player</th><th>Seasons</th><th>GP</th>'
        '<th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>Team(s)</th>'
        '</tr></thead>'
        f'<tbody>{tot_rows}</tbody></table></div>'
    )
    return f"""
<h1>Career Stats</h1>
<p class="subtitle">All-time per-game averages and totals across every season &middot; Click any column to sort</p>
<div class="view-toggle">
  <button class="vtog active" data-view-show="cavg-view">Per Game</button>
  <button class="vtog" data-view-show="ctot-view">Career Totals</button>
</div>
<div id="cavg-view">{avg_table}</div>
<div id="ctot-view" style="display:none">{tot_table}</div>"""


# ── Main ─────────────────────────────────────────────────────────────────────

def build():
    seasons_file = os.path.join(BASE, "data", "seasons.json")
    with open(seasons_file, encoding="utf-8") as f:
        seasons = json.load(f)

    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)

    all_data = []
    for season in seasons:
        name = season["name"]
        print(f"Parsing {name}...")
        rows     = load_csv(season["scorecard"])
        team_key = parse_team_key(rows)
        std      = parse_standings(rows)
        awards   = parse_awards(rows)
        players  = parse_player_stats(rows, team_key)
        games    = parse_games(rows)
        print(f"  {len(std)} teams  |  {len(players)} players  |  "
              f"{len(games)} games  |  {len(awards)} awards")
        all_data.append((name, {
            "standings": std, "awards": awards,
            "players": players, "games": games,
        }))

    if not all_data:
        print("No seasons found in data/seasons.json — nothing to build.")
        return

    latest_name, latest = all_data[-1]
    std, players, games, awards = (
        latest["standings"], latest["players"],
        latest["games"],     latest["awards"],
    )

    career_players = compute_career_stats(all_data)

    pages = {
        "index.html":    (latest_name,    gen_index(std, players, games, awards, latest_name)),
        "standings.html":("Standings",    gen_standings(std, latest_name)),
        "stats.html":    ("Player Stats", gen_stats(players, latest_name)),
        "leaders.html":  ("Leaders",      gen_leaders(players, latest_name)),
        "games.html":    ("Games",        gen_games(games, latest_name)),
        "awards.html":   ("Awards",       gen_awards(awards, latest_name)),
        "career.html":   ("Career Stats", gen_career(career_players)),
        "history.html":  ("History",      gen_history(all_data)),
    }

    for filename, (title, body) in pages.items():
        out_path = os.path.join(OUT, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_page(title, body, active=filename))
        print(f"  wrote {filename}")

    print(f"\nDone — {len(pages)} pages in docs/")
    print("Open docs/index.html in a browser to preview.")
    print("Push to GitHub and enable Pages (Settings > Pages > main branch, /docs) to publish.")


if __name__ == "__main__":
    build()
