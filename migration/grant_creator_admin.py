#!/usr/bin/env python3
"""Item 5 — emit a provisioning file that explicitly grants Admin to the folder creator.

12.3+ no longer auto-grants Admin to whoever created a top-level folder.
This restores that behavior for specific folders.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders", required=True, help="out/.../05-toplevel-folder-creators.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    creators = json.loads(Path(args.folders).read_text())
    doc: dict = {"apiVersion": 1, "resourcePermissions": []}
    for row in creators:
        uid, created_by = row.get("uid"), row.get("createdBy")
        if not uid or not created_by:
            continue
        doc["resourcePermissions"].append({
            "orgId": 1, "resource": "folders", "uid": uid,
            "permissions": [{"userLogin": created_by, "permission": "Admin"}],
        })

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(yaml.safe_dump(doc, sort_keys=False))
    log("info", "grant_creator_admin", "done", folders=len(doc["resourcePermissions"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
