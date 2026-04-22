#!/usr/bin/env python3
"""List installed plugins + flag Angular, unsigned, unpinned grafanaDependency."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _lib import GrafanaClient, log, out_dir, write_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)

    c = GrafanaClient.from_env()
    plugins = c.get("/api/plugins", params={"embedded": 0})
    rows = []
    angular = 0
    unsigned = 0
    no_dep = 0
    for p in plugins:
        is_angular = bool(p.get("angularDetected") or p.get("angular"))
        is_unsigned = (p.get("signatureType") or "").lower() not in {"grafana", "commercial", "community"}
        has_dep = bool((p.get("dependencies") or {}).get("grafanaDependency"))
        if is_angular:
            angular += 1
        if is_unsigned:
            unsigned += 1
        if not has_dep:
            no_dep += 1
        rows.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("type"),
                "version": (p.get("info") or {}).get("version"),
                "angular": is_angular,
                "signatureType": p.get("signatureType"),
                "grafanaDependency": (p.get("dependencies") or {}).get("grafanaDependency"),
            }
        )

    summary = {
        "total": len(rows),
        "angular_count": angular,
        "unsigned_count": unsigned,
        "missing_grafanaDependency": no_dep,
        "rows": rows,
    }
    write_json(out / "plugin_inventory.summary.json", summary)
    log(
        "info",
        "plugin_inventory",
        "done",
        total=len(rows),
        angular=angular,
        unsigned=unsigned,
        no_dep=no_dep,
    )
    return 1 if angular else 0


if __name__ == "__main__":
    sys.exit(main())
