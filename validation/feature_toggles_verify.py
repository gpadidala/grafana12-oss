#!/usr/bin/env python3
"""Assert every §5.6 / docs/06 feature toggle is enabled=true on the live instance.

Fails with rc=1 and writes a precise diff if any toggle is missing or false.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log, write_json  # noqa: E402


REQUIRED = [
    "provisioning",
    "kubernetesDashboards",
    "dashboardsNewLayouts",
    "dashboardScene",
    "grafanaManagedRecordingRules",
    "sqlExpressions",
    "regressionTransformation",
    "adhocFiltersNew",
    "logsPanelControls",
    "panelTimeSettings",
    "gitSync",
    "templateVariablesRegexTransform",
    "multiVariableProperties",
    "suggestedDashboards",
    "otlpLogs",
    "metricsDrilldown",
    "logsDrilldown",
    "tracesDrilldown",
    "profilesDrilldown",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)

    c = GrafanaClient.from_env()
    # /api/featuremgmt is admin-scoped and may 404 behind basic auth; fall back to
    # /api/frontend/settings which reports the same toggle state to any authenticated user.
    try:
        ft = c.get("/api/featuremgmt")
        state = {f["name"]: bool(f.get("enabled")) for f in ft if isinstance(f, dict)}
    except Exception:  # noqa: BLE001
        fs = c.get("/api/frontend/settings")
        state = {k: bool(v) for k, v in (fs.get("featureToggles") or {}).items()}
    missing = [t for t in REQUIRED if not state.get(t)]
    unknown = [t for t in REQUIRED if t not in state]

    report = {
        "required": REQUIRED,
        "missing_or_disabled": missing,
        "unknown": unknown,
        "state": state,
    }
    write_json(out / "feature_toggles.summary.json", report)
    log(
        "info",
        "feature_toggles_verify",
        "done",
        missing_count=len(missing),
        unknown_count=len(unknown),
    )
    if missing or unknown:
        print(json.dumps({"missing": missing, "unknown": unknown}, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
