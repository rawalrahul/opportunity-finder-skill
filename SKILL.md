---
name: opportunity-finder
description: Use in Codex, Claude, or Gemini CLI when the user wants to discover, research, or rank business/product opportunities and pain points from real online discussions (Reddit, Hacker News) for a topic, niche, keyword, or community - e.g. "find opportunities in X", "what are people frustrated about in Y", "pain points around Z", market/idea validation from social signal.
---

# Opportunity Finder

## Overview

Discovers business opportunities by mining real complaints from Reddit + Hacker News, then scoring them with a 7-factor algorithm. Scripts handle deterministic work (fetching, math); **you** (the agent) handle judgment (frustration detection, clustering) - no external LLM API or key needed.

Pipeline: `fetch posts` -> `you extract opportunities` -> `you cluster` -> `score.py ranks` -> `report.py renders` -> present or save.

## Workflow

### 1. Fetch raw posts

```bash
python scripts/fetch_posts.py --query "<topic>" --source all --limit 30 --out posts.json
```

- `--source`: `all` (default), `hn`, or `reddit`.
- `--limit`: posts per Reddit search/subreddit and per HN tag (`story`, `comment`), so HN may return up to roughly 2x this value before dedupe.
- `--subreddits "SaaS,startups,smallbusiness"`: restrict Reddit to specific communities (empty = search all of Reddit).
- HN needs no auth. Reddit uses public `.json` endpoints (no key, but may rate-limit at high volume - the script skips failures silently).

Read `posts.json`. If empty, broaden the query or try `--source hn` only.

### 2. Extract opportunities (your judgment)

Act as an expert market researcher. Read every post. Identify distinct pain points, frustrations, and unmet needs related to the query. Frustration signal words: frustrated, annoyed, hate, broken, useless, wish there was, no good, waste of time, can't, impossible, expensive, alternative to.

For each pain point produce an object:
- `title`: clear actionable opportunity name (5-10 words)
- `description`: 2-3 sentences - the opportunity and why it matters
- `frustrationIntensity`: integer 1-10 (1 = mild annoyance, 10 = hair-on-fire)
- `quotes`: array of `{text, source, url, platform, date}` - real quotes from the posts as evidence
- `existingSolutions`: object `{ "ToolName": "its weakness", ... }` (empty `{}` if none)
- `suggestedApproach`: one of `SaaS` | `service` | `content` | `tool`
- `platforms`: list of platforms where it appeared

### 3. Cluster similar opportunities (your judgment)

Merge opportunities describing the same core problem: keep the clearest title, combine descriptions and quotes, average frustration intensity, consolidate solutions, union platforms.

### 4. Score and rank

Write `{ "posts": [...], "opportunities": [...] }` to a file, then:

```bash
python scripts/score.py --in scored_input.json --out ranked.json
```

`score.py` computes 7 weighted factors (frequency .25, frustration .20, recency .15, platform-diversity .10, engagement .10, competition-gap .10, market-size .10), a `totalScore` (0-100), and a `scoreLabel`. It re-matches each opportunity to related posts to compute frequency/recency/engagement, so always pass the full `posts` array.

### 5. Generate a report

When the user asks for a saved report, PDF, HTML, deliverable, or "these kinds of reports", render the ranked output with:

```bash
python scripts/report.py --in ranked.json --topic "<topic>" --out report.md
```

Optional exports:

```bash
python scripts/report.py --in ranked.json --topic "<topic>" --out report.md --html report.html --pdf report.pdf
```

PDF export requires Playwright and a local Chromium install. If PDF export is unavailable, save Markdown and/or HTML and state that PDF export could not be generated.

### 6. Present

Sort is already done (desc by score). For each opportunity show: title, **score + label**, frustration intensity, platforms, top 2-3 quotes with links, existing solutions + weaknesses, suggested approach. Lead with the highest scorers. If a report was saved, link or name the saved file path.

## Score interpretation

| Score | Label | Meaning |
|-------|-------|---------|
| 80-100 | High Priority | Strong signal across platforms |
| 60-79 | Worth Investigating | Solid, may need validation |
| 40-59 | Moderate Potential | Niche or seasonal |
| <40 | Weak Signal | Likely noise or well-served |

## Common mistakes

- **Skipping fetch, inventing posts**: always run `fetch_posts.py`. Opportunities must be grounded in real fetched quotes.
- **Not passing `posts` to score.py**: frequency/recency/engagement factors need the post array; without it scores collapse.
- **Not creating a report when requested**: use `report.py` after scoring so the user gets a reusable artifact, not only a chat summary.
- **Old posts score low on recency** (linear decay to 0 at 90 days) - this is correct; flag genuinely stale topics.
- **Reddit returns nothing**: rate-limited or query too narrow. `fetch_posts.py` falls back to Scrapling + old.reddit when Scrapling is installed; otherwise retry with `--source hn` or broaden query. Don't fabricate.

## Scope

This is on-demand analysis for the operator running it. It does NOT provide real-time monitoring, alerts, bots, dashboards, or scheduled reports - those require an always-on hosted service (the full OpportunityFinder SaaS), not a skill.
