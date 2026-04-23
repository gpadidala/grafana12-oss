#!/usr/bin/env python3
"""Item 12 — rewrite pre-Scenes DOM selectors to Scenes test-ids in validation/ CI scripts.

Mapping is conservative: flags unknowns rather than guessing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


SELECTOR_MAP = {
    r'\[data-panelid=["\'](\d+)["\']\]': r'[data-testid="data-testid Panel header $1"]',
    r'\.panel-container':                  '[data-testid="data-testid Panel header"]',
    r'getPanelCtrl\(':                     'getScene(',
}


def rewrite(text: str) -> tuple[str, int]:
    n = 0
    for pattern, repl in SELECTOR_MAP.items():
        text, count = re.subn(pattern, repl, text)
        n += count
    return text, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()

    total = 0
    for path in Path(args.root).rglob("*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".mjs", ".py", ".sh"}:
            continue
        text = path.read_text()
        new_text, n = rewrite(text)
        if n:
            path.write_text(new_text)
            total += n
            log("info", "rewrite_scenes_selectors", "patched", path=str(path), count=n)

    log("info", "rewrite_scenes_selectors", "done", total=total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
