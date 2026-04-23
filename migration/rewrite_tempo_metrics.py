#!/usr/bin/env python3
"""Item 10 — rewrite Tempo metrics-summary / Aggregate-by panels to TraceQL metrics.

Conservative: flags each panel with a TODO comment in the title so a human can
finish the query shape. Removes the deprecated `groupBy` / `metrics/summary`
payload fragments.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


def rewrite_panel(p: dict) -> bool:
    changed = False
    for t in p.get("targets", []) or []:
        if "metrics/summary" in json.dumps(t) or "groupBy" in t:
            t.pop("groupBy", None)
            t["queryType"] = "metrics"
            t.setdefault("expr", "{ } | rate()")
            p["title"] = f"[TODO migrate] {p.get('title','')}"
            changed = True
    if p.get("panels"):
        for sub in p["panels"]:
            changed = rewrite_panel(sub) or changed
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    inventory = json.loads(Path(args.panels).read_text())
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    for entry in inventory:
        # Re-read the full dashboard JSON and rewrite on a copy.
        src = Path(entry.get("source_path", ""))
        if not src.exists():
            log("warn", "rewrite_tempo_metrics", "missing_source", uid=entry.get("uid"))
            continue
        payload = json.loads(src.read_text())
        dash = payload.get("dashboard", payload)
        changed = False
        for p in dash.get("panels", []) or []:
            changed = rewrite_panel(p) or changed
        if changed:
            (out_root / f"{dash.get('uid','unknown')}.json").write_text(json.dumps(payload, indent=2))

    log("info", "rewrite_tempo_metrics", "done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
