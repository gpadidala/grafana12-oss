#!/usr/bin/env python3
"""Item 11 — rewrite HA Alertmanager cluster metric prefix across dashboards/rules.

Builds a mapping from the `old` grep output to the `new` grep output (from the
live 12.4.3 /metrics), applies in-place across --apply-to directories.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402

METRIC_RE = re.compile(r"(?:^|\W)(alertmanager_(?:cluster|peer)_[a-z_]+)")


def collect_names(path: Path) -> set[str]:
    names: set[str] = set()
    for line in path.read_text().splitlines():
        for m in METRIC_RE.finditer(line):
            names.add(m.group(1))
    return names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--apply-to", nargs="+", required=True)
    args = ap.parse_args()

    old_names = sorted(collect_names(Path(args.old)))
    new_names = sorted(collect_names(Path(args.new)))
    # Align by suffix where possible; otherwise skip and let human review.
    mapping: dict[str, str] = {}
    for old in old_names:
        suffix = old.split("_", 2)[-1] if "_" in old else ""
        candidates = [n for n in new_names if n.endswith(suffix)]
        if len(candidates) == 1:
            mapping[old] = candidates[0]
    log("info", "rewrite_am_metric_prefix", "mapping_derived", count=len(mapping))

    for root in args.apply_to:
        for path in Path(root).rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".yaml", ".yml", ".md"}:
                continue
            text = path.read_text()
            new_text = text
            for old, new in mapping.items():
                new_text = new_text.replace(old, new)
            if new_text != text:
                path.write_text(new_text)
                log("info", "rewrite_am_metric_prefix", "patched", path=str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
