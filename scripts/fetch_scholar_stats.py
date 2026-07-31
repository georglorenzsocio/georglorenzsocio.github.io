#!/usr/bin/env python3
"""
Fetch citation statistics from Google Scholar for a fixed author profile,
write them to a Jekyll data file (_data/scholar.yml), and render a small
citations-per-year chart (assets/scholar_citations.png) for the "About me"
page, similar in spirit to https://czymara.com.

Run daily by .github/workflows/update-scholar-stats.yml. If the fetch
fails (Google Scholar occasionally blocks automated requests), the
script exits with an error and leaves the existing data/chart untouched,
so the site keeps showing the last successfully fetched numbers instead
of breaking.
"""

import os
import sys
import datetime
from datetime import timezone

import yaml
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scholarly import scholarly

SCHOLAR_USER_ID = "C9KEwL4AAAAJ"  # Georg Lorenz's Google Scholar profile
DATA_PATH = "_data/scholar.yml"
CHART_PATH = "assets/scholar_citations.png"


def fetch_author(user_id: str) -> dict:
    author = scholarly.search_author_id(user_id)
    return scholarly.fill(author, sections=["indices", "counts"])


def build_stats(author: dict, user_id: str) -> dict:
    current_year = datetime.datetime.now(timezone.utc).year
    return {
        "citations_all": author.get("citedby", 0),
        "citations_recent": author.get("citedby5y", 0),
        "hindex_all": author.get("hindex", 0),
        "hindex_recent": author.get("hindex5y", 0),
        "i10index_all": author.get("i10index", 0),
        "i10index_recent": author.get("i10index5y", 0),
        "since_year": current_year - 5,
        "profile_url": f"https://scholar.google.com/citations?user={user_id}",
        "last_updated": datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def render_chart(author: dict, path: str) -> None:
    cites_per_year = author.get("cites_per_year", {}) or {}
    if not cites_per_year:
        return

    years = sorted(cites_per_year.keys())
    counts = [cites_per_year[y] for y in years]

    os.makedirs(os.path.dirname(path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(4.6, 1.8), dpi=200)
    ax.bar(years, counts, color="#4a4a4a", width=0.6)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.set_yticks([])
    ax.set_title("Citations per year", fontsize=8, loc="left", color="#4a4a4a")
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    fig.tight_layout(pad=0.4)
    fig.savefig(path, transparent=True)
    plt.close(fig)


def main() -> int:
    try:
        author = fetch_author(SCHOLAR_USER_ID)
        stats = build_stats(author, SCHOLAR_USER_ID)
    except Exception as exc:  # noqa: BLE001 - we want to catch anything scholarly throws
        print(f"Failed to fetch Google Scholar stats: {exc}", file=sys.stderr)
        return 1

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        yaml.dump(stats, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    try:
        render_chart(author, CHART_PATH)
    except Exception as exc:  # noqa: BLE001 - chart is a nice-to-have, don't fail the run over it
        print(f"Warning: could not render citation chart: {exc}", file=sys.stderr)

    print(f"Wrote {DATA_PATH}: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
