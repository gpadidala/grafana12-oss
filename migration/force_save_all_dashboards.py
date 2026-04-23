#!/usr/bin/env python3
"""Item 29 — force-save every dashboard once post-upgrade so auto-migrated
Angular → React panels persist to the DB.

Grafana migrates on load; a save is what makes the migration stick. Without
this step unsaved dashboards re-migrate on every load (slow) and Git Sync diffs
stay blank.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--only-if-angular-pre", action="store_true")
    ap.add_argument("--inventory", help="TSV of pre-upgrade angular panels (optional)")
    args = ap.parse_args()

    if os.environ.get("CONFIRM") != "yes":
        print("CONFIRM=yes required — this rewrites every dashboard", file=sys.stderr)
        return 2

    c = GrafanaClient.from_env()

    only: set[str] | None = None
    if args.only_if_angular_pre and args.inventory:
        only = {line.split("\t", 1)[0] for line in Path(args.inventory).read_text().splitlines() if line.strip()}

    saved = 0
    failed = 0
    for row in c.get("/api/search", params={"type": "dash-db", "limit": 5000}):
        uid = row["uid"]
        if only and uid not in only:
            continue
        try:
            payload = c.get(f"/api/dashboards/uid/{uid}")
            body = {
                "dashboard": payload["dashboard"],
                "folderUid": payload.get("meta", {}).get("folderUid"),
                "overwrite": True,
                "message": "v12 migration — force-save Angular→React persistence",
            }
            c.session.post(f"{c.base_url}/api/dashboards/db", json=body, timeout=60).raise_for_status()
            saved += 1
        except Exception as e:  # noqa: BLE001
            log("warn", "force_save", "failed", uid=uid, err=str(e))
            failed += 1

    log("info", "force_save", "done", saved=saved, failed=failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
