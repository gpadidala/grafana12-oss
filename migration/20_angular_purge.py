#!/usr/bin/env python3
"""Angular panel purge / replace.

For each dashboard in out/<run-id>/dashboards/snapshot-pre/ that contains Angular panels,
rewrite the JSON using React equivalents where a deterministic mapping exists, and
write the result to migration/angular-rewrites/<uid>.json. Dashboards without a clean
mapping are listed in migration/angular-manual-review.md.

Mapping (deterministic subset — extend per project needs):
  - graph → timeseries
  - singlestat → stat
  - table-old → table
  - grafana-piechart-panel → piechart (core, non-Angular)
  - grafana-worldmap-panel → geomap
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402

MAPPING = {
    "graph": "timeseries",
    "singlestat": "stat",
    "table-old": "table",
    "grafana-piechart-panel": "piechart",
    "grafana-worldmap-panel": "geomap",
}


def rewrite(dash: dict) -> tuple[dict, list[str]]:
    manual: list[str] = []

    def walk(panels: list[dict]) -> None:
        for p in panels:
            t = p.get("type")
            if t in MAPPING:
                p["type"] = MAPPING[t]
                # Normalize options for common cases; deeper field mapping is type-specific.
                p.setdefault("fieldConfig", {"defaults": {}, "overrides": []})
                p.setdefault("options", {})
            elif t and "angular" in t.lower():
                manual.append(f"panel id={p.get('id')} type={t}")
            if p.get("panels"):
                walk(p["panels"])

    walk(dash.get("panels", []) or [])
    return dash, manual


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=os.environ.get("RUN_ID"))
    args = ap.parse_args()
    if not args.run_id:
        print("RUN_ID missing", file=sys.stderr)
        return 2

    snap = Path("out") / args.run_id / "dashboards" / "snapshot-pre"
    out = Path("migration") / "angular-rewrites"
    out.mkdir(parents=True, exist_ok=True)
    manual_entries: list[dict] = []
    rewritten = 0

    for path in sorted(snap.glob("*.json")):
        payload = json.loads(path.read_text())
        dash = payload.get("dashboard", {})
        new_dash, manual = rewrite(dash)
        if manual:
            manual_entries.append({"uid": dash.get("uid"), "title": dash.get("title"), "panels": manual})
        if new_dash != dash:
            payload["dashboard"] = new_dash
            (out / path.name).write_text(json.dumps(payload, indent=2, sort_keys=True))
            rewritten += 1

    md = ["# Angular manual review", ""]
    for e in manual_entries:
        md += [f"## {e['title']} (`{e['uid']}`)", ""]
        md += [f"- {p}" for p in e["panels"]]
        md += [""]
    Path("migration/angular-manual-review.md").write_text("\n".join(md))

    log("info", "angular_purge", "done", rewritten=rewritten, manual=len(manual_entries))
    return 1 if manual_entries else 0


if __name__ == "__main__":
    sys.exit(main())
