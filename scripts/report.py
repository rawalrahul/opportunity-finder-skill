#!/usr/bin/env python3
"""
report.py - Render ranked opportunity results as a polished report.

Input: ranked JSON emitted by score.py.
Output: Markdown by default, plus optional HTML and PDF.

PDF export uses Playwright when installed:
  python -m playwright install chromium
"""
import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def clean(value):
    text = str(value or "")
    replacements = {
        "â€™": "'",
        "â€œ": '"',
        "â€": '"',
        "â€“": "-",
        "â€”": "-",
        "â€¦": "...",
        "Â": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def slug(text):
    out = re.sub(r"[^a-z0-9]+", "-", clean(text).lower()).strip("-")
    return out or "opportunity"


def md_escape(text):
    return clean(text).replace("|", "\\|")


def label(score):
    if score >= 80:
        return "High Priority"
    if score >= 60:
        return "Worth Investigating"
    if score >= 40:
        return "Moderate Potential"
    return "Weak Signal"


def top_recommendation(opps):
    if not opps:
        return "No ranked opportunities were provided."
    first = opps[0]
    title = clean(first.get("title"))
    approach = clean(first.get("suggestedApproach", "product"))
    return (
        f"The strongest opportunity is **{title}**. It has the best combined "
        f"score in the evidence set and should be validated first as a {approach}."
    )


def render_markdown(opps, topic, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    topic_title = clean(topic).strip()
    lines = [
        f"# {topic_title} Opportunity Report",
        "",
        f"Generated: {generated_at}",
        "",
        "## Executive Summary",
        "",
        top_recommendation(opps),
        "",
        "## Ranked Opportunities",
        "",
        "| Rank | Opportunity | Score | Label | Suggested Approach |",
        "|---:|---|---:|---|---|",
    ]

    for index, opp in enumerate(opps, start=1):
        score = float(opp.get("totalScore", 0))
        lines.append(
            "| {rank} | {title} | {score:.2f} | {label} | {approach} |".format(
                rank=index,
                title=md_escape(opp.get("title")),
                score=score,
                label=md_escape(opp.get("scoreLabel") or label(score)),
                approach=md_escape(opp.get("suggestedApproach", "")),
            )
        )

    lines += ["", "## Opportunity Details", ""]

    for index, opp in enumerate(opps, start=1):
        score = float(opp.get("totalScore", 0))
        lines += [
            f"### {index}. {clean(opp.get('title'))}",
            "",
            f"Score: {score:.2f} ({clean(opp.get('scoreLabel') or label(score))})",
            "",
            clean(opp.get("description")),
            "",
            f"Suggested approach: {clean(opp.get('suggestedApproach', ''))}",
            "",
        ]

        scoring = opp.get("scoring") or {}
        if scoring:
            parts = [f"{clean(k)} {float(v):.2f}" for k, v in scoring.items()]
            lines += ["Score factors: " + ", ".join(parts), ""]

        quotes = opp.get("quotes") or []
        if quotes:
            lines += ["Evidence:", ""]
            for quote in quotes[:4]:
                text = clean(quote.get("text"))
                source = clean(quote.get("source") or quote.get("platform"))
                url = clean(quote.get("url"))
                if url:
                    lines.append(f"- \"{text}\"  ")
                    lines.append(f"  Source: [{source}]({url})")
                else:
                    lines.append(f"- \"{text}\" ({source})")
            lines.append("")

        solutions = opp.get("existingSolutions") or {}
        if solutions:
            lines += ["Existing solutions and weaknesses:", ""]
            for name, weakness in solutions.items():
                lines.append(f"- {clean(name)}: {clean(weakness)}")
            lines.append("")

    lines += [
        "## Recommendation",
        "",
        "Validate the highest-scoring opportunity with 10-20 target users before building broadly. "
        "Use the quoted evidence as interview prompts, then narrow the first version to one urgent workflow, one buyer, and one integration surface.",
        "",
    ]
    return "\n".join(lines)


def render_html(markdown_text, title):
    body = []
    in_ul = False
    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if line.startswith("- "):
            if not in_ul:
                body.append("<ul>")
                in_ul = True
            body.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if in_ul:
            body.append("</ul>")
            in_ul = False

        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            body.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("|"):
            body.append(f"<pre>{html.escape(line)}</pre>")
        elif not line:
            body.append("")
        else:
            body.append(f"<p>{html.escape(line)}</p>")
    if in_ul:
        body.append("</ul>")

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; max-width: 920px; margin: 48px auto; color: #172033; line-height: 1.55; }}
    h1 {{ font-size: 34px; margin-bottom: 8px; }}
    h2 {{ margin-top: 34px; border-top: 1px solid #d8dde8; padding-top: 20px; }}
    h3 {{ margin-top: 28px; }}
    pre {{ white-space: pre-wrap; background: #f6f8fb; border: 1px solid #e5e9f0; padding: 8px 10px; border-radius: 6px; }}
    a {{ color: #1455d9; }}
  </style>
</head>
<body>
{chr(10).join(body)}
</body>
</html>
"""


def write_pdf(html_path, pdf_path):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("PDF export requires Playwright. Install it or omit --pdf.") from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(Path(html_path).resolve().as_uri(), wait_until="load")
        page.pdf(path=str(pdf_path), format="A4", print_background=True, margin={
            "top": "18mm",
            "bottom": "18mm",
            "left": "16mm",
            "right": "16mm",
        })
        browser.close()


def main():
    ap = argparse.ArgumentParser(description="Render opportunity report")
    ap.add_argument("--in", dest="infile", required=True, help="ranked JSON from score.py")
    ap.add_argument("--topic", required=True, help="report topic/title prefix")
    ap.add_argument("--out", required=True, help="Markdown output path")
    ap.add_argument("--html", default="", help="optional HTML output path")
    ap.add_argument("--pdf", default="", help="optional PDF output path")
    args = ap.parse_args()

    opps = load_json(args.infile)
    md = render_markdown(opps, args.topic)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")

    html_path = args.html
    if args.html or args.pdf:
        html_path = html_path or str(out.with_suffix(".html"))
        html_text = render_html(md, f"{args.topic} Opportunity Report")
        Path(html_path).write_text(html_text, encoding="utf-8")

    if args.pdf:
        write_pdf(html_path, Path(args.pdf))


if __name__ == "__main__":
    main()
