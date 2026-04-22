#!/usr/bin/env python3
"""Render an HTML report from accumulated JSON summaries in out/."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    runs = sorted(Path(args.in_dir).glob("*"))
    body: list[str] = [
        "<!doctype html><html><head><meta charset=utf-8>",
        "<title>grafana12-oss migration report</title>",
        "<style>body{font:14px system-ui;margin:2rem}pre{background:#111;color:#eee;padding:1rem;overflow:auto}</style>",
        "</head><body><h1>grafana12-oss migration report</h1>",
    ]
    for r in runs:
        if not r.is_dir():
            continue
        body.append(f"<h2>{html.escape(r.name)}</h2>")
        for summary in sorted(r.glob("*.summary.json")):
            body.append(f"<h3>{html.escape(summary.name)}</h3>")
            body.append(f"<pre>{html.escape(summary.read_text())}</pre>")
        acc = r / "acceptance.md"
        if acc.exists():
            body.append("<h3>acceptance.md</h3>")
            body.append(f"<pre>{html.escape(acc.read_text())}</pre>")
    body.append("</body></html>")

    Path(args.out).write_text("\n".join(body))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
