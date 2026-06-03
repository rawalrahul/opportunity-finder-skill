#!/usr/bin/env python3
"""
fetch_posts.py - Collect raw posts for opportunity analysis.

Sources (no API key required):
  - HackerNews via Algolia API (stories + comments, no auth)
  - Reddit via public .json endpoints (no auth, low-volume; may 429)

Outputs a unified JSON array of posts to stdout (or --out file).
Each post matches the CollectedPost shape used by score.py:
  externalId, platform, title, body, url, author, subreddit, score,
  numComments, createdAt (ISO8601)

The AI analysis (frustration detection, clustering) is done by the
agent running the skill - this script only does deterministic fetching.
"""
import argparse
import html
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = "OpportunityFinder-Skill/1.0 (research)"
HN_BASE = "https://hn.algolia.com/api/v1"


def clean(value):
    return html.unescape(str(value or ""))


def _get(url, headers=None, retries=3):
    headers = headers or {}
    headers.setdefault("User-Agent", UA)
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 429:
                    time.sleep(1.0 * (2 ** i))
                    continue
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429 and i < retries - 1:
                time.sleep(1.0 * (2 ** i))
                continue
            if e.code == 404:
                return None
            if i < retries - 1:
                time.sleep(1.0 * (2 ** i))
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries - 1:
                time.sleep(1.0 * (2 ** i))
    if last:
        sys.stderr.write(f"fetch failed for {url}: {last}\n")
    return None


def fetch_hn(query, limit, tags):
    params = urllib.parse.urlencode(
        {"query": query, "tags": tags, "hitsPerPage": limit}
    )
    data = _get(f"{HN_BASE}/search?{params}")
    if not data:
        return []
    out = []
    for h in data.get("hits", []):
        out.append(
            {
                "externalId": h.get("objectID"),
                "platform": "HackerNews",
                "title": clean(h.get("title")),
                "body": clean(
                    h.get("story_text")
                    or h.get("comment_text")
                    or f"{h.get('title') or ''} - {h.get('url') or ''}"
                ),
                "url": clean(
                    h.get("url")
                    or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
                ),
                "author": h.get("author"),
                "subreddit": None,
                "score": h.get("points") or 0,
                "numComments": h.get("num_comments") or 0,
                "createdAt": h.get("created_at"),
            }
        )
    return out


def _parse_reddit_children(children):
    out = []
    for c in children:
        d = c.get("data", {})
        sub = d.get("subreddit")
        out.append(
            {
                "externalId": d.get("id"),
                "platform": "Reddit",
                "title": d.get("title") or "",
                "body": d.get("selftext") or d.get("url") or "",
                "url": f"https://reddit.com/r/{sub}/comments/{d.get('id')}",
                "author": d.get("author"),
                "subreddit": sub,
                "score": d.get("score") or 0,
                "numComments": d.get("num_comments") or 0,
                "createdAt": datetime.fromtimestamp(
                    d.get("created_utc", 0), tz=timezone.utc
                ).isoformat(),
            }
        )
    return out


def fetch_reddit(query, subreddits, limit):
    out = []
    if subreddits:
        for sub in subreddits:
            params = urllib.parse.urlencode(
                {
                    "q": query,
                    "sort": "new",
                    "limit": limit,
                    "restrict_sr": "1",
                    "t": "month",
                }
            )
            data = _get(f"https://www.reddit.com/r/{sub}/search.json?{params}")
            if data and "data" in data:
                out.extend(_parse_reddit_children(data["data"].get("children", [])))
            time.sleep(0.5)  # be polite to unauthenticated endpoint
    else:
        params = urllib.parse.urlencode(
            {"q": query, "sort": "new", "limit": limit, "t": "month"}
        )
        data = _get(f"https://www.reddit.com/search.json?{params}")
        if data and "data" in data:
            out.extend(_parse_reddit_children(data["data"].get("children", [])))
    return out


def main():
    ap = argparse.ArgumentParser(description="Fetch raw posts for opportunity analysis")
    ap.add_argument("--query", required=True, help="topic / keyword to search")
    ap.add_argument(
        "--source",
        default="all",
        choices=["all", "hn", "reddit"],
        help="which sources to fetch (default: all)",
    )
    ap.add_argument(
        "--subreddits",
        default="",
        help="comma-separated subreddits (empty = search all of reddit)",
    )
    ap.add_argument("--limit", type=int, default=30, help="posts per source/subreddit")
    ap.add_argument("--out", default="", help="output file (default: stdout)")
    args = ap.parse_args()

    subs = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    posts = []
    if args.source in ("all", "hn"):
        posts += fetch_hn(args.query, args.limit, "story")
        posts += fetch_hn(args.query, args.limit, "comment")
    if args.source in ("all", "reddit"):
        posts += fetch_reddit(args.query, subs, args.limit)

    # dedupe by (platform, externalId)
    seen = set()
    deduped = []
    for p in posts:
        key = (p["platform"], p["externalId"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)

    payload = json.dumps(deduped, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        sys.stderr.write(f"wrote {len(deduped)} posts to {args.out}\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
