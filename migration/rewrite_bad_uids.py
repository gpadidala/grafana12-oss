#!/usr/bin/env python3
"""Item 9 — rewrite non-conformant DS UIDs and every panel reference.

Target regex: ^[a-zA-Z0-9_-]{1,40}$
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402

VALID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def slugify(uid: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]", "-", uid)[:40].strip("-") or "ds"
    return slug


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bad-uids", required=True)
    ap.add_argument("--provisioning", required=True)
    ap.add_argument("--dashboards", required=True)
    ap.add_argument("--mapping", required=True)
    args = ap.parse_args()

    bad = [u.strip() for u in Path(args.bad_uids).read_text().splitlines() if u.strip() and not VALID.match(u.strip())]
    mapping = {u: slugify(u) for u in bad}
    Path(args.mapping).parent.mkdir(parents=True, exist_ok=True)
    Path(args.mapping).write_text(json.dumps(mapping, indent=2))

    def subst(s: str) -> str:
        for old, new in mapping.items():
            s = s.replace(old, new)
        return s

    for path in Path(args.provisioning).rglob("*.yaml"):
        path.write_text(subst(path.read_text()))
    for path in Path(args.dashboards).rglob("*.json"):
        path.write_text(subst(path.read_text()))

    log("info", "rewrite_bad_uids", "done", renamed=len(mapping))
    return 0


if __name__ == "__main__":
    sys.exit(main())
