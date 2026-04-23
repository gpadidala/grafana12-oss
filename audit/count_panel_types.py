#!/usr/bin/env python3
"""Item 14 — tally panel types across dashboards/, optionally filtered to one type."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import log  # noqa: E402


def walk(panels: list[dict]) -> list[str]:
    out: list[str] = []
    for p in panels or []:
        if p.get("type"):
            out.append(p["type"])
        if p.get("panels"):
            out.extend(walk(p["panels"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboards", required=True)
    ap.add_argument("--filter", default=None, help="only emit dashboards containing this panel type")
    args = ap.parse_args()

    counts: Counter = Counter()
    matched: list[dict] = []
    for path in sorted(Path(args.dashboards).rglob("*.json")):
        payload = json.loads(path.read_text())
        dash = payload.get("dashboard", payload)
        types = walk(dash.get("panels", []) or [])
        counts.update(types)
        if args.filter and args.filter in types:
            matched.append({"uid": dash.get("uid"), "title": dash.get("title"),
                            "matching_panels": sum(1 for t in types if t == args.filter)})

    result = {"counts": dict(sorted(counts.items(), key=lambda x: -x[1])),
              "filter": args.filter, "matched_dashboards": matched}
    print(json.dumps(result, indent=2))
    log("info", "count_panel_types", "done", total_types=len(counts), matched=len(matched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
