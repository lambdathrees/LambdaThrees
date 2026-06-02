# Build Website Workflow

Use this workflow to generate or update the Lambda 3s public stats website.
This is a **separate workflow** from `workflows/season-forecast.md`.

The site is a set of static HTML files in the `docs/` folder that can be hosted
for free on GitHub Pages. Every time you run the build script, all pages are
regenerated from the latest data.

---

## What the site includes

- **Home** — Champion banner, top standings, scoring/rebounding leaders, recent results
- **Standings** — Full regular-season final standings with W/L/PCT/Point Margin
- **Stats** — Per-game averages for every player (sortable by any column)
- **Leaders** — Top 5 per category: Points, Rebounds, Assists, Steals, Blocks
- **Games** — Full game log grouped by round (Week 1/2/3, Play-In, Playoffs)
- **Awards** — All season awards and winners
- **History** — Season-by-season standings and leaders (grows as you add seasons)

---

## How to update the site

### Step 1 — Convert your Excel data to CSV

If you have a new or updated Excel file:

```
python scripts/prepare_data.py data/your-file.xlsx
```

This exports each sheet to `data/processed/`. The site builder reads from there.

### Step 2 — Register the season (first time only per season)

Open `data/seasons.json` and add an entry:

```json
[
  {
    "name": "Spring 2026",
    "scorecard": "data/processed/Spring_26.csv",
    "teams": "data/processed/Teams.csv"
  },
  {
    "name": "Fall 2026",
    "scorecard": "data/processed/Fall_26.csv",
    "teams": "data/processed/Teams_Fall_26.csv"
  }
]
```

The **last entry** in the list becomes the "current season" shown on all main pages.
Earlier entries appear in the History tab.

### Step 3 — Build the site

```
python scripts/build_site.py
```

This regenerates all 7 pages in the `docs/` folder and prints a summary of what was parsed.

### Step 4 — Preview locally (optional)

Open `docs/index.html` in any browser to verify the output before publishing.

### Step 5 — Publish to GitHub Pages

```
git add docs/ data/seasons.json
git commit -m "Update site — Spring 2026"
git push
```

GitHub Pages auto-deploys within ~60 seconds. Your site will be live at:
`https://your-username.github.io/your-repo-name/`

---

## One-time GitHub Pages setup

Do this once when you first push the project to GitHub:

1. Go to your repository on GitHub
2. Click **Settings** → **Pages** (in the left sidebar)
3. Under **Source**, select:
   - Branch: `main`
   - Folder: `/docs`
4. Click **Save**
5. GitHub will show your public URL — share it with league players

---

## Spreadsheet format requirements

The build script is designed for the **Lambda Threes Scorecard** Excel format.
It expects:
- One main sheet per season with box scores, player averages, standings, and awards
- Team section headers in column A (e.g., "Team Grit", "Team Laub")
- Player stats rows with player name in column B, points in column C
- Per-game averages table with "Player" header in column J and "Games Played" in column P
- Standings table with team names in column O and W/L/PM in columns P–R
- Awards in any column that contains keywords: MVP, ROTY, First Team, Award, Fourth Man

If the spreadsheet format changes significantly, the parsers in `scripts/build_site.py`
may need updating. Ask Claude: *"Update the site builder for my new spreadsheet format"*
and share the new file.

---

## Adding a past season

To add historical data for a season that already happened:

1. Add the old season's scorecard CSV to `data/processed/`
2. Add it as an entry **before** the current season in `data/seasons.json`
3. Run `python scripts/build_site.py`
4. The History page will now include a tab for that season

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `0 players` in build output | The averages table wasn't found — check that your CSV has "Player" in col J and "Games Played" in col P on the same header row |
| `0 teams` in standings | Standings not found — check that col O has team names and col P has win totals |
| `0 games` | No team section headers detected in col A — verify team names start with "Team " |
| Wrong scores | A team section may be missing its player rows — check for blank rows between header and stats |
| Awards missing | Award names must contain one of: mvp, roty, first team, award, fourth man |
