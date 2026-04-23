#!/usr/bin/env python3
"""Item 4 — Provisioning full-replace ACL gap analysis.

Reads live folder permissions (NDJSON from `gapi /api/folders/{uid}/permissions`)
and every provisioning YAML under provisioning/access-control/, emits the delta
so you can see which users/teams would LOSE access under the 12.3 full-replace
model if you upgrade without rewriting the file.

Usage:
  python3 audit/compare_permissions.py \
    --current out/RUN/audit/04-current-folder-perms.ndjson \
    --provisioning provisioning/access-control/ \
    --out out/RUN/audit/04-permission-gap.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import log  # noqa: E402


def parse_provisioning(root: Path) -> dict[str, list[dict]]:
    """Map folder_uid → list of {subject, permission} from every YAML."""
    declared: dict[str, list[dict]] = {}
    for path in root.rglob("*.yaml"):
        doc = yaml.safe_load(path.read_text()) or {}
        for rp in doc.get("resourcePermissions", []) or []:
            if rp.get("resource") != "folders":
                continue
            uid = rp.get("uid", "")
            declared.setdefault(uid, []).extend(rp.get("permissions", []) or [])
    return declared


def normalize(perm: dict[str, Any]) -> tuple[str, str, str]:
    subj = perm.get("userLogin") or perm.get("team") or perm.get("role") or ""
    kind = "user" if perm.get("userLogin") else ("team" if perm.get("team") else "role")
    return (kind, subj, perm.get("permission", ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--current", required=True)
    ap.add_argument("--provisioning", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    live: dict[str, set[tuple[str, str, str]]] = {}
    for line in Path(args.current).read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        folder = rec.get("folder", "")
        for p in rec.get("perms", []) or []:
            live.setdefault(folder, set()).add(normalize(p))

    declared = parse_provisioning(Path(args.provisioning))
    gap: list[dict] = []
    for folder, live_set in live.items():
        decl_set = {normalize(p) for p in declared.get(folder, [])}
        lost = live_set - decl_set
        added = decl_set - live_set
        if lost or added:
            gap.append({
                "folder": folder,
                "live": sorted(list(live_set)),
                "declared": sorted(list(decl_set)),
                "would_lose_access": sorted(list(lost)),
                "would_gain_access": sorted(list(added)),
            })

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(gap, indent=2))
    log("info", "compare_permissions", "done", gap_count=len(gap))
    return 1 if gap else 0


if __name__ == "__main__":
    sys.exit(main())
