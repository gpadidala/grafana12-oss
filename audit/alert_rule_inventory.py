#!/usr/bin/env python3
"""Dump all Grafana-managed alert rules, contact points, notification policies, mute timings, templates."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _lib import GrafanaClient, log, write_json


ENDPOINTS = {
    "alert_rules": "/api/v1/provisioning/alert-rules",
    "contact_points": "/api/v1/provisioning/contact-points",
    "policies": "/api/v1/provisioning/policies",
    "mute_timings": "/api/v1/provisioning/mute-timings",
    "templates": "/api/v1/provisioning/templates",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)

    c = GrafanaClient.from_env()
    summary: dict = {"counts": {}, "snapshot_path": str(out / "alerting")}
    (out / "alerting").mkdir(parents=True, exist_ok=True)
    for name, path in ENDPOINTS.items():
        try:
            data = c.get(path)
        except Exception as e:  # noqa: BLE001
            log("warn", "alert_rule_inventory", "fetch_failed", endpoint=path, err=str(e))
            data = []
        count = len(data) if isinstance(data, list) else (len(data.get("route", {}).get("routes", [])) if isinstance(data, dict) else 0)
        summary["counts"][name] = count
        write_json(out / "alerting" / f"{name}.json", data)

    write_json(out / "alert_rule_inventory.summary.json", summary)
    log("info", "alert_rule_inventory", "done", **summary["counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
