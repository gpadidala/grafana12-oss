#!/usr/bin/env python3
"""Item 15 — replace deprecated `cache_size` with its 12.x successors.

Typical mapping (verified against /metrics output):
    grafana_cache_size{cache="memcached|redis"} → grafana_cache_usage_bytes
    grafana_cache_requests_total                → grafana_cache_gets_total
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


MAP = {
    "grafana_cache_size": "grafana_cache_usage_bytes",
    "grafana_cache_requests_total": "grafana_cache_gets_total",
    "cache_size": "grafana_cache_usage_bytes",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hits", required=True, help="file listing hits from grep (path:line:content)")
    ap.add_argument("--apply-to", nargs="+", required=True)
    args = ap.parse_args()

    changed = 0
    for root in args.apply_to:
        for path in Path(root).rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".yaml", ".yml", ".md"}:
                continue
            text = path.read_text()
            new_text = text
            for old, new in MAP.items():
                new_text = new_text.replace(old, new)
            if new_text != text:
                path.write_text(new_text)
                log("info", "rewrite_cache_size_metric", "patched", path=str(path))
                changed += 1
    log("info", "rewrite_cache_size_metric", "done", files=changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
