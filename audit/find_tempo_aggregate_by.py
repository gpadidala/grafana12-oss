#!/usr/bin/env python3
"""Item 10 — find panels that query Tempo metrics-summary / `Aggregate by` (removed in 12.0)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import log  # noqa: E402


TRIGGERS = ("metrics/summary", "groupBy", "aggregateBy", "metricsSummary")


def walk_panels(panels: list[dict]) -> list[dict]:
    hits: list[dict] = []
    for p in panels or []:
        t = (p.get("datasource", {}) or {}).get("type", "")
        body = json.dumps(p)
        if t == "tempo" and any(trig in body for trig in TRIGGERS):
            hits.append({"id": p.get("id"), "title": p.get("title"), "type": p.get("type")})
        if p.get("panels"):
            hits.extend(walk_panels(p["panels"]))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboards", required=True, help="dir of dashboard JSON files")
    args = ap.parse_args()

    rows: list[dict] = []
    for path in sorted(Path(args.dashboards).rglob("*.json")):
        payload = json.loads(path.read_text())
        dash = payload.get("dashboard", payload)
        hits = walk_panels(dash.get("panels", []) or [])
        if hits:
            rows.append({"uid": dash.get("uid"), "title": dash.get("title"), "panels": hits})

    print(json.dumps(rows, indent=2))
    log("info", "find_tempo_aggregate_by", "done", dashboards=len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
