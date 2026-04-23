#!/usr/bin/env python3
"""Item 4 — rewrite every access-control YAML to the COMPLETE desired ACL.

In 12.3 partial permission files replace the whole ACL (anything omitted is
removed, except default Admin). This script reads the compare_permissions gap
report and merges the live ACL into the provisioning file so nothing is lost.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", required=True, help="out/.../04-permission-gap.json")
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    gap = json.loads(Path(args.gap).read_text())
    live_by_folder = {row["folder"]: row["live"] for row in gap}

    src = Path(args.in_dir)
    dst = Path(args.out)
    dst.mkdir(parents=True, exist_ok=True)

    for path in src.rglob("*.yaml"):
        rel = path.relative_to(src)
        out_path = dst / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc = yaml.safe_load(path.read_text()) or {}
        for rp in doc.get("resourcePermissions", []) or []:
            if rp.get("resource") != "folders":
                continue
            folder_uid = rp.get("uid", "")
            live = live_by_folder.get(folder_uid, [])
            existing = {(p.get("userLogin") or p.get("team") or p.get("role", ""), p.get("permission")) for p in rp.get("permissions", []) or []}
            merged = list(rp.get("permissions", []) or [])
            for kind, subj, perm in live:
                if (subj, perm) in existing:
                    continue
                merged.append({ {"user": "userLogin", "team": "team", "role": "role"}[kind]: subj, "permission": perm })
            rp["permissions"] = merged
        out_path.write_text(yaml.safe_dump(doc, sort_keys=False))
        log("info", "rewrite_permissions", "wrote", path=str(out_path))

    return 0


if __name__ == "__main__":
    sys.exit(main())
