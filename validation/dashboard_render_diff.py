#!/usr/bin/env python3
"""Pre/post dashboard render diff.

Renders each dashboard via the Grafana renderer plugin endpoint, downloads the PNG,
and compares against a baseline captured at audit time. Fails when diff > 2%.

Baseline capture:  --mode baseline  (writes PNGs to out/<run-id>/render-baseline/)
Diff mode:         --mode diff      (compares against a prior baseline dir)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log, write_json  # noqa: E402

try:
    from PIL import Image, ImageChops
except ImportError:
    Image = None  # type: ignore[assignment]


def render(c: GrafanaClient, uid: str) -> bytes:
    r = c.get_raw(f"/render/d/{uid}", params={"width": 1600, "height": 900, "kiosk": "tv"})
    return r.content


def pixel_diff_ratio(a: bytes, b: bytes) -> float:
    if Image is None:
        return 1.0 if hashlib.sha256(a).digest() != hashlib.sha256(b).digest() else 0.0
    ia, ib = Image.open(BytesIO(a)), Image.open(BytesIO(b))
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    diff = ImageChops.difference(ia.convert("RGB"), ib.convert("RGB"))
    bbox = diff.getbbox()
    if not bbox:
        return 0.0
    total = ia.size[0] * ia.size[1]
    changed = sum(1 for px in diff.getdata() if any(px))
    return changed / total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["baseline", "diff"], default="diff")
    ap.add_argument("--baseline-dir", default=None)
    ap.add_argument("--threshold", type=float, default=0.02)
    args = ap.parse_args()
    out = Path(args.out)
    img_dir = out / ("render-baseline" if args.mode == "baseline" else "render-current")
    img_dir.mkdir(parents=True, exist_ok=True)

    c = GrafanaClient.from_env()
    uids = [row["uid"] for row in c.get("/api/search", params={"type": "dash-db", "limit": 5000})]

    results = []
    regressions = 0
    for uid in uids[:50]:  # top 50; extend by sorting on view count in a real env
        try:
            png = render(c, uid)
        except Exception as e:  # noqa: BLE001
            log("warn", "render_diff", "render_failed", uid=uid, err=str(e))
            continue
        (img_dir / f"{uid}.png").write_bytes(png)
        if args.mode == "diff" and args.baseline_dir:
            base = Path(args.baseline_dir) / f"{uid}.png"
            if base.exists():
                ratio = pixel_diff_ratio(base.read_bytes(), png)
                row = {"uid": uid, "ratio": ratio, "ok": ratio <= args.threshold}
                if not row["ok"]:
                    regressions += 1
                results.append(row)

    write_json(out / "dashboard_render_diff.summary.json", {"regressions": regressions, "rows": results, "threshold": args.threshold})
    log("info", "render_diff", "done", regressions=regressions, checked=len(results))
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
