# Opportunity Finder Skill

Opportunity Finder is an Agent Skill for Codex, Claude, and Gemini CLI that discovers and ranks product or business opportunities from real online discussions.

It fetches posts from Hacker News and Reddit, helps the agent extract pain-point clusters, scores those opportunities with a deterministic 7-factor model, and renders polished opportunity reports.

## What It Is Good For

- Finding opportunities in a topic, niche, market, or community.
- Researching pain points from Reddit and Hacker News.
- Ranking ideas by frequency, frustration, recency, engagement, platform diversity, competition gap, and market-size proxy.
- Generating Markdown, HTML, or PDF-style reports from ranked opportunities.

Example prompts:

- `find opportunities in developer tooling`
- `find opportunities in IT operations automation`
- `what are people frustrated about in small business back-office automation`
- `rank product ideas around bookkeeping automation`

## Repository Layout

```text
.
|-- SKILL.md
|-- GEMINI.md
|-- agents/
|   `-- openai.yaml
|-- scripts/
|   |-- fetch_posts.py
|   |-- score.py
|   `-- report.py
`-- examples/
    |-- README.md
    |-- Developer_Tooling_Opportunities.md
    |-- Developer_Tooling_Opportunities.pdf
    |-- IT_Operations_Automation_Opportunities.md
    `-- IT_Operations_Automation_Opportunities.pdf
```

## Workflow

Fetch posts:

```bash
python scripts/fetch_posts.py --query "developer tooling pain" --source all --limit 30 --out posts.json
```

The agent reads `posts.json`, extracts opportunity objects, clusters similar pains, then writes:

```json
{
  "posts": [],
  "opportunities": []
}
```

Score opportunities:

```bash
python scripts/score.py --in scored_input.json --out ranked.json
```

Generate a report:

```bash
python scripts/report.py --in ranked.json --topic "Developer Tooling" --out report.md
```

Optional HTML/PDF export:

```bash
python scripts/report.py --in ranked.json --topic "Developer Tooling" --out report.md --html report.html --pdf report.pdf
```

PDF export requires Playwright and a Chromium install:

```bash
python -m playwright install chromium
```

## Reddit Support

The Reddit JSON endpoint often blocks unauthenticated requests. `fetch_posts.py` first tries Reddit's public JSON endpoint, then falls back to Scrapling + old.reddit when Scrapling is installed.

Install Scrapling if needed:

```bash
python -m pip install scrapling
```

## Example Reports

The `examples/` folder contains directly viewable Markdown reports plus PDF exports. Start here:

- [Examples index](examples/README.md)
- [Developer Tooling Opportunities](examples/Developer_Tooling_Opportunities.md)
- [IT Operations Automation Opportunities](examples/IT_Operations_Automation_Opportunities.md)

PDF versions are also included for download/export parity:

- [Developer_Tooling_Opportunities.pdf](examples/Developer_Tooling_Opportunities.pdf)
- [IT_Operations_Automation_Opportunities.pdf](examples/IT_Operations_Automation_Opportunities.pdf)

These example deliverables clarify the desired report quality, structure, and level of evidence.

## Install As A Skill

### Gemini CLI

Gemini CLI can install Agent Skills directly from Git:

```bash
gemini skills install https://github.com/rawalrahul/opportunity-finder-skill.git --consent
gemini skills list
```

For local development:

```bash
gemini skills link /path/to/opportunity-finder-skill
/skills reload
```

This repo also includes `GEMINI.md`, so when opened directly in Gemini CLI it provides project context and points Gemini to the skill workflow.

### Codex / Claude

Copy this folder to your skills directory:

```bash
# Codex
cp -R opportunity-finder-skill ~/.codex/skills/opportunity-finder

# Claude
cp -R opportunity-finder-skill ~/.claude/skills/opportunity-finder
```

On Windows PowerShell:

```powershell
Copy-Item -Recurse opportunity-finder-skill $HOME\.codex\skills\opportunity-finder
Copy-Item -Recurse opportunity-finder-skill $HOME\.claude\skills\opportunity-finder
```

## Notes

This skill is for on-demand opportunity research. It does not provide monitoring, scheduled reports, dashboards, or hosted alerts.
