#!/usr/bin/env python3
"""
score.py - 7-factor opportunity scoring (faithful port of the OpportunityFinder
scorer.ts + scoring/factors/*.ts).

Input JSON (stdin or --in):
{
  "posts": [ <CollectedPost>, ... ],          # from fetch_posts.py
  "opportunities": [
    {
      "title": "...",
      "description": "...",
      "frustrationIntensity": 7,              # 1-10, judged by the agent
      "quotes": [ {"text": "...", "source": "...", "url": "...",
                   "platform": "...", "date": "..."} ],
      "existingSolutions": {"ToolName": "weakness", ...},
      "suggestedApproach": "SaaS|service|content|tool",
      "platforms": ["Reddit", "HackerNews"]    # optional
    }, ...
  ]
}

Output: same opportunities, each with `scoring` (7 factor values 0-100),
`totalScore` (0-100), and `scoreLabel`, sorted descending by totalScore.

Weights (sum = 1.0):
  frequency .25  frustration .20  recency .15
  platformDiversity .10  engagement .10  competitionGap .10  marketSize .10
"""
import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone

WEIGHTS = {
    "frequency": 0.25,
    "frustrationIntensity": 0.20,
    "recency": 0.15,
    "platformDiversity": 0.10,
    "engagement": 0.10,
    "competitionGap": 0.10,
    "marketSizeProxy": 0.10,
}

LARGE_SUBREDDITS = {
    "AskReddit", "programming", "webdev", "SaaS", "startups",
    "smallbusiness", "Entrepreneur",
}


# ---- individual factors (ported 1:1) -------------------------------------

def f_frequency(post_count):
    if post_count == 0:
        return 0.0
    if post_count == 1:
        return 10.0
    return min(100.0, math.log(post_count + 1) * 20)


def f_frustration(intensity):
    return min(100.0, (intensity / 10) * 100)


def _created(post):
    raw = post.get("createdAt")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def f_recency(posts):
    if not posts:
        return 50.0
    dates = [d for d in (_created(p) for p in posts) if d]
    if not dates:
        return 50.0
    most_recent = max(dates)
    days = (datetime.now(timezone.utc) - most_recent).days
    return max(0.0, 100 - (days / 90) * 100)


def f_platform_diversity(posts):
    if not posts:
        return 0.0
    unique = len({p.get("platform") for p in posts})
    return min(100.0, (unique / 5) * 100)


def f_engagement(posts):
    if not posts:
        return 0.0
    total = sum((p.get("score") or 0) + (p.get("numComments") or 0) * 2 for p in posts)
    return min(100.0, math.log(total + 1) * 15)


def f_competition_gap(existing_solutions):
    n = len(existing_solutions or {})
    if n == 0:
        return 90.0
    if n == 1:
        return 70.0
    if n <= 3:
        return 50.0
    return 30.0


def f_market_size(posts):
    if not posts:
        return 50.0
    size = 0
    if any(p.get("subreddit") in LARGE_SUBREDDITS for p in posts):
        size += 30
    avg = sum((p.get("score") or 0) + (p.get("numComments") or 0) for p in posts) / len(posts)
    if avg > 100:
        size += 40
    elif avg > 50:
        size += 25
    elif avg > 10:
        size += 15
    if len(posts) > 10:
        size += 20
    elif len(posts) > 5:
        size += 10
    return min(100.0, size + 10)


# ---- related-post matching (ported from scorer.ts findRelatedPosts) ------

def find_related(opp, all_posts):
    words = [w for w in re.split(r"\s+", opp.get("title", "").lower()) if len(w) > 3]
    quotes = opp.get("quotes", []) or []
    related = []
    for post in all_posts:
        text = f"{post.get('title','')} {post.get('body','')}".lower()
        has_quote = any(
            (q.get("text", "")[:30].lower() in text) for q in quotes if q.get("text")
        )
        if has_quote:
            related.append(post)
            continue
        matches = sum(1 for w in words if w in text)
        if matches >= 2:
            related.append(post)
    return related


def label(score):
    if score >= 80:
        return "High Priority"
    if score >= 60:
        return "Worth Investigating"
    if score >= 40:
        return "Moderate Potential"
    return "Weak Signal"


def score_opportunity(opp, all_posts):
    related = find_related(opp, all_posts)
    factors = {
        "frequency": f_frequency(len(related)),
        "frustrationIntensity": f_frustration(opp.get("frustrationIntensity", 5)),
        "recency": f_recency(related),
        "platformDiversity": f_platform_diversity(related),
        "engagement": f_engagement(related),
        "competitionGap": f_competition_gap(opp.get("existingSolutions", {})),
        "marketSizeProxy": f_market_size(related),
    }
    total = sum(factors[k] * WEIGHTS[k] for k in WEIGHTS)
    out = dict(opp)
    out["scoring"] = {k: round(v, 2) for k, v in factors.items()}
    out["relatedPostCount"] = len(related)
    out["totalScore"] = round(total, 2)
    out["scoreLabel"] = label(total)
    return out


def main():
    ap = argparse.ArgumentParser(description="Score opportunities (7-factor)")
    ap.add_argument("--in", dest="infile", default="", help="input JSON (default stdin)")
    ap.add_argument("--out", default="", help="output file (default stdout)")
    args = ap.parse_args()

    raw = open(args.infile, encoding="utf-8").read() if args.infile else sys.stdin.read()
    data = json.loads(raw)
    posts = data.get("posts", [])
    opps = data.get("opportunities", [])

    scored = sorted(
        (score_opportunity(o, posts) for o in opps),
        key=lambda x: x["totalScore"],
        reverse=True,
    )
    payload = json.dumps(scored, indent=2, ensure_ascii=False)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(payload)
        sys.stderr.write(f"wrote {len(scored)} scored opportunities to {args.out}\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
