# Breaking Changes Matrix — 11.6.4 → 12.4.x

Source: Grafana v12.0/12.1/12.2/12.3/12.4 "What's new" pages. (From 12.0 onward there is no standalone breaking-changes page — what's-new is authoritative.) Remediation is **mandatory** for every row.

| # | Area | Change | Remediation | Script / File |
|---|---|---|---|---|
| 1 | Plugins | AngularJS support fully removed. Core Angular panels force-migrated to React on dashboard load. Non-core Angular plugins do not load. | Run `detect-angular-dashboards`; update plugins to React; manually replace panels without React equivalent; force-save each migrated dashboard via API to persist. Regenerate provisioned JSON at source. | `migration/20_angular_purge.py`, `dashboards/validation/angular-regression-guard.json` |
| 2 | Plugins | Deprecated UI extension APIs removed; reactive extension APIs (11.4+) are the only option. | Rebuild any custom app plugin against `@grafana/runtime` reactive extension API. | `audit/plugin_inventory.py` |
| 3 | Plugins | CLI plugin install compatibility check honors `grafanaDependency` (since 10.2). | Verify every private plugin declares correct `grafanaDependency` in `plugin.json`. | `audit/plugin_inventory.py` |
| 4 | Auth | `editors_can_admin` config option removed (12.0). | Remove from `grafana.ini`. Grant `fixed:teams:writer` via RBAC where still needed. | `provisioning/access-control/teams-writer.yaml` |
| 5 | Auth | Top-level folder creator no longer auto-granted admin (12.3). | Explicit RBAC provisioning grants creator admin where required, or accept new default. | `provisioning/access-control/folder-creator-admin.yaml` |
| 6 | Provisioning | Permissions enforced full-replace (12.3) — anything omitted is removed (except default Admin). | Rewrite every permission file to list complete desired ACL. | `provisioning/access-control/*.yaml` |
| 7 | Alerting | Several legacy single-tenant Alertmanager config endpoints deprecated (12.0), removed in 13.0. | Migrate automation to per-tenant equivalents now. | `migration/50_postflight.sh` |
| 8 | Alerting | HA Alertmanager cluster metrics prefix changed in 12.4. | Update Prometheus scrape + Mimir recording rules + SLO dashboards referencing old prefix. | `observability/prometheus-scrape-config.yaml`, `dashboards/validation/unified-alerting-ha.json` |
| 9 | Traces | `Aggregate by` (Tempo metrics-summary API) removed. | Switch users to Traces Drilldown / TraceQL metrics. | User comms in runbook |
| 10 | Dashboards | Dynamic Dashboards schema v2 migration is **one-way**. | Only flip `kubernetesDashboards` / `dashboardsNewLayouts` after DB backup + JSON export. | `migration/10_backup.sh`, hard-rule guard in `30_schema_upgrade.py` |
| 11 | Metrics | `cache_size` metric deprecated (split into two metrics, removal in 13). | Update internal Grafana-monitoring dashboards. | `dashboards/platform/grafana-self.json` |
| 12 | Auth | Actions tied to legacy API Keys removed (12.3). | Complete API-key → service-account migration before cutover. | `audit/api_key_migration.py` (in `pre_upgrade_audit.py`) |
| 13 | Data sources | UID format enforcement tightened in REST/provisioning paths. | Re-validate every provisioned DS UID (alphanumeric + hyphen, ≤ 40 chars). | `audit/datasource_inventory.py` |
| 14 | Frontend | Scenes-powered dashboard architecture mandatory (flag removed in 13). | Rebuild any custom dashboard-manipulation tooling against Scenes model. | `migration/30_schema_upgrade.py` |

## Gating

`make audit` blocks with NO-GO if any of the rows above still has outstanding remediation.
