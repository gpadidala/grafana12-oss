#!/usr/bin/env python3
"""Export every dashboard's JSON + summarize schemaVersion distribution."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from _lib import GrafanaClient, log, out_dir, write_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    snap = out / "dashboards" / "snapshot-pre"
    snap.mkdir(parents=True, exist_ok=True)

    c = GrafanaClient.from_env()
    results = c.get("/api/search", params={"type": "dash-db", "limit": 5000})
    schema_counter: Counter = Counter()
    exports = []

    for row in results:
        uid = row["uid"]
        try:
            payload = c.get(f"/api/dashboards/uid/{uid}")
        except Exception as e:  # noqa: BLE001
            log("warn", "dashboard_inventory", "fetch_failed", uid=uid, err=str(e))
            continue
        dash = payload.get("dashboard", {})
        sv = int(dash.get("schemaVersion", 0))
        schema_counter[sv] += 1
        (snap / f"{uid}.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
        exports.append({"uid": uid, "title": dash.get("title"), "schemaVersion": sv})

    summary = {
        "dashboard_count": len(exports),
        "schema_distribution": dict(sorted(schema_counter.items())),
        "dashboards_below_v36": sum(v for k, v in schema_counter.items() if k < 36),
        "exports_path": str(snap),
    }
    write_json(out / "dashboard_inventory.summary.json", summary)
    log("info", "dashboard_inventory", "done", **summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
