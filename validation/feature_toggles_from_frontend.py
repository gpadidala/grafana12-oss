#!/usr/bin/env python3
"""Parse /api/frontend/settings JSON from stdin and assert every §5.6 toggle is enabled.

Used by `make toggles` in lab/Makefile when an SA token isn't handy — falls back to
frontend/settings which any authenticated user (including admin basic-auth) can read.

Exit 0 when all toggles are enabled; 1 otherwise.
"""
from __future__ import annotations

import json
import sys


REQUIRED = [
    "provisioning", "kubernetesDashboards", "dashboardsNewLayouts",
    "dashboardScene", "grafanaManagedRecordingRules", "sqlExpressions",
    "regressionTransformation", "adhocFiltersNew", "logsPanelControls",
    "panelTimeSettings", "gitSync", "templateVariablesRegexTransform",
    "multiVariableProperties", "suggestedDashboards", "otlpLogs",
    "metricsDrilldown", "logsDrilldown", "tracesDrilldown", "profilesDrilldown",
]


def main() -> int:
    data = json.load(sys.stdin)
    ft = data.get("featureToggles", {}) or {}
    version = data.get("buildInfo", {}).get("version", "?")

    ok, bad, missing = [], [], []
    for t in REQUIRED:
        if t in ft:
            (ok if ft[t] else bad).append(t)
        else:
            missing.append(t)

    print(f"  grafana {version}  —  required={len(REQUIRED)}  enabled={len(ok)}  disabled={len(bad)}  missing={len(missing)}")
    for t in ok:
        print(f"    + {t}")
    for t in bad:
        print(f"    - {t} (disabled)")
    for t in missing:
        print(f"    ? {t} (missing)")
    return 0 if not (bad or missing) else 1


if __name__ == "__main__":
    sys.exit(main())
