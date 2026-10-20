#!/usr/bin/env python3
"""Render the two extra charts from live GitHub data (self-hosted, no third party):

  assets/activity.svg   — line/area chart of daily contributions, last ~12 months
  assets/trophies.svg   — a wall of stat badges (stars, repos, followers, commits, …)

`charts.yml` runs this on a schedule and commits the SVGs when the numbers move.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "Linus-Shyu/Linus-Shyu")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parent.parent / "assets"

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"
EMOJI = "'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif"
MONTHS = {f"{m:02d}": s for m, s in zip(range(1, 13), "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}

GREEN = "#3fe066"
HEAD = "#9affbd"
VALUE = "#cdf5d4"
DIM = "#4e6a57"
CARD = "#0f1511"
EDGE = "#1d221c"


def graphql(query: str):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "charts-bot",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def fetch() -> dict:
    q = """
    query {
      user(login: "LOGIN") {
        followers { totalCount }
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          totalCount
          nodes { stargazerCount }
        }
        contributionsCollection {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          totalRepositoryContributions
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """.replace("LOGIN", REPO.split("/")[0])
    u = graphql(q)["data"]["user"]
    cc = u["contributionsCollection"]
    days = [
        (d["date"], d["contributionCount"])
        for w in cc["contributionCalendar"]["weeks"]
        for d in w["contributionDays"]
    ]
    days.sort()
    return {
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "repos_contributed": cc["totalRepositoryContributions"],
        "total": cc["contributionCalendar"]["totalContributions"],
        "days": days,
    }


def fmt(n: int) -> str:
    return f"{n:,}"


def activity_svg(data: dict) -> str:
    days = data["days"]
    n = len(days)
    x0, x1, y0, y1 = 56, 944, 62, 234
    w, h = x1 - x0, y1 - y0
    counts = [c for _, c in days]
    mx = max(counts) or 1

    pts = []
    for i, (_, c) in enumerate(days):
        x = x0 + (i / (n - 1)) * w
        y = y1 - (c / mx) * h
        pts.append((x, y))

    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"M{x0:.1f},{y1:.1f} L{line.replace(' ', ' L')} L{x1:.1f},{y1:.1f} Z"

    grid = "\n  ".join(
        f'<line x1="{x0}" y1="{y0 + k * h / 4:.1f}" x2="{x1}" y2="{y0 + k * h / 4:.1f}" stroke="{EDGE}"/>'
        for k in range(5)
    )

    # month tick labels at each month boundary
    ticks = []
    prev = None
    for i, (date, _) in enumerate(days):
        m = date[5:7]
        if m != prev:
            x = x0 + (i / (n - 1)) * w
            ticks.append(f'<text x="{x:.1f}" y="262" font-family="{MONO}" font-size="11" fill="{DIM}" text-anchor="middle">{MONTHS[m]}</text>')
            prev = m
    ticks_svg = "\n  ".join(ticks)

    lx, ly = pts[-1]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 300" width="1000" height="300" role="img" aria-label="Contribution activity, last 12 months">
  <defs>
    <linearGradient id="act-fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#3fe066" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#3fe066" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <rect x="24" y="24" width="952" height="252" rx="16" fill="{CARD}" stroke="{EDGE}"/>

  <text x="56" y="48" font-family="{MONO}" font-size="14" font-weight="700" fill="{GREEN}">contribution activity</text>
  <text x="944" y="48" font-family="{MONO}" font-size="12" fill="{DIM}" text-anchor="end">{fmt(data['total'])} in the last 12 months</text>

  {grid}
  <path d="{area}" fill="url(#act-fill)"/>
  <polyline points="{line}" fill="none" stroke="{GREEN}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{lx:.1f}" cy="{ly:.1f}" r="4" fill="{HEAD}"/>

  <text x="48" y="{y0 + 4:.0f}" font-family="{MONO}" font-size="11" fill="{DIM}" text-anchor="end">{mx}</text>
  <text x="48" y="{y1:.0f}" font-family="{MONO}" font-size="11" fill="{DIM}" text-anchor="end">0</text>

  {ticks_svg}
</svg>
'''


def trophies_svg(data: dict) -> str:
    badges = [
        ("⭐", "Stars", data["stars"]),
        ("📦", "Repositories", data["repos"]),
        ("👥", "Followers", data["followers"]),
        ("✅", "Commits", data["commits"]),
        ("🔀", "Pull Requests", data["prs"]),
        ("💬", "Issues", data["issues"]),
        ("🧠", "Reviews", data["reviews"]),
        ("🤝", "Repos Contributed", data["repos_contributed"]),
    ]
    cards = []
    cw, ch, gx, gy = 210, 76, 12, 12
    for idx, (emoji, label, value) in enumerate(badges):
        col, row = idx % 4, idx // 4
        x = 56 + col * (cw + gx)
        y = 64 + row * (ch + gy)
        cards.append(
            f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="12" fill="{CARD}" stroke="{EDGE}"/>\n'
            f'  <text x="{x + 18}" y="{y + 36}" font-size="22" font-family="{EMOJI}">{emoji}</text>\n'
            f'  <text x="{x + 56}" y="{y + 36}" font-family="{MONO}" font-size="20" font-weight="700" fill="{GREEN}">{fmt(value)}</text>\n'
            f'  <text x="{x + 18}" y="{y + 64}" font-family="{MONO}" font-size="11" fill="{DIM}">{label}</text>'
        )
    cards_svg = "\n  ".join(cards)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 260" width="1000" height="260" role="img" aria-label="Trophy wall">
  <rect x="24" y="24" width="952" height="212" rx="16" fill="{CARD}" stroke="{EDGE}"/>

  <text x="56" y="48" font-family="{MONO}" font-size="14" font-weight="700" fill="{GREEN}">trophies</text>

  {cards_svg}
</svg>
'''


def main() -> int:
    data = fetch() if TOKEN else {
        "stars": 0, "repos": 0, "followers": 0, "commits": 0, "prs": 0,
        "issues": 0, "reviews": 0, "repos_contributed": 0, "total": 0, "days": [],
    }
    print("data:", {k: v for k, v in data.items() if k != "days"})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "activity.svg").write_text(activity_svg(data), encoding="utf-8")
    (OUT / "trophies.svg").write_text(trophies_svg(data), encoding="utf-8")
    print("wrote assets/activity.svg + assets/trophies.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
