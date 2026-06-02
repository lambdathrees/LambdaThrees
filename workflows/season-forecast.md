# Season Forecast Workflow

Use this file to run a full end-of-season analysis and next-season forecast for the league.
Start a new Claude Code chat session and say:

> "Follow the workflow in @workflows/season-forecast.md"

Claude will walk through every phase below in order.

---

## How to run this workflow

When invoked, Claude must follow these phases **in order**. Do not skip ahead or generate any forecast output until all earlier phases are complete.

---

## Phase 1 — Upfront League Intake

**Before asking for any data files**, present the user with this numbered questionnaire in a single message and wait for all answers before proceeding.

Tell the user:

> Before I load any data, I need a few details about your league so my analysis is accurate. Please answer as many of these as you can — you can skip anything that doesn't apply.
>
> 1. **League name** — What is your league called?
> 2. **Number of teams** — How many teams are in the league, and how many players per roster?
> 3. **Regular season format** — How many games does each team play? Are there divisions or conferences?
> 4. **Playoff format** — How many teams qualify for the playoffs? Is it single-elimination, best-of series, or something else? How many rounds?
> 5. **Draft format** — Snake draft, auction, or lottery? Are draft pick positions based on final standings (worst-to-first), randomized, or something else? Are there rookie eligibility rules?
> 6. **Awards** — What individual awards does your league give out? (e.g., MVP, Rookie of the Year, Defensive Player of the Year, Sixth Man, etc.)
> 7. **Stat categories** — What statistics are tracked? (e.g., points, rebounds, assists, steals, blocks, FG%, 3-pointers, +/−) Is this a fantasy-style league or real on-court stats?
> 8. **Special rules or context** — Any trades, waivers, salary cap, expansion teams, rule changes, or anything else I should know going into the analysis?

After the user responds, confirm your understanding by summarizing the league format back to them in 3–5 bullet points, then ask if anything needs correcting before moving on.

---

## Phase 2 — Data Loading

Once the league format is confirmed, ask the user to provide their spreadsheet data. Say:

> Now I'm ready for the data. Please share your spreadsheet files using one of these methods:
>
> - **Preferred:** Save each Excel sheet as a CSV (File → Save As → CSV in Excel), place the files in the `data/` folder, and reference them here with `@data/your-file.csv`
> - **Alternative:** Run the helper script to auto-convert: `python scripts/prepare_data.py data/your-file.xlsx` — this exports each sheet to `data/processed/`
>
> Useful files to include (share whatever you have):
> - Player statistics for the past season(s)
> - Team win/loss records and standings
> - Playoff results
> - Past draft history or draft order
> - Award winners from prior seasons

As the user shares each file, read it with the Read tool. After reading all files, produce a brief **Data Summary** in this format:

```
Files loaded:
- [filename] — [N rows, key columns found]
- ...

What I found:
- [Key observations about the data — notable stats, outlier performances, missing columns, etc.]

Potential data gaps:
- [Anything that seems missing that could affect the forecast]
```

---

## Phase 3 — Follow-up Questions

After reviewing the data, ask any targeted clarifying questions based on what was found. Frame it as:

> Based on the data, I have a few follow-up questions before I finalize the forecast:

Focus questions on:
- Ambiguous column names or stat categories that are unclear
- Players with very high or very low stats that might reflect injuries, trades, or partial seasons
- Roster moves (trades, signings, departures) that happened after the season ended and aren't captured in the data
- Any context about team strength that the numbers might not show (e.g., a strong team that underperformed due to scheduling, injuries, or off-court issues)
- Draft pick positions if not already provided (who picks where next season?)

Wait for the user's answers before generating any forecast output.

---

## Phase 4 — Generate the Season Forecast Report

With all context gathered, generate the full forecast report and save it to `output/season-YYYY-forecast.md` (replace YYYY with the upcoming season year). The report must follow this exact structure:

---

```markdown
# [League Name] — [Season YYYY] Pre-Season Forecast

*Generated: [date]*

---

## Executive Summary

- [Bullet 1: Overall league narrative heading into next season]
- [Bullet 2: Team to watch / favorite]
- [Bullet 3: Key storyline (draft, rivalry, breakout player, etc.)]
- [Bullet 4: Biggest question mark]
- [Bullet 5: Wild card / dark horse]

---

## Pre-Season Power Rankings

| Rank | Team | Last Season Record | Projected Outlook | Key Reason |
|------|------|--------------------|-------------------|------------|
| 1    | ...  | ...                | Contender         | ...        |
| 2    | ...  | ...                | ...               | ...        |
| ...  |      |                    |                   |            |

Brief narrative (2–3 sentences) explaining the top 3 teams and any notable movers up or down from last season.

---

## Team-by-Team Outlook

For each team, use this format:

### [Team Name]
- **Last season:** [Record / finish]
- **Strengths:** [1–2 bullet points]
- **Weaknesses:** [1–2 bullet points]
- **Key player:** [Name — why they matter]
- **Ceiling:** [Best realistic outcome]
- **Floor:** [Worst realistic outcome]
- **Draft need:** [What position/skill they should target in the draft]

---

## Draft Analysis

### Projected Draft Order
| Pick | Team | Last Season Finish | Rationale |
|------|------|--------------------|-----------|
| 1    | ...  | ...                | ...       |
| 2    | ...  | ...                | ...       |
| ...  |      |                    |           |

### Top Available Players / Key Draft Targets
List the most impactful players likely available in the draft, with a brief note on who they'd help most.

| Player | Position | Projected Value | Best Fit |
|--------|----------|-----------------|----------|
| ...    | ...      | ...             | ...      |

### Team Draft Recommendations
For each team, one sentence on their ideal draft strategy given their pick position and roster need.

---

## Potential Trade Proposals

> Note: Each team appears in at most 2 proposals. Proposals use projected draft picks and the roster needs identified above.

For each proposal, use this format:

### Trade [N]: [Team A] ↔ [Team B]
- **[Team A] sends:** [player(s) and/or picks]
- **[Team B] sends:** [player(s) and/or picks]
- **Why Team A does this:** [1 sentence]
- **Why Team B does this:** [1 sentence]
- **Likelihood:** High / Medium / Low — [brief reason]

---

## Off-Season Questions to Watch

A short numbered list (4–6 items) of the biggest unresolved questions that will shape next season — things like: will a key player improve, will a struggling team retool, how will a top pick impact their new team, etc.

---

*Report generated by the Season Forecast Workflow. Data based on [seasons provided]. Forecasts are projections, not guarantees.*
```

---

## Phase 5 — Wrap-up

After saving the report, tell the user:

> Your forecast report has been saved to `output/season-YYYY-forecast.md`. Here are a few things you can ask me to do next:
> - Dive deeper into any team or player
> - Simulate a specific trade scenario
> - Generate a playoff bracket prediction
> - Adjust the power rankings based on off-season moves you share

---

## Workflow Rules for Claude

- Never generate forecast content before completing Phases 1–3.
- Always save the final report to `output/` — do not just print it to chat.
- Keep the tone factual and commissioner-facing (this report may be shared with league players).
- If a stat seems implausible, flag it and ask before incorporating it into predictions.
- For 3v3 basketball: rosters are small, so individual player impact is amplified — weight individual star performers heavily in power rankings.
