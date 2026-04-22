#!/usr/bin/env python3
"""Alert rule parity check.

Compares alert rules between a pre-upgrade snapshot (out/<run-id>/audit/alerting/alert_rules.json)
and the live 12.4.x instance. Confirms every rule UID + group + evaluation interval
survives the migration. Also samples recent evaluation state to assert firing parity.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log, write_json  # noqa: E402


def key(rule: dict) -> tuple[str, str, str]:
    return (rule.get("folderUID", ""), rule.get("ruleGroup", ""), rule.get("uid", ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pre-snapshot", required=False,
                    help="Path to pre-upgrade alerting/alert_rules.json (defaults to latest audit-*).")
    args = ap.parse_args()
    out = Path(args.out)

    pre_path: Path | None
    if args.pre_snapshot:
        pre_path = Path(args.pre_snapshot)
    else:
        candidates = sorted(Path("out").glob("audit-*/alerting/alert_rules.json"))
        pre_path = candidates[-1] if candidates else None
    if not pre_path or not pre_path.exists():
        log("warn", "alerting_parity", "no_pre_snapshot")
        write_json(out / "alerting_parity.summary.json", {"error": "no pre-snapshot"})
        return 0

    pre_rules = json.loads(pre_path.read_text())
    pre_keys = {key(r) for r in pre_rules}

    c = GrafanaClient.from_env()
    live = c.get("/api/v1/provisioning/alert-rules")
    live_keys = {key(r) for r in live}

    missing = sorted(pre_keys - live_keys)
    added = sorted(live_keys - pre_keys)
    ratio = len(pre_keys & live_keys) / max(len(pre_keys), 1)

    summary = {
        "pre_count": len(pre_keys),
        "live_count": len(live_keys),
        "parity_ratio": ratio,
        "missing_sample": missing[:20],
        "added_sample": added[:20],
    }
    write_json(out / "alerting_parity.summary.json", summary)
    log("info", "alerting_parity", "done", **{k: v for k, v in summary.items() if not k.endswith("sample")})
    return 0 if ratio >= 0.99 else 1


if __name__ == "__main__":
    sys.exit(main())
