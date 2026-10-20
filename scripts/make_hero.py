#!/usr/bin/env python3
"""Render the profile hero (neofetch-style terminal) from live GitHub data.

Two variants are written next to this script's repo:
  assets/hero-dark.svg   — green phosphor on a dark terminal
  assets/hero-light.svg  — paper-white terminal, dark green text

`repos`, `stars` and `followers` come from the GitHub API at run time, so the
workflow can refresh them on a schedule. Everything else is static, verified
profile data.
"""
from __future__ import annotations

import json
import os
import random
import urllib.request
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "Linus-Shyu/Linus-Shyu")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parent.parent / "assets"

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, 'JetBrains Mono', Consolas, monospace"
ANSI = ["#1a1a1a", "#ff5555", "#50fa7b", "#f1fa8c", "#6272a4", "#bd93f9", "#8be9fd", "#f8f8f2"]

# dark ramp ends on the brighter phosphor green; light ramp ends on a deep green
DARK_RAMP = ["#161b22", "#14402a", "#1f7a44", "#2ec65c", "#3fe066"]
LIGHT_RAMP = ["#eef1ea", "#d9ecdd", "#b7e0c6", "#6fc896", "#34b56b"]


def fetch_counts() -> dict[str, str]:
    query = """
    query {
      user(login: "REPO") {
        followers { totalCount }
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          totalCount
          nodes { stargazerCount }
        }
      }
    }
    """.replace("REPO", REPO.split("/")[0])
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "hero-bot",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.load(res)["data"]["user"]
    repos = data["repositories"]["totalCount"]
    stars = sum(n["stargazerCount"] for n in data["repositories"]["nodes"])
    followers = data["followers"]["totalCount"]
    return {"repos": f"{repos}", "stars": f"{stars}", "followers": f"{followers}"}


def build_graph(dark: bool):
    cols, rows = 17, 8
    order = []
    for r in range(rows):
        cs = range(cols) if r % 2 == 0 else range(cols - 1, -1, -1)
        order += [(r, c) for c in cs]

    rng = random.Random(21)
    levels = {
        (r, c): rng.choices([0, 1, 2, 3, 4], weights=[30, 26, 22, 14, 8])[0]
        for r in range(rows)
        for c in range(cols)
    }
    eaten = set(order[:84])
    head = order[83]

    if dark:
        ramp = DARK_RAMP
        body, headc, eye = "#3fe066", "#9affbd", "#06220f"
    else:
        ramp = LIGHT_RAMP
        body, headc, eye = "#0c7a43", "#065f2e", "#ffffff"

    return cols, rows, levels, eaten, head, ramp, body, headc, eye


def render(theme: str, counts: dict[str, str]) -> str:
    dark = theme == "dark"
    pid = f"nf-{theme}"
    cols, rows, levels, eaten, head, ramp, body, headc, eye = build_graph(dark)

    page_a, page_b = ("#0e130f", "#080a08") if dark else ("#f1f4ef", "#fbfcf9")
    win = "#0a0d0b" if dark else "#f7f9f4"
    bar = "#101410" if dark else "#ecefea"
    edge = "#1d221c" if dark else "#d7ded7"
    green = "#3fe066" if dark else "#0a8f4d"
    label = "#40d26c" if dark else "#0f7c48"
    value = "#cdf5d4" if dark else "#23281f"
    dim = "#4e6a57" if dark else "#758a7a"
    amber = "#ffb86c" if dark else "#b45309"
    scan_op = "0.08" if dark else "0.03"
    glow_op = "0.13" if dark else "0.04"

    gx, gy, cell = 52, 134, 15
    cells_svg = []
    for r in range(rows):
        for c in range(cols):
            key = (r, c)
            fill = headc if key == head else (body if key in eaten else ramp[levels[key]])
            cells_svg.append(
                f'<rect x="{gx + c * cell + 1.5}" y="{gy + r * cell + 1.5}" '
                f'width="{cell - 3}" height="{cell - 3}" rx="3" fill="{fill}"/>'
            )
    hr, hc = head  # (row, col)
    ex = gx + hc * cell + (cell - 3) / 2
    ey = gy + hr * cell + (cell - 3) / 2
    cells_svg.append(f'<circle cx="{ex + 3}" cy="{ey - 2}" r="1.7" fill="{eye}"/>')
    cells_svg.append(f'<circle cx="{ex + 3}" cy="{ey + 3}" r="1.7" fill="{eye}"/>')
    cells = "\n  ".join(cells_svg)

    info = [
        ("name", "Linus Shyu", "v"),
        ("company", "Young Agent Lab", "v"),
        ("location", "Kowloon City District, Hong Kong", "v"),
        ("website", "linusshyu.dev", "a"),
        ("repos", counts.get("repos", "—"), "v"),
        ("stars", counts.get("stars", "—"), "v"),
        ("followers", counts.get("followers", "—"), "v"),
        ("langs", "Swift · Rust · TypeScript · Python · Solidity", "v"),
        ("contact", "@Linus_Shyu", "v"),
    ]
    rows_svg = []
    y = 160
    for key, val, kind in info:
        col = amber if kind == "a" else value
        rows_svg.append(
            f'<text x="316" y="{y}" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{label}">{key:<10}</text>'
            f'<text x="412" y="{y}" font-family="{MONO}" font-size="13.5" fill="{col}">{val}</text>'
        )
        y += 20
    info_svg = "\n  ".join(rows_svg)

    palette = "\n  ".join(
        f'<rect x="{316 + i * 17}" y="332" width="15" height="9" rx="2" fill="{ANSI[i]}"/>'
        for i in range(8)
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 380" width="1000" height="380" role="img" aria-label="Linus Shyu terminal">
  <defs>
    <linearGradient id="{pid}-page" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{page_a}"/><stop offset="100%" stop-color="{page_b}"/>
    </linearGradient>
    <radialGradient id="{pid}-glow" cx="16%" cy="6%" r="80%">
      <stop offset="0%" stop-color="#3fe066" stop-opacity="{glow_op}"/>
      <stop offset="100%" stop-color="#3fe066" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="{pid}-vignette" cx="50%" cy="50%" r="72%">
      <stop offset="0%" stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="{'0.4' if dark else '0.07'}"/>
    </radialGradient>
    <pattern id="{pid}-scan" width="3" height="3" patternUnits="userSpaceOnUse">
      <rect width="3" height="1" fill="#000" opacity="{scan_op}"/>
    </pattern>
    <filter id="{pid}-shadow" x="-10%" y="-10%" width="120%" height="132%">
      <feDropShadow dx="0" dy="10" stdDeviation="20" flood-color="#000" flood-opacity="{'0.55' if dark else '0.16'}"/>
    </filter>
    <filter id="{pid}-bloom"><feGaussianBlur stdDeviation="3.5"/></filter>
    <style>
      .cur{{animation:{pid}-blink 1.1s steps(1) infinite}}
      @keyframes {pid}-blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
    </style>
  </defs>

  <rect width="1000" height="380" rx="22" fill="url(#{pid}-page)"/>

  <rect x="24" y="24" width="952" height="332" rx="16" fill="{win}" stroke="{edge}" filter="url(#{pid}-shadow)"/>
  <path d="M24 40 a16 16 0 0 1 16 -16 h920 a16 16 0 0 1 16 16 v20 h-952 Z" fill="{bar}"/>
  <circle cx="47" cy="47" r="5.5" fill="#ff5f57"/><circle cx="66" cy="47" r="5.5" fill="#febc2e"/><circle cx="85" cy="47" r="5.5" fill="#28c840"/>
  <text x="108" y="52" font-family="{MONO}" font-size="12" fill="{dim}">Linus@github — zsh — 90×26</text>
  <text x="940" y="52" font-family="{MONO}" font-size="12" fill="{dim}" text-anchor="end">100% ▮▮▯</text>

  <rect x="24" y="60" width="952" height="296" fill="url(#{pid}-glow)"/>

  {cells}
  <text x="52" y="272" font-family="{MONO}" font-size="11.5" fill="{dim}">$ tail -f contributions.log</text>

  <text x="316" y="114" font-family="{MONO}" font-size="22" font-weight="700" fill="{green}" filter="url(#{pid}-bloom)" opacity="0.5">Linus@Linus</text>
  <text x="316" y="114" font-family="{MONO}" font-size="22" font-weight="700" fill="{green}">Linus@Linus</text>
  <text x="316" y="130" font-family="{MONO}" font-size="12" fill="{dim}">───────────── ───────────── ────────</text>

  {info_svg}

  {palette}

  <text x="52" y="352" font-family="{MONO}" font-size="14" fill="{green}">➜</text>
  <text x="72" y="352" font-family="{MONO}" font-size="14" fill="{value}">~</text>
  <text x="92" y="352" font-family="{MONO}" font-size="14" fill="{dim}">git:(master) $</text>
  <rect class="cur" x="210" y="340" width="9" height="15" fill="{green}"/>

  <rect x="24" y="24" width="952" height="332" rx="16" fill="url(#{pid}-scan)"/>
  <rect width="1000" height="380" rx="22" fill="url(#{pid}-vignette)"/>
</svg>
'''


def main() -> int:
    counts = fetch_counts() if TOKEN else {"repos": "—", "stars": "—", "followers": "—"}
    print("counts:", counts)
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        (OUT / f"hero-{theme}.svg").write_text(render(theme, counts), encoding="utf-8")
        print(f"wrote assets/hero-{theme}.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
