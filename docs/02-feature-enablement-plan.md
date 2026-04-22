# Feature Enablement Plan — v12.0 → v12.4

Every feature below is **enabled** in `helm/values.common.yaml` via `[feature_toggles]` and gets a demo dashboard in `dashboards/v12-feature-demos/v12-<slug>.json`. `make feature-toggles-verify` fails the pipeline if any toggle reports `enabled=false` or `stage=unknown` at runtime.

## 12.0 (major)

| Feature | Toggle(s) | Demo dashboard | E2E test |
|---|---|---|---|
| Drilldown GA (Metrics/Logs/Traces/Profiles) | `metricsDrilldown,logsDrilldown,tracesDrilldown,profilesDrilldown` | `v12-drilldown-suite.json` | `validation/e2e/drilldown.spec.ts` |
| Grafana-managed recording rules GA | `grafanaManagedRecordingRules` | `v12-recording-rules.json` | `validation/e2e/recording-rules.spec.ts` |
| Cloud Migration Assistant GA | (UI-only) | `v12-cloud-migration.json` | `validation/e2e/cloud-migration.spec.ts` |
| Plugin management | (core) | `v12-plugin-catalog.json` | `validation/e2e/plugin-catalog.spec.ts` |
| Git Sync (exp. OSS) | `gitSync,provisioning` | `v12-git-sync.json` | `validation/e2e/git-sync.spec.ts` |
| Terraform / grafanactl / grr | (tooling) | n/a | `validation/e2e/grafanactl.spec.ts` |
| Dynamic dashboards (exp.) | `kubernetesDashboards,dashboardsNewLayouts,dashboardScene` | `v12-dynamic-dashboards.json` | `validation/e2e/dynamic-dashboards.spec.ts` |
| SQL Expressions | `sqlExpressions` | `v12-sql-expressions.json` | `validation/e2e/sql-expressions.spec.ts` |
| Table panel `react-data-grid` | (core, 12.0+) | `v12-react-data-grid-table.json` | `validation/e2e/react-data-grid.spec.ts` |
| Scenes-powered architecture | `dashboardScene` | all dashboards | `validation/e2e/scenes.spec.ts` |
| Experimental themes | (core) | n/a | `validation/e2e/themes.spec.ts` |
| New Logs Explore controls | `logsPanelControls` | `v12-logs-controls.json` | `validation/e2e/logs-controls.spec.ts` |

## 12.1

| Feature | Toggle(s) | Demo dashboard | E2E test |
|---|---|---|---|
| New Alert rule page GA | (core) | `v12-alert-rule-page.json` | `validation/e2e/alert-rule-page.spec.ts` |
| Regression analysis transformation | `regressionTransformation` | `v12-regression-transform.json` | `validation/e2e/regression.spec.ts` |
| Visualization Actions custom vars | (core) | `v12-viz-actions.json` | `validation/e2e/viz-actions.spec.ts` |
| Grafana Advisor | (core) | `v12-advisor.json` | `validation/e2e/advisor.spec.ts` |
| Google OAuth HD parameter validation | `[auth.google]` | n/a | `validation/e2e/oidc-google.spec.ts` |
| GCP SA + Impersonation | (GCP DS config) | n/a | `validation/e2e/gcp-ds-impersonation.spec.ts` |

## 12.2

| Feature | Toggle(s) | Demo dashboard | E2E test |
|---|---|---|---|
| Enhanced ad-hoc filtering GA | `adhocFiltersNew` | `v12-adhoc-filters.json` | `validation/e2e/adhoc-filters.spec.ts` |
| Redesigned table viz GA | (core) | `v12-table-redesign.json` | `validation/e2e/table-redesign.spec.ts` |
| Logs Drilldown JSON viewer | `logsDrilldown` | `v12-logs-json-viewer.json` | `validation/e2e/logs-json.spec.ts` |
| Metrics Drilldown → alert rule | `metricsDrilldown` | `v12-metrics-to-alert.json` | `validation/e2e/metrics-to-alert.spec.ts` |
| SQL Expressions public preview | `sqlExpressions` | (reused) | (reused) |

## 12.3

| Feature | Toggle(s) | Demo dashboard | E2E test |
|---|---|---|---|
| Interactive learning (public preview) | (core) | `v12-interactive-learning.json` | `validation/e2e/interactive-learning.spec.ts` |
| Panel time settings drawer | `panelTimeSettings` | `v12-panel-time-drawer.json` | `validation/e2e/panel-time-drawer.spec.ts` |
| Switch template variable type | (core) | `v12-switch-variable.json` | `validation/e2e/switch-variable.spec.ts` |
| Redesigned logs panel | (core) | `v12-logs-panel.json` | `validation/e2e/logs-panel.spec.ts` |
| New data sources (SolarWinds, Honeycomb, OpenSearch) | (plugin) | `v12-new-datasources.json` | `validation/e2e/new-datasources.spec.ts` |

## 12.4 (target)

| Feature | Toggle(s) | Demo dashboard | E2E test |
|---|---|---|---|
| Git Sync public preview | `gitSync,provisioning` | `v12-git-sync-pr.json` | `validation/e2e/git-sync-pr.spec.ts` |
| Dynamic dashboards public preview | `kubernetesDashboards,dashboardsNewLayouts` | `v12-dynamic-dashboards-pp.json` | `validation/e2e/dynamic-dashboards-pp.spec.ts` |
| Dashboards from templates | `suggestedDashboards` | `v12-dashboards-from-template.json` | `validation/e2e/template-dashboards.spec.ts` |
| Multi-property variables | `multiVariableProperties` | `v12-multi-property-vars.json` | `validation/e2e/multi-property-vars.spec.ts` |
| Regex transforms on variable values | `templateVariablesRegexTransform` | `v12-regex-variables.json` | `validation/e2e/regex-variables.spec.ts` |
| Smarter visualization suggestions | (core) | `v12-viz-suggestions.json` | `validation/e2e/viz-suggestions.spec.ts` |
| Updated gauge panel | (core) | `v12-gauge.json` | `validation/e2e/gauge.spec.ts` |
| OpenTelemetry log defaults | `otlpLogs` | `v12-otlp-logs.json` | `validation/e2e/otlp-logs.spec.ts` |
| Logs Drilldown default columns configurable | `logsDrilldown` | (reused) | (reused) |
| Zabbix DS enhancements | (plugin) | `v12-zabbix.json` | `validation/e2e/zabbix.spec.ts` |
| Suggested dashboards on empty | `suggestedDashboards` | (reused) | (reused) |
| HA Alertmanager metrics prefix change | (observability) | `unified-alerting-ha.json` (validation) | `validation/e2e/alertmanager-ha-metrics.spec.ts` |

## Canonical feature-toggles block

See [06-feature-toggle-reference.md](06-feature-toggle-reference.md). Canonical block also lives in `helm/values.common.yaml` so the toggle list is a single source of truth.
