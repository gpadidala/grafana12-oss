#!/usr/bin/env python3
"""Bump every dashboard schemaVersion and force-save post-upgrade.

On a 12.4 instance this triggers Scenes-based migration server-side. Combined with
the kubernetesDashboards / dashboardsNewLayouts toggles, newly saved dashboards land
in the v2 layout engine. Because the v2 migration is one-way (§15 hard rule #1),
this script REFUSES to run unless out/<run-id>/backup/pg_dump/grafana.sql.gz exists
and is < 24h old.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log  # noqa: E402


def assert_fresh_backup(run_id: str) -> None:
    dump = Path("out") / run_id / "backup" / "pg_dump" / "grafana.sql.gz"
    if not dump.exists():
        log("fatal", "schema_upgrade", "missing_dump", path=str(dump))
        sys.exit(2)
    age = time.time() - dump.stat().st_mtime
    if age > 24 * 3600:
        log("fatal", "schema_upgrade", "stale_dump", age_seconds=int(age))
        sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=os.environ.get("RUN_ID"))
    args = ap.parse_args()
    if not args.run_id:
        print("RUN_ID missing", file=sys.stderr)
        return 2

    assert_fresh_backup(args.run_id)

    c = GrafanaClient.from_env()
    # Prefer rewritten dashboards when present; fall back to pre-snapshot.
    rewrite_dir = Path("migration") / "angular-rewrites"
    snap_dir = Path("out") / args.run_id / "dashboards" / "snapshot-pre"

    saved = 0
    failed = 0
    for src in sorted(snap_dir.glob("*.json")):
        preferred = rewrite_dir / src.name
        payload = json.loads((preferred if preferred.exists() else src).read_text())
        dash = payload.get("dashboard", {})
        # Force a save; let the server migrate schemaVersion.
        body = {
            "dashboard": dash,
            "folderUid": payload.get("meta", {}).get("folderUid"),
            "overwrite": True,
            "message": "v12 migration force-save (schema upgrade)",
        }
        try:
            c.session.post(
                f"{c.base_url}/api/dashboards/db",
                json=body,
                timeout=60,
            ).raise_for_status()
            saved += 1
        except Exception as e:  # noqa: BLE001
            log("warn", "schema_upgrade", "save_failed", uid=dash.get("uid"), err=str(e))
            failed += 1

    log("info", "schema_upgrade", "done", saved=saved, failed=failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
