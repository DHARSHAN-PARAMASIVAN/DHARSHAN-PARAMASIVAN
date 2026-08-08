#!/usr/bin/env python3
"""Sync live profile README sections from the GitHub API."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
USER = os.environ.get("GITHUB_ACTOR", "DHARSHAN-PARAMASIVAN")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

SKIP = {
    USER.lower(),
    "portfolio",
    "sample",
}


def api_get(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "signal-sheet-sync",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def replace_block(text: str, name: str, body: str) -> str:
    start = f"<!--LIVE:{name}:START-->"
    end = f"<!--LIVE:{name}:END-->"
    pattern = re.compile(
        re.escape(start) + r"[\s\S]*?" + re.escape(end),
        re.MULTILINE,
    )
    replacement = f"{start}\n{body.rstrip()}\n{end}"
    if not pattern.search(text):
        raise SystemExit(f"Missing markers for {name}")
    return pattern.sub(replacement, text)


def repo_row(repo: dict) -> str:
    name = repo["name"]
    desc = (repo.get("description") or "No description yet.").strip()
    if len(desc) > 90:
        desc = desc[:87] + "..."
    lang = repo.get("language") or "—"
    stars = repo.get("stargazers_count", 0)
    url = repo["html_url"]
    return f"| [{name}]({url}) | {desc} | `{lang}` | {stars} |"


def main() -> None:
    user = api_get(f"https://api.github.com/users/{USER}")
    repos = api_get(
        f"https://api.github.com/users/{USER}/repos?per_page=100&sort=updated&type=owner"
    )

    public = [
        r
        for r in repos
        if not r.get("fork")
        and not r.get("private")
        and r["name"].lower() not in SKIP
    ][:8]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pulse = f"""```bash
$ uptime --profile
user:           {USER}
public_repos:   {user.get('public_repos', len(repos))}
followers:      {user.get('followers', 0)}
following:      {user.get('following', 0)}
last_sync:      {now}
status:         ONLINE | auto-synced by GitHub Actions
```"""

    table_lines = [
        "| Repo | Latest signal | Lang | Stars |",
        "| --- | --- | --- | ---: |",
    ]
    table_lines.extend(repo_row(r) for r in public)
    if len(public) == 0:
        table_lines.append("| — | No public repos yet | — | 0 |")
    live_repos = "\n".join(table_lines)

    text = README.read_text(encoding="utf-8")
    text = replace_block(text, "PULSE", pulse)
    text = replace_block(text, "REPOS", live_repos)
    README.write_text(text, encoding="utf-8")
    print(f"Synced {len(public)} repos at {now}")


if __name__ == "__main__":
    main()
