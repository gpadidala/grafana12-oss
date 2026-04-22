#!/usr/bin/env python3
"""API smoke: /api/health, /api/datasources, /api/alertmanager/grafana/api/v2/status, /api/plugins, /api/featuremgmt."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log, write_json  # noqa: E402


CHECKS = [
    ("/api/health", lambda b: b.get("database") == "ok"),
    ("/api/datasources", lambda b: isinstance(b, list) and len(b) > 0),
    ("/api/alertmanager/grafana/api/v2/status", lambda b: isinstance(b, dict)),
    ("/api/plugins", lambda b: isinstance(b, list)),
    ("/api/featuremgmt", lambda b: isinstance(b, list)),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)

    c = GrafanaClient.from_env()
    rows = []
    failed = 0
    for path, predicate in CHECKS:
        try:
            body = c.get(path)
            ok = bool(predicate(body))
        except Exception as e:  # noqa: BLE001
            ok, body = False, {"error": str(e)}
        rows.append({"path": path, "ok": ok})
        if not ok:
            failed += 1
        log("info", "api_smoke", "check", path=path, ok=ok)

    write_json(out / "api_smoke.summary.json", {"failed": failed, "checks": rows})
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
