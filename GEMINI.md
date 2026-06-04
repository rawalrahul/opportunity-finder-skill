# Gemini Context: Opportunity Finder Skill

This repository packages the `opportunity-finder` Agent Skill. When a user asks Gemini to find, research, validate, or rank opportunities from online discussion signals, use the skill workflow in `SKILL.md`.

## Use This Skill For

- Finding product or business opportunities in a market, niche, topic, or community.
- Mining pain points from Hacker News and Reddit.
- Ranking opportunities with the bundled deterministic scorer.
- Creating Markdown, HTML, or PDF reports that resemble the examples in `examples/`.

## Workflow For Gemini

1. Read `SKILL.md` before running the workflow.
2. Fetch real posts with `scripts/fetch_posts.py`.
3. Extract and cluster opportunities from fetched evidence. Do not invent posts or quotes.
4. Score with `scripts/score.py`.
5. Render saved deliverables with `scripts/report.py` when the user asks for a report or artifact.
6. Prefer Markdown reports for GitHub-viewable examples; generate PDF only when explicitly requested or useful.

## Important Commands

```bash
python scripts/fetch_posts.py --query "<topic>" --source all --limit 30 --out posts.json
python scripts/score.py --in scored_input.json --out ranked.json
python scripts/report.py --in ranked.json --topic "<topic>" --out report.md
```

Optional PDF export:

```bash
python scripts/report.py --in ranked.json --topic "<topic>" --out report.md --html report.html --pdf report.pdf
```

## Evidence Rules

- Always ground opportunities in fetched posts.
- Include real quotes with URLs.
- Mention when a source is unavailable or blocked.
- If Reddit JSON is blocked, `fetch_posts.py` can fall back to Scrapling + old.reddit when Scrapling is installed.
- Do not treat market-size estimates as primary evidence unless they were separately sourced.

## Output Style

Use the files in `examples/` as the preferred report style:

- `examples/Developer_Tooling_Opportunities.md`
- `examples/IT_Operations_Automation_Opportunities.md`

Reports should include an executive summary, ranked opportunity table, opportunity details, evidence, market/competition notes when available, and a clear recommendation.
