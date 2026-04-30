#!/usr/bin/env python3
"""Item 8 — ensure every custom plugin's plugin.json declares a valid grafanaDependency range."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="e.g. 12.4.3")
    ap.add_argument("--root", required=True)
    args = ap.parse_args()

    target = args.target
    major = int(target.split(".")[0])
    # Conservative range: anything since last-major through next-major exclusive.
    dep_range = f">={major-1}.0.0 <{major+1}.0.0"

    changed = 0
    for path in Path(args.root).rglob("plugin.json"):
        doc = json.loads(path.read_text())
        deps = doc.setdefault("dependencies", {})
        if deps.get("grafanaDependency") != dep_range:
            old = deps.get("grafanaDependency")
            deps["grafanaDependency"] = dep_range
            path.write_text(json.dumps(doc, indent=2) + "\n")
            log("info", "fix_plugin_dependency", "patched", path=str(path), old=old, new=dep_range)
            changed += 1

    log("info", "fix_plugin_dependency", "done", changed=changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
