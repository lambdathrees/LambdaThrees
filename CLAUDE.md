# Project Context

This is my AI agent workspace. I use this for forcasting, data organization, and organizing statistics 

# About Me

I am the commissioner on a basketball league tasked with keeping player statistics, determining awards, organizing seeding, and overseeing the draft. My primary audience is the players in my league with a secondary audience being my two fellow commissioners. I prefer clear, insightful output. 

# Rules

 - Always ask clarifying questions before starting a complex task
 - If certain statistics seem wrong or confusing, ask for further context
 - Keep reports and summaries concise - bullet points over paragraphs
 - Save all output files to the output folder


 # Project Structure

 - workflows/ - Workflow instruction files(plain english recipes the agent follows)
 - output/ - finished deliverables(reports, drafts, analysis)
 - resources/ - reference docs and templates
 - data/ - raw input files (CSV or converted Excel sheets)
 - data/processed/ - auto-converted CSVs from Excel (output of scripts/prepare_data.py)
 - scripts/ - utility scripts

# Workflows

## Season Forecast
File: `workflows/season-forecast.md`

Analyzes past-season player statistics, team records, and league trends to produce a next-season forecast report. Output includes pre-season power rankings, team outlooks, draft analysis, and potential trade proposals.

**To run:** Start a new chat and say:
> "Follow the workflow in @workflows/season-forecast.md"

**To prepare Excel data:** Run `python scripts/prepare_data.py data/your-file.xlsx` to convert all sheets to CSV, then reference the files in chat with `@data/processed/sheet-name.csv`.

## Build Website
File: `workflows/build-website.md`

Generates a public static website (7 HTML pages) from your season data. Includes standings, player stats, game results, league leaders, awards, and a historical archive. Hosted for free on GitHub Pages.

**To run:** `python scripts/build_site.py`

**To publish:** Commit the `docs/` folder and push to GitHub. Enable Pages in repo Settings → Pages → main branch, /docs folder.

**To add a new season:** Add the processed CSV to `data/seasons.json`, then re-run the build script.