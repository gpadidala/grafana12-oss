#!/usr/bin/env python3
"""Print every provisioned dashboard as a clickable URL, grouped by tag.

Usage:  GRAFANA_URL=http://localhost:3012 python3 validation/print_dashboards.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request


def fetch(path: str) -> list[dict]:
    url = os.environ.get("GRAFANA_URL", "http://localhost:3012").rstrip("/") + path
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


def main() -> int:
    base = os.environ.get("GRAFANA_URL", "http://localhost:3012").rstrip("/")

    groups = [
        ("Validation suite",  "/api/search?type=dash-db&tag=validation&limit=200"),
        ("v12 feature demos", "/api/search?type=dash-db&tag=feature-demo&limit=200"),
        ("Platform",          "/api/search?type=dash-db&tag=platform&limit=200"),
    ]
    for title, path in groups:
        rows = fetch(path)
        print(f"== {title} ({len(rows)}) ==")
        for d in rows:
            print(f"  {base}{d['url']}")
        print()

    print("== Folders (click in UI) ==")
    for f in fetch("/api/search?type=dash-folder"):
        print(f"  {f['title']:<20} {base}/dashboards/f/{f['uid']}")

    print()
    print(f"Home redirects to: {base}/d/v12-upgrade-overview/v12-upgrade-overview")
    return 0


if __name__ == "__main__":
    sys.exit(main())
