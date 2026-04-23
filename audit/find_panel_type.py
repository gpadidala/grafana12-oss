#!/usr/bin/env python3
"""Items 18 + 20 — find every panel of a given type across dashboards/."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import log  # noqa: E402


def walk(panels: list[dict], want: str) -> list[dict]:
    hits: list[dict] = []
    for p in panels or []:
        if p.get("type") == want:
            hits.append({"id": p.get("id"), "title": p.get("title")})
        if p.get("panels"):
            hits.extend(walk(p["panels"], want))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True, help="panel type e.g. datagrid|gauge|table|timeseries")
    ap.add_argument("--dashboards", required=True, help="dir of dashboard JSON files")
    args = ap.parse_args()

    rows: list[dict] = []
    for path in sorted(Path(args.dashboards).rglob("*.json")):
        payload = json.loads(path.read_text())
        dash = payload.get("dashboard", payload)
        hits = walk(dash.get("panels", []) or [], args.type)
        if hits:
            rows.append({"uid": dash.get("uid"), "title": dash.get("title"), "panels": hits})

    print(json.dumps(rows, indent=2))
    log("info", "find_panel_type", "done", panel_type=args.type, dashboards=len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
