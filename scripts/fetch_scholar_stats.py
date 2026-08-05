#!/usr/bin/env python3
"""
Fetch citation statistics from Google Scholar (via SerpApi's Google Scholar
Author API) for a fixed author profile, write them to a Jekyll data file
(_data/scholar.yml), and render a small citations-per-year chart
(assets/scholar_citations.png) for the "About me" page, similar in spirit
to https://czymara.com.

Run daily by .github/workflows/update-scholar-stats.yml. Requires a
SERPAPI_KEY secret (see https://serpapi.com/ - free tier covers ~100
searches/month, plenty for one fetch a day). We switched to SerpApi
because Google Scholar reliably blocks scraping requests coming from
GitHub Actions' shared runner IPs (the previous `scholarly`-based
approach started failing every single day).

If the fetch fails, the script exits with an error and leaves the
existing data/chart untouched, so the site keeps showing the last
successfully fetched numbers instead of breaking.
"""

import os
import sys
import datetime
from datetime import timezone

import yaml
import requests
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCHOLAR_USER_ID = "C9KEwL4AAAAJ"  # Georg Lorenz's Google Scholar profile
DATA_PATH = "_data/scholar.yml"
CHART_PATH = "assets/scholar_citations.png"
SERPAPI_URL = "https://serpapi.com/search.json"


def fetch_author(user_id: str, api_key: str) -> dict:
    params = {
        "engine": "google_scholar_author",
        "author_id": user_id,
        "hl": "en",
        "api_key": api_key,
    }
    resp = requests.get(SERPAPI_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    status = data.get("search_metadata", {}).get("status")
    if status != "Success":
        raise RuntimeError(f"SerpApi search did not succeed (status={status!r}): {data.get('error')}")
    return data


def _metric(table_entry: dict) -> tuple:
    """Given one cited_by.table entry, e.g. {'citations': {'all': X, 'since_2016': Y}},
    return (all_value, recent_value) regardless of the exact 'since_XXXX' key name."""
    (metric_values,) = table_entry.values()
    all_value = metric_values.get("all", 0)
    recent_key = next((k for k in metric_values if k != "all"), None)
    recent_value = metric_values.get(recent_key, 0) if recent_key else 0
    return all_value, recent_value


def build_stats(data: dict, user_id: str) -> dict:
    table = data.get("cited_by", {}).get("table", [])
    citations_all = citations_recent = 0
    hindex_all = hindex_recent = 0
    i10index_all = i10index_recent = 0

    for entry in table:
        if "citations" in entry:
            citations_all, citations_recent = _metric(entry)
        elif "h_index" in entry:
            hindex_all, hindex_recent = _metric(entry)
        elif "i10_index" in entry:
            i10index_all, i10index_recent = _metric(entry)

    current_year = datetime.datetime.now(timezone.utc).year
    return {
        "citations_all": citations_all,
        "citations_recent": citations_recent,
        "hindex_all": hindex_all,
        "hindex_recent": hindex_recent,
        "i10index_all": i10index_all,
        "i10index_recent": i10index_recent,
        "since_year": current_year - 5,
        "profile_url": f"https://scholar.google.com/citations?user={user_id}",
        "last_updated": datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def render_chart(data: dict, path: str) -> None:
    graph = data.get("cited_by", {}).get("graph", []) or []
    if not graph:
        return

    years = [g["year"] for g in graph]
    counts = [g.get("citations", 0) for g in graph]

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
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print(
            "Failed to fetch Google Scholar stats: SERPAPI_KEY environment variable is not set "
            "(add it as a repository secret; see https://serpapi.com/manage-api-key).",
            file=sys.stderr,
        )
        return 1

    try:
        data = fetch_author(SCHOLAR_USER_ID, api_key)
        stats = build_stats(data, SCHOLAR_USER_ID)
    except Exception as exc:  # noqa: BLE001 - we want to catch anything the request/parsing throws
        print(f"Failed to fetch Google Scholar stats: {exc}", file=sys.stderr)
        return 1

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        yaml.dump(stats, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    try:
        render_chart(data, CHART_PATH)
    except Exception as exc:  # noqa: BLE001 - chart is a nice-to-have, don't fail the run over it
        print(f"Warning: could not render citation chart: {exc}", file=sys.stderr)

    print(f"Wrote {DATA_PATH}: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
