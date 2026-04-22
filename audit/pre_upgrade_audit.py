#!/usr/bin/env python3
"""Pre-upgrade audit orchestrator (§3 of master prompt).

Emits a GO/NO-GO verdict to <out>/report.md + report.json.
Delegates to the per-domain inventory scripts; this file only aggregates.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _lib import GrafanaClient, log, out_dir, write_json


BLOCKERS = []
WARNINGS = []


def run_child(script: str, out: Path) -> dict:
    log("info", "audit", "child_start", script=script)
    res = subprocess.run(
        [sys.executable, f"audit/{script}", "--out", str(out)],
        capture_output=True,
        text=True,
    )
    log("info", "audit", "child_end", script=script, rc=res.returncode)
    if res.returncode != 0:
        BLOCKERS.append(f"{script} failed: rc={res.returncode}")
    summary_path = out / f"{Path(script).stem}.summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text())
    return {"error": "no summary emitted"}


def check_health(c: GrafanaClient) -> dict:
    h = c.get("/api/health")
    settings = c.get("/api/frontend/settings")
    version = settings.get("buildInfo", {}).get("version", "unknown")
    log("info", "audit", "health", version=version, db=h.get("database"))
    if not version.startswith("11."):
        BLOCKERS.append(f"source version unexpected: {version}")
    return {"version": version, "health": h}


def check_editors_can_admin(c: GrafanaClient) -> None:
    """12.0 removed editors_can_admin — flag presence."""
    # We cannot read grafana.ini through the API; require ops to confirm.
    WARNINGS.append(
        "Manually confirm grafana.ini has no `editors_can_admin` key (removed in 12.0)."
    )


def check_feature_toggles(c: GrafanaClient) -> dict:
    ft = c.get("/api/featuremgmt")
    enabled = {f["name"]: f.get("enabled", False) for f in ft if isinstance(f, dict)}
    return {"current_state": enabled}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=False)
    args = ap.parse_args()
    out = out_dir(args.out)

    c = GrafanaClient.from_env()
    summary = {"run_id": out.name, "blockers": [], "warnings": [], "children": {}}

    summary["health"] = check_health(c)
    check_editors_can_admin(c)
    summary["feature_toggles"] = check_feature_toggles(c)

    for script in (
        "dashboard_inventory.py",
        "plugin_inventory.py",
        "datasource_inventory.py",
        "alert_rule_inventory.py",
        "schema_diff.py",
    ):
        summary["children"][script] = run_child(script, out)

    summary["blockers"] = BLOCKERS
    summary["warnings"] = WARNINGS
    verdict = "GO" if not BLOCKERS else "NO-GO"
    summary["verdict"] = verdict

    write_json(out / "report.json", summary)
    md = [f"# Pre-Upgrade Audit — {verdict}", ""]
    md += [f"- **Source version:** {summary['health']['version']}"]
    md += [f"- **Blockers ({len(BLOCKERS)}):**"] + [f"  - {b}" for b in BLOCKERS]
    md += [f"- **Warnings ({len(WARNINGS)}):**"] + [f"  - {w}" for w in WARNINGS]
    md += ["", "## Per-domain summaries", ""]
    for k, v in summary["children"].items():
        md += [f"### {k}", "```json", json.dumps(v, indent=2), "```", ""]
    (out / "report.md").write_text("\n".join(md))
    log("info", "audit", "verdict", verdict=verdict, out=str(out))
    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
