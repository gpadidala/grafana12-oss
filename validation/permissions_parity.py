#!/usr/bin/env python3
"""Item 4 — assert every provisioned folder's live ACL matches its YAML exactly."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log  # noqa: E402


def normalize(perm: dict) -> tuple[str, str]:
    subj = perm.get("userLogin") or perm.get("team") or perm.get("role") or ""
    return (subj, perm.get("permission", ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--provisioning", required=True)
    args = ap.parse_args()

    c = GrafanaClient.from_env()
    mismatches: list[dict] = []

    for path in Path(args.provisioning).rglob("*.yaml"):
        doc = yaml.safe_load(path.read_text()) or {}
        for rp in doc.get("resourcePermissions", []) or []:
            if rp.get("resource") != "folders":
                continue
            uid = rp.get("uid", "")
            declared = {normalize(p) for p in rp.get("permissions", []) or []}
            try:
                live_perms = c.get(f"/api/folders/{uid}/permissions")
                live = {normalize(p) for p in live_perms or []}
            except Exception as e:  # noqa: BLE001
                mismatches.append({"uid": uid, "error": str(e)})
                continue
            if declared != live:
                mismatches.append({
                    "uid": uid,
                    "only_in_yaml": sorted(declared - live),
                    "only_live": sorted(live - declared),
                })

    log("info", "permissions_parity", "done", mismatches=len(mismatches))
    for m in mismatches:
        print(m)
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
