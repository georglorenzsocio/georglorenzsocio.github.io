#!/usr/bin/env python3
"""
Fetch citation statistics from Google Scholar for a fixed author profile
and write them to a Jekyll data file (_data/scholar.yml) so the site can
display them via {{ site.data.scholar.* }}.

Run daily by .github/workflows/update-scholar-stats.yml. If the fetch
fails (Google Scholar occasionally blocks automated requests), the
script exits with an error and leaves the existing _data/scholar.yml
untouched, so the site keeps showing the last successfully fetched
numbers instead of breaking.
"""

import sys
from datetime import timezone
import datetime

import yaml
from scholarly import scholarly

SCHOLAR_USER_ID = "C9KEwL4AAAAJ"  # Georg Lorenz's Google Scholar profile
OUTPUT_PATH = "_data/scholar.yml"


def fetch_stats(user_id: str) -> dict:
    author = scholarly.search_author_id(user_id)
    author = scholarly.fill(author, sections=["indices", "counts"])

    return {
        "citations_all": author.get("citedby", 0),
        "citations_recent": author.get("citedby5y", 0),
        "hindex_all": author.get("hindex", 0),
        "hindex_recent": author.get("hindex5y", 0),
        "i10index_all": author.get("i10index", 0),
        "i10index_recent": author.get("i10index5y", 0),
        "profile_url": f"https://scholar.google.com/citations?user={user_id}",
        "last_updated": datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def main() -> int:
    try:
        stats = fetch_stats(SCHOLAR_USER_ID)
    except Exception as exc:  # noqa: BLE001 - we want to catch anything scholarly throws
        print(f"Failed to fetch Google Scholar stats: {exc}", file=sys.stderr)
        return 1

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(stats, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Wrote {OUTPUT_PATH}: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
