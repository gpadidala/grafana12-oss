#!/usr/bin/env python3
"""Dump all data sources + run /health on each. Validate UID format (≤40, [a-zA-Z0-9-])."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _lib import GrafanaClient, log, write_json

UID_RE = re.compile(r"^[A-Za-z0-9-]{1,40}$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)

    c = GrafanaClient.from_env()
    ds = c.get("/api/datasources")
    rows = []
    bad_uid = 0
    unhealthy = 0
    for d in ds:
        uid = d.get("uid", "")
        uid_ok = bool(UID_RE.match(uid))
        if not uid_ok:
            bad_uid += 1
        health = {"status": "skipped"}
        try:
            health = c.get(f"/api/datasources/uid/{uid}/health")
        except Exception as e:  # noqa: BLE001
            health = {"status": "error", "message": str(e)}
            unhealthy += 1
        if health.get("status") not in {"OK", "ok"}:
            unhealthy += 1
        rows.append(
            {
                "uid": uid,
                "name": d.get("name"),
                "type": d.get("type"),
                "uid_format_ok": uid_ok,
                "health": health,
            }
        )

    summary = {
        "total": len(rows),
        "bad_uid_count": bad_uid,
        "unhealthy_count": unhealthy,
        "rows": rows,
    }
    write_json(out / "datasource_inventory.summary.json", summary)
    log("info", "datasource_inventory", "done", total=len(rows), bad_uid=bad_uid, unhealthy=unhealthy)
    return 1 if (bad_uid or unhealthy) else 0


if __name__ == "__main__":
    sys.exit(main())
