#!/usr/bin/env python3
"""Item 5 — after cutover, verify each pre-upgrade top-level folder creator
still has Admin (either via auto-grant fallback or the explicit provisioning fix).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--baseline", required=True)
    args = ap.parse_args()

    c = GrafanaClient.from_env()
    baseline = json.loads(Path(args.baseline).read_text())
    lost: list[dict] = []

    for row in baseline:
        uid = row.get("uid")
        creator = row.get("createdBy")
        if not uid or not creator:
            continue
        try:
            perms = c.get(f"/api/folders/{uid}/permissions")
        except Exception as e:  # noqa: BLE001
            lost.append({"uid": uid, "creator": creator, "error": str(e)})
            continue
        has_admin = any(
            (p.get("userLogin") == creator and p.get("permission") == "Admin") for p in perms or []
        )
        if not has_admin:
            lost.append({"uid": uid, "creator": creator})

    log("info", "folder_admin_parity", "done", lost=len(lost))
    print(json.dumps(lost, indent=2))
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
