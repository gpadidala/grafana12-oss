#!/usr/bin/env python3
"""Item 16 — migrate deprecated /api/alertmanager/grafana/... single-tenant endpoints.

Rewrite map (12.4 → canonical provisioning/per-tenant routes):
  /api/alertmanager/grafana/config/api/v1/alerts        → /api/v1/provisioning/alert-rules
  /api/alertmanager/grafana/api/v2/silences             → /api/alertmanager/grafana/api/v2/silences  (unchanged; noted)
  /api/alertmanager/grafana/config/api/v1/config        → /api/v1/provisioning/policies (or contact-points depending on payload)

This stub applies the deterministic 1:1 rewrites and leaves the rest annotated.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


MAP = {
    r"/api/alertmanager/grafana/config/api/v1/alerts":    "/api/v1/provisioning/alert-rules",
    r"/api/alertmanager/grafana/config/api/v1/templates": "/api/v1/provisioning/templates",
    r"/api/alertmanager/grafana/config/api/v1/receivers": "/api/v1/provisioning/contact-points",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hits", required=True)
    args = ap.parse_args()

    patched = 0
    for line in Path(args.hits).read_text().splitlines():
        if ":" not in line:
            continue
        path_str = line.split(":", 1)[0]
        path = Path(path_str)
        if not path.is_file():
            continue
        text = path.read_text()
        new_text = text
        for pat, repl in MAP.items():
            new_text = re.sub(pat, repl, new_text)
        if new_text != text:
            path.write_text(new_text)
            patched += 1
            log("info", "rewrite_am_endpoints", "patched", path=str(path))

    log("info", "rewrite_am_endpoints", "done", files=patched)
    return 0


if __name__ == "__main__":
    sys.exit(main())
