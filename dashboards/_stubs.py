#!/usr/bin/env python3
"""Generate Scenes-compatible dashboard stubs (schemaVersion 40) from manifests.

Run once:  python3 dashboards/_stubs.py

Produces the §8 validation suite + the v12 feature-demo set listed in
docs/02-feature-enablement-plan.md. Committed output is the source of truth —
this script is just a bootstrap helper so you don't hand-write 40 JSON shells.
"""
from __future__ import annotations

import json
from pathlib import Path


def shell(uid: str, title: str, tags: list[str], description: str = "") -> dict:
    return {
        "uid": uid,
        "title": title,
        "tags": tags,
        "description": description,
        "schemaVersion": 40,
        "version": 1,
        "editable": True,
        "graphTooltip": 0,
        "refresh": "30s",
        "time": {"from": "now-6h", "to": "now"},
        "timepicker": {},
        "templating": {"list": [
            {
                "name": "datasource",
                "type": "datasource",
                "query": "prometheus",
                "refresh": 1,
                "hide": 0,
                "current": {"text": "Prometheus", "value": "prom"},
            },
            {
                "name": "env",
                "type": "custom",
                "multi": True,
                "includeAll": True,
                "options": [
                    {"text": "dev",         "value": "dev"},
                    {"text": "development", "value": "dev"},
                    {"text": "prod",        "value": "prod"},
                    {"text": "production",  "value": "prod"},
                ],
                "_requiresToggle": "multiVariableProperties",
            },
        ]},
        "panels": [
            {
                "id": 1,
                "type": "stat",
                "title": title,
                "gridPos": {"h": 4, "w": 24, "x": 0, "y": 0},
                "datasource": {"uid": "${datasource}", "type": "prometheus"},
                "targets": [{"refId": "A", "expr": "up{job=\"grafana\"}"}],
                "options": {"reduceOptions": {"calcs": ["lastNotNull"]}},
                "fieldConfig": {"defaults": {}, "overrides": []},
            }
        ],
    }


VALIDATION = [
    ("v12-upgrade-overview", "v12 Upgrade Overview", "Single pane — version, uptime, pod count, DS health, alert firing, plugin errors"),
    ("dashboard-render-health", "Dashboard Render Health", "grafana_page_response_status_total + request duration histograms"),
    ("datasource-health", "Data Source Health", "Per-DS success, latency, error code breakdown"),
    ("alerting-engine", "Alerting Engine", "Rule eval duration, failures, AM cluster status, notification latency"),
    ("unified-alerting-ha", "Unified Alerting HA (12.4 prefix)", "HA gossip + new 12.4 cluster metric prefix; split-brain detection"),
    ("scenes-migration", "Scenes Migration", "schemaVersion distribution, v1→v2 progress, dynamic-dashboard adoption"),
    ("plugin-inventory", "Plugin Inventory", "Signature type, Angular flag (== 0), versions"),
    ("angular-regression-guard", "Angular Regression Guard", "Angular panel count — RED if > 0"),
    ("git-sync-health", "Git Sync Health", "Sync success/fail, last-sync, open PRs, conflicts"),
    ("rbac-audit", "RBAC Audit", "Service accounts vs API keys, folder permission distribution"),
    ("session-and-login", "Session & Login", "Login success/failure, OIDC errors, session duration"),
    ("db-and-cache", "DB & Cache", "Postgres latency, Redis hit rate, session-storage size"),
    ("rendering-service", "Rendering Service", "Renderer queue, duration p95, failures, PDF exports"),
    ("api-latency-slo", "API Latency SLO", "Burn-rate panels, 99% < 500ms"),
    ("migration-cutover", "Migration Cutover", "Pre/post KPI comparison; variables flip snapshots"),
]

FEATURE_DEMOS = [
    # 12.0
    ("v12-drilldown-suite",             "v12 Drilldown Suite"),
    ("v12-recording-rules",             "v12 Grafana-managed Recording Rules"),
    ("v12-cloud-migration",             "v12 Cloud Migration Assistant"),
    ("v12-plugin-catalog",              "v12 Plugin Catalog"),
    ("v12-git-sync",                    "v12 Git Sync"),
    ("v12-dynamic-dashboards",          "v12 Dynamic Dashboards"),
    ("v12-sql-expressions",             "v12 SQL Expressions"),
    ("v12-react-data-grid-table",       "v12 Table (react-data-grid)"),
    ("v12-logs-controls",               "v12 Logs Explore Controls"),
    # 12.1
    ("v12-alert-rule-page",             "v12.1 Alert Rule Page"),
    ("v12-regression-transform",        "v12.1 Regression Transform"),
    ("v12-viz-actions",                 "v12.1 Visualization Actions"),
    ("v12-advisor",                     "v12.1 Grafana Advisor"),
    # 12.2
    ("v12-adhoc-filters",               "v12.2 Ad-hoc Filters"),
    ("v12-table-redesign",              "v12.2 Redesigned Table"),
    ("v12-logs-json-viewer",            "v12.2 Logs JSON Viewer"),
    ("v12-metrics-to-alert",            "v12.2 Metrics Drilldown → Alert"),
    # 12.3
    ("v12-interactive-learning",        "v12.3 Interactive Learning"),
    ("v12-panel-time-drawer",           "v12.3 Panel Time Drawer"),
    ("v12-switch-variable",             "v12.3 Switch Variable Type"),
    ("v12-logs-panel",                  "v12.3 Redesigned Logs Panel"),
    ("v12-new-datasources",             "v12.3 New Data Sources"),
    # 12.4
    ("v12-git-sync-pr",                 "v12.4 Git Sync (PR workflow)"),
    ("v12-dynamic-dashboards-pp",       "v12.4 Dynamic Dashboards (PP)"),
    ("v12-dashboards-from-template",    "v12.4 Dashboards From Templates"),
    ("v12-multi-property-vars",         "v12.4 Multi-property Variables"),
    ("v12-regex-variables",             "v12.4 Variable Regex Transforms"),
    ("v12-viz-suggestions",             "v12.4 Visualization Suggestions"),
    ("v12-gauge",                       "v12.4 Updated Gauge"),
    ("v12-otlp-logs",                   "v12.4 OpenTelemetry Log Defaults"),
    ("v12-zabbix",                      "v12.4 Zabbix Enhancements"),
]


def main() -> None:
    root = Path(__file__).resolve().parent
    for uid, title, desc in VALIDATION:
        path = root / "validation" / f"{uid}.json"
        path.write_text(json.dumps(shell(uid, title, ["v12-migration", "platform", "validation"], desc), indent=2, sort_keys=True))
    for uid, title in FEATURE_DEMOS:
        path = root / "v12-feature-demos" / f"{uid}.json"
        path.write_text(json.dumps(shell(uid, title, ["v12-migration", "feature-demo"], title), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
