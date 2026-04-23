#!/usr/bin/env python3
"""Item 18 — rewrite deprecated `datagrid` panels to `table` (react-data-grid)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


def walk(panels: list[dict]) -> int:
    n = 0
    for p in panels or []:
        if p.get("type") == "datagrid":
            p["type"] = "table"
            p.setdefault("options", {})
            p.setdefault("fieldConfig", {"defaults": {}, "overrides": []})
            n += 1
        if p.get("panels"):
            n += walk(p["panels"])
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", required=True, help="output of audit/find_panel_type.py --type datagrid")
    args = ap.parse_args()

    inventory = json.loads(Path(args.panels).read_text())
    total = 0
    for entry in inventory:
        src = Path(entry.get("source_path", ""))
        if not src.exists():
            continue
        payload = json.loads(src.read_text())
        dash = payload.get("dashboard", payload)
        n = walk(dash.get("panels", []) or [])
        if n:
            src.write_text(json.dumps(payload, indent=2))
            total += n
            log("info", "rewrite_datagrid_to_table", "patched", uid=dash.get("uid"), panels=n)

    log("info", "rewrite_datagrid_to_table", "done", total=total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
