#!/usr/bin/env python3
"""Schema v1 → v2 readiness report.

Reads dashboards/snapshot-pre/*.json and classifies each as:
  - already-v2 (schemaVersion >= 40 + dashboardScene compatible)
  - needs-upgrade (schemaVersion 36-39)
  - legacy-blocking (schemaVersion < 36 — must upgrade before cutover)
  - angular-bearing (any panel type in the Angular list)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from _lib import log, write_json


ANGULAR_PANEL_TYPES = {
    "graph",           # legacy Graph panel (pre-TimeSeries)
    "singlestat",
    "table-old",
    "grafana-piechart-panel",
    "grafana-worldmap-panel",
}


def classify(dash: dict) -> tuple[str, bool]:
    sv = int(dash.get("schemaVersion", 0))
    panels = dash.get("panels", []) or []
    has_angular = any(p.get("type") in ANGULAR_PANEL_TYPES for p in panels)
    if has_angular:
        return "angular-bearing", True
    if sv >= 40:
        return "already-v2", False
    if sv >= 36:
        return "needs-upgrade", False
    return "legacy-blocking", False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    snap = out / "dashboards" / "snapshot-pre"
    if not snap.exists():
        log("warn", "schema_diff", "no_snapshot", path=str(snap))
        write_json(out / "schema_diff.summary.json", {"error": "no snapshot dir"})
        return 0

    buckets: Counter = Counter()
    angular_list = []
    for path in sorted(snap.glob("*.json")):
        payload = json.loads(path.read_text())
        dash = payload.get("dashboard", {})
        bucket, angular = classify(dash)
        buckets[bucket] += 1
        if angular:
            angular_list.append({"uid": dash.get("uid"), "title": dash.get("title")})

    summary = {
        "buckets": dict(buckets),
        "angular_dashboards": angular_list,
        "angular_count": len(angular_list),
    }
    write_json(out / "schema_diff.summary.json", summary)
    log("info", "schema_diff", "done", **{k: v for k, v in summary.items() if k != "angular_dashboards"})
    return 1 if (buckets["legacy-blocking"] or angular_list) else 0


if __name__ == "__main__":
    sys.exit(main())
