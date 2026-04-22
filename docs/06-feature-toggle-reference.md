# Feature Toggle Reference — canonical list

This is the single source of truth for every v12 feature toggle the platform enables. Mirrored verbatim in `helm/values.common.yaml`. Any change happens here first and propagates via PR.

## `grafana.ini` block

```ini
[feature_toggles]
enable = provisioning,kubernetesDashboards,dashboardsNewLayouts,dashboardScene,grafanaManagedRecordingRules,sqlExpressions,regressionTransformation,adhocFiltersNew,logsPanelControls,panelTimeSettings,gitSync,templateVariablesRegexTransform,multiVariableProperties,suggestedDashboards,otlpLogs,metricsDrilldown,logsDrilldown,tracesDrilldown,profilesDrilldown
```

## One-per-line (for readability + Git diffs)

| Toggle | Introduced | Stage | Purpose |
|---|---|---|---|
| `provisioning` | 12.0 | ga | File + API + Git Sync provisioning backbone |
| `kubernetesDashboards` | 12.0 | exp | k8s-style dashboard storage; required for dynamic v2 layouts |
| `dashboardsNewLayouts` | 12.0 | exp | Dynamic dashboards (tabs, rows with conditional logic) |
| `dashboardScene` | 12.0 | ga | Scenes-powered dashboard runtime |
| `grafanaManagedRecordingRules` | 12.0 | ga | Grafana-managed recording rules |
| `sqlExpressions` | 12.0 | preview | SQL (MySQL dialect) over DS results |
| `regressionTransformation` | 12.1 | ga | Predict / interpolate transform |
| `adhocFiltersNew` | 12.2 | ga | New ad-hoc filter UX |
| `logsPanelControls` | 12.0 | ga | New Logs Explore controls |
| `panelTimeSettings` | 12.3 | ga | Per-panel time drawer |
| `gitSync` | 12.0 | preview | Git Sync (public preview in 12.4 on Cloud; experimental in OSS — enable with toggle) |
| `templateVariablesRegexTransform` | 12.4 | preview | Regex transforms on variable values |
| `multiVariableProperties` | 12.4 | preview | Multi-property variables |
| `suggestedDashboards` | 12.4 | preview | Template + suggested dashboards |
| `otlpLogs` | 12.4 | preview | OpenTelemetry log defaults |
| `metricsDrilldown` | 12.0 | ga | Metrics Drilldown |
| `logsDrilldown` | 12.0 | ga | Logs Drilldown |
| `tracesDrilldown` | 12.0 | ga | Traces Drilldown |
| `profilesDrilldown` | 12.0 | ga | Profiles Drilldown |

## Verification

`make feature-toggles-verify` (also runs inside `make validate`) calls `/api/featuremgmt` on every pod and asserts each toggle above reports `enabled=true`. Fails the pipeline on any mismatch.

## Governance rules

1. Never enable `kubernetesDashboards` or `dashboardsNewLayouts` without a completed `10_backup.sh` in the same run (§15 hard rule #1 — schema v2 is one-way).
2. New toggles added only via PR to this file + `helm/values.common.yaml`; CI rejects drift.
3. Any toggle `stage=preview` is allowed only when an E2E test exists for it under `validation/e2e/`.
