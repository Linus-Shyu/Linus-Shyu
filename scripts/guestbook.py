#!/usr/bin/env python3
"""Rebuild the guestbook block in README.md from issues labelled `guestbook`.

Every entry is sanitised: newlines collapse, pipes are replaced (they would break
the markdown table), angle brackets are stripped, and both the handle and the note
are wrapped in code spans so a visitor cannot inject links or formatting.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "Linus-Shyu/Linus-Shyu")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = "README.md"
START = "<!-- GUESTBOOK:START -->"
END = "<!-- GUESTBOOK:END -->"
MAX_ROWS = 30
MAX_NOTE = 110


def api(path: str):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "guestbook-bot",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def clean(text: str | None) -> str:
    text = (text or "").strip()
    # drop the issue-form boilerplate some visitors leave behind
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"[\r\n]+", " ", text)
    text = text.replace("|", "⁄").replace("`", "'")
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_NOTE:
        text = text[: MAX_NOTE - 1].rstrip() + "…"
    return text or "—"


def build_block() -> str:
    issues = api(f"/repos/{REPO}/issues?labels=guestbook&state=all&per_page=100")
    entries = []
    for item in issues:
        if "pull_request" in item:
            continue
        login = item["user"]["login"]
        if login.endswith("[bot]"):
            continue
        entries.append(
            (
                item["created_at"][:10],
                login,
                clean(item.get("body")),
                item["number"],
            )
        )

    entries.sort(key=lambda e: (e[0], e[3]), reverse=True)
    entries = entries[:MAX_ROWS]

    if not entries:
        return (
            f"{START}\n"
            "_Nobody has signed in yet — you could be the first._\n"
            f"{END}"
        )

    rows = "\n".join(
        f"| `{date}` | [`@{login}`](https://github.com/{login}) | `{note}` |"
        for date, login, note, _ in entries
    )
    return (
        f"{START}\n"
        "| `logged` | visitor | note |\n"
        "|:--|:--|:--|\n"
        f"{rows}\n"
        f"{END}"
    )


def main() -> int:
    block = build_block()
    with open(README, encoding="utf-8") as fh:
        text = fh.read()

    if START not in text or END not in text:
        print(f"markers missing in {README}", file=sys.stderr)
        return 2

    updated = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        lambda _: block,
        text,
        flags=re.S,
    )
    if updated != text:
        with open(README, "w", encoding="utf-8") as fh:
            fh.write(updated)
        print("guestbook updated")
    else:
        print("guestbook unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
