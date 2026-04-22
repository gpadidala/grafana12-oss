#!/usr/bin/env python3
"""Aggregate acceptance gate (§11). Reads every other summary and produces acceptance.md.

Exit 0 only when every gate passes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import log  # noqa: E402


def load(path: Path) -> dict:
    if not path.exists():
        return {"_missing": True}
    return json.loads(path.read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)

    gates = {
        "feature_toggles": load(out / "feature_toggles.summary.json"),
        "api_smoke": load(out / "api_smoke.summary.json"),
        "render_diff": load(out / "dashboard_render_diff.summary.json"),
        "alerting_parity": load(out / "alerting_parity.summary.json"),
    }

    failed = []
    if gates["feature_toggles"].get("missing_or_disabled") or gates["feature_toggles"].get("unknown"):
        failed.append("feature_toggles")
    if gates["api_smoke"].get("failed"):
        failed.append("api_smoke")
    if gates["render_diff"].get("regressions"):
        failed.append("render_diff")
    if gates["alerting_parity"].get("parity_ratio", 1.0) < 0.99:
        failed.append("alerting_parity")

    md = ["# Acceptance Gate", ""]
    md.append(f"**Verdict:** {'FAIL' if failed else 'PASS'}")
    md.append("")
    md.append(f"**Failed gates:** {failed or 'none'}")
    md.append("")
    for name, data in gates.items():
        md.append(f"## {name}")
        md.append("```json")
        md.append(json.dumps(data, indent=2))
        md.append("```")

    (out / "acceptance.md").write_text("\n".join(md))
    log("info", "acceptance_gate", "done", verdict="FAIL" if failed else "PASS", failed=failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
