# Grafana `11.6.4` → `12.4.3` — Complete Breaking-Changes + Validation Playbook
## For Claude Code — every item is actionable, each has a validator, fix, and pass/fail gate

**Source of truth:** Grafana releases `v12.0.x` → `v12.4.3` (tag `v12.4.3`, released 09 Mar), plus the per-minor "What's new" breaking-change sections (Grafana stopped publishing a dedicated breaking-changes page at v12.0 — the what's-new pages are authoritative).

**Convention for every item below:**
- 🔴 **BREAKING** — will break if ignored
- 🟠 **BEHAVIORAL** — behavior change, may surprise users
- 🟡 **DEPRECATED** — still works in 12.4.3 but removal planned (13.0 kills several)

Every item has:
1. **What breaks**
2. **Detect** (a command / API call Claude Code runs against the live 11.6.4 instance before upgrade)
3. **Fix** (idempotent remediation)
4. **Validate** (post-upgrade assertion — fail the pipeline if not met)

Run order: run §0 env setup once, then every item's **Detect** step during `make audit`, every **Fix** during `make migrate`, every **Validate** during `make validate`.

---

## §0 — Shared environment

```bash
# Set these once; every script below reads them
export GRAFANA_URL_OLD="https://grafana-old.internal"     # 11.6.4
export GRAFANA_URL_NEW="https://grafana.internal"         # 12.4.3 target
export GRAFANA_TOKEN="$(cat ~/.grafana/admin.token)"      # service account token w/ Admin
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export OUT="./out/${RUN_ID}"
mkdir -p "${OUT}"/{audit,fix,validate}

# Helper
gapi() {
  local base="$1"; shift
  curl -fsSL -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
       -H "Accept: application/json" \
       -H "Content-Type: application/json" \
       "${base}$@"
}
```

All scripts `set -euo pipefail`. All output as structured JSON to `${OUT}/...`.

---

# PART A — BREAKING (🔴) — must fix before cutover

## 1. 🔴 AngularJS framework fully removed (12.0)

**What breaks:** Any plugin or core panel built on AngularJS fails to load. Core Angular panels (Graph-old, Table-old, Singlestat, Worldmap) are force-migrated to React on dashboard load, but the migration must be **saved** to persist. Non-core Angular plugins stop loading entirely. The `angular_support_enabled = true` escape hatch from 11.x is gone.

**Detect (against 11.6.4):**
```bash
# 1a — plugin inventory, flag Angular deps
gapi "${GRAFANA_URL_OLD}" /api/plugins \
  | jq '[.[] | select(.angularDetected == true or .signatureType=="unsigned")
         | {id, name, type, angularDetected, info: .info.version}]' \
  > "${OUT}/audit/01-angular-plugins.json"

# 1b — dashboard scan (Grafana Labs official tool)
go install github.com/grafana/detect-angular-dashboards@latest
detect-angular-dashboards -server "${GRAFANA_URL_OLD}" -token "${GRAFANA_TOKEN}" \
  -o json > "${OUT}/audit/01-angular-dashboards.json"

# 1c — core-panel usage (these auto-migrate but you need a save)
for uid in $(gapi "${GRAFANA_URL_OLD}" "/api/search?type=dash-db" | jq -r '.[].uid'); do
  gapi "${GRAFANA_URL_OLD}" "/api/dashboards/uid/${uid}" \
    | jq -r --arg uid "$uid" '
        .dashboard.panels // []
        | .[]
        | select(.type | IN("graph","table-old","singlestat","grafana-worldmap-panel"))
        | "\($uid)\t\(.type)\t\(.title)"' \
    >> "${OUT}/audit/01-core-angular-panels.tsv"
done
```

**Fix:**
```bash
# 2a — update every plugin to latest (many have React versions now)
gapi "${GRAFANA_URL_OLD}" /api/plugins | jq -r '.[].id' \
  | xargs -I{} grafana-cli plugins update {}

# 2b — for plugins with no React version, pick a replacement and rewrite dashboard JSON
python3 migration/20_angular_purge.py \
  --inventory "${OUT}/audit/01-angular-plugins.json" \
  --replacements config/angular-replacements.yaml \
  --out "${OUT}/fix/angular-rewrites/"

# 2c — force-save every core Angular panel dashboard AFTER 12.4.3 cutover
#      (Grafana auto-migrates on load; save is what persists it)
python3 migration/20_angular_purge.py --phase save-migrations \
  --url "${GRAFANA_URL_NEW}"
```

**Validate (post-upgrade):**
```bash
# MUST return 0 — any Angular usage post-cutover is a regression
COUNT=$(gapi "${GRAFANA_URL_NEW}" /api/plugins \
        | jq '[.[] | select(.angularDetected == true)] | length')
[[ "$COUNT" -eq 0 ]] || { echo "FAIL: angular plugins still present: $COUNT"; exit 1; }

# Every previously-flagged dashboard must load without a deprecation banner
python3 validation/dashboard_render_diff.py \
  --dashboards "${OUT}/audit/01-angular-dashboards.json" \
  --url "${GRAFANA_URL_NEW}" \
  --fail-on-banner
```

---

## 2. 🔴 `editors_can_admin` config option removed (12.0)

**What breaks:** Grafana 12 refuses to start if `editors_can_admin` is present OR silently ignores it. Editors who were relying on this to manage Teams lose that capability.

**Detect:**
```bash
# Scan every config source
grep -rn 'editors_can_admin' /etc/grafana helm/ provisioning/ 2>/dev/null \
  | tee "${OUT}/audit/02-editors-can-admin.txt"

# Also check runtime setting
gapi "${GRAFANA_URL_OLD}" /api/admin/settings \
  | jq '.users.editors_can_admin' \
  >> "${OUT}/audit/02-editors-can-admin.txt"
```

**Fix:**
```bash
# Remove from grafana.ini / Helm values
yq -i 'del(.grafana.ini.users.editors_can_admin)' helm/values.common.yaml

# Grant replacement permission via RBAC for users who need it
cat > provisioning/access-control/editors-team-writer.yaml <<'EOF'
apiVersion: 1
roles:
  - name: "custom:editor-team-writer"
    description: "Restores pre-12.0 editor-can-admin on teams"
    version: 1
    global: true
    permissions:
      - action: "teams:read"
      - action: "teams:write"
      - action: "teams:create"
      - action: "teams.permissions:read"
      - action: "teams.permissions:write"
EOF
```

**Validate:**
```bash
# Config must not contain the deprecated key
! gapi "${GRAFANA_URL_NEW}" /api/admin/settings | jq -e '.users.editors_can_admin'

# Users who had the privilege must still be able to write teams via RBAC
gapi "${GRAFANA_URL_NEW}" "/api/access-control/users/permissions/search?action=teams:write" \
  | jq -e 'length > 0'
```

---

## 3. 🔴 Legacy API Keys — actions removed (12.3)

**What breaks:** Roles and actions tied to the old API-key subsystem are gone. Any automation still authenticating with a legacy API key continues to work, but code granting `apikeys:read`/`apikeys:write` fails silently because those actions no longer exist.

**Detect:**
```bash
# List any remaining legacy API keys (not service accounts)
gapi "${GRAFANA_URL_OLD}" /api/auth/keys \
  | jq '[.[] | {id, name, role, expiration}]' \
  > "${OUT}/audit/03-legacy-api-keys.json"

# Find provisioning files referencing removed actions
grep -rnE 'apikeys:(read|write|create|delete)' provisioning/ terraform/ \
  > "${OUT}/audit/03-removed-actions.txt" || true
```

**Fix:**
```bash
# Migrate every legacy key to a Service Account + Token (one-shot UI action in 11.x,
# or scripted via API)
python3 migration/migrate_api_keys_to_sa.py \
  --url "${GRAFANA_URL_OLD}" \
  --inventory "${OUT}/audit/03-legacy-api-keys.json" \
  --out "${OUT}/fix/sa-token-mapping.json"

# Rotate every consumer to the new token BEFORE cutover
# (distribute sa-token-mapping.json to owning teams via Vault)
```

**Validate:**
```bash
# Zero legacy API keys post-migration
[[ "$(gapi "${GRAFANA_URL_NEW}" /api/auth/keys | jq 'length')" -eq 0 ]] \
  || { echo "FAIL: legacy API keys remain"; exit 1; }

# Every service account healthy
gapi "${GRAFANA_URL_NEW}" "/api/serviceaccounts/search?perpage=1000" \
  | jq -e 'all(.serviceAccounts[]; .isDisabled == false)'
```

---

## 4. 🔴 Provisioning enforces full-replace permission model (12.3)

**What breaks:** Any partial permission file that previously **added** to existing permissions now **replaces** them. If your file lists one user, every other user loses access (except the default Admin).

**Detect:**
```bash
# Dump current permissions on every folder/dashboard that is provisioned
for uid in $(gapi "${GRAFANA_URL_OLD}" "/api/folders" | jq -r '.[].uid'); do
  gapi "${GRAFANA_URL_OLD}" "/api/folders/${uid}/permissions" \
    | jq --arg uid "${uid}" '{folder: $uid, perms: .}' \
    >> "${OUT}/audit/04-current-folder-perms.ndjson"
done

# Compare against each provisioning file's permission list — any delta is at-risk
python3 audit/compare_permissions.py \
  --current "${OUT}/audit/04-current-folder-perms.ndjson" \
  --provisioning provisioning/access-control/ \
  --out "${OUT}/audit/04-permission-gap.json"
```

**Fix:**
```bash
# Rewrite every provisioning file to be the COMPLETE desired ACL (not a delta)
python3 migration/rewrite_permissions_full_replace.py \
  --gap "${OUT}/audit/04-permission-gap.json" \
  --in provisioning/access-control/ \
  --out "${OUT}/fix/access-control/"

# Diff & review
diff -ru provisioning/access-control/ "${OUT}/fix/access-control/" | tee "${OUT}/fix/04-acl.diff"
```

**Validate:**
```bash
# Every provisioned resource's live ACL must exactly match the file
python3 validation/permissions_parity.py \
  --url "${GRAFANA_URL_NEW}" \
  --provisioning "${OUT}/fix/access-control/"
```

---

## 5. 🔴 Top-level folder creator no longer auto-admin (12.3)

**What breaks:** In 11.x, whoever created a folder at the root level automatically got Admin on it. In 12.3+, that no longer happens. Users who expected to edit "their" folders may find they can only view.

**Detect:**
```bash
# Inventory who created what top-level folder
gapi "${GRAFANA_URL_OLD}" /api/folders \
  | jq '[.[] | select(.parentUid == null) | {uid, title, createdBy}]' \
  > "${OUT}/audit/05-toplevel-folder-creators.json"
```

**Fix (pick one):**
```bash
# Option A — explicitly grant creator Admin on their folder(s) via provisioning
python3 migration/grant_creator_admin.py \
  --folders "${OUT}/audit/05-toplevel-folder-creators.json" \
  --out provisioning/access-control/creator-admin.yaml

# Option B — accept the new default, communicate to users
echo "12.3+ behavior: creator is NOT auto-admin. Use Admin > Teams > Permissions to grant." \
  > "${OUT}/fix/05-communication.md"
```

**Validate:**
```bash
# After chosen fix, sample users can still edit "their" folders
python3 validation/folder_admin_parity.py \
  --baseline "${OUT}/audit/05-toplevel-folder-creators.json" \
  --url "${GRAFANA_URL_NEW}"
```

---

## 6. 🔴 Dynamic-dashboards schema v2 migration is one-way (12.0, re-emphasized 12.4)

**What breaks:** Once a dashboard is migrated to schema v2 (enabled by `kubernetesDashboards` / `dashboardsNewLayouts` feature toggles), it **cannot be migrated back**. Any rollback to 11.6.4 requires DB restore.

**Detect:**
```bash
# Before flipping any v2 toggle, DB backup must exist
ls -l backup/postgres-${RUN_ID}.dump 2>/dev/null || {
  echo "BLOCKER: no DB backup; run 10_backup.sh first"; exit 1; }

# Capture schemaVersion distribution
for uid in $(gapi "${GRAFANA_URL_OLD}" "/api/search?type=dash-db" | jq -r '.[].uid'); do
  gapi "${GRAFANA_URL_OLD}" "/api/dashboards/uid/${uid}" \
    | jq -r '[.dashboard.uid, .dashboard.schemaVersion] | @tsv'
done > "${OUT}/audit/06-schema-versions.tsv"

awk '{v[$2]++} END {for (k in v) print k, v[k]}' "${OUT}/audit/06-schema-versions.tsv" \
  > "${OUT}/audit/06-schema-hist.txt"
```

**Fix:**
```bash
# MANDATORY guardrail in 40_helm_upgrade.sh — refuse to enable v2 toggles
# without a same-run DB backup
bash <<'GUARD'
if grep -qE 'dashboardsNewLayouts|kubernetesDashboards' helm/values.common.yaml; then
  find backup/ -name "postgres-${RUN_ID}.dump" -mmin -30 -size +1M \
    || { echo "REFUSING: v2 toggle enabled without fresh backup"; exit 1; }
fi
GUARD

# Export every dashboard's JSON pre-flip (redundant safety net)
mkdir -p "${OUT}/fix/dashboards-pre-v2/"
for uid in $(gapi "${GRAFANA_URL_OLD}" "/api/search?type=dash-db" | jq -r '.[].uid'); do
  gapi "${GRAFANA_URL_OLD}" "/api/dashboards/uid/${uid}" \
    > "${OUT}/fix/dashboards-pre-v2/${uid}.json"
done
```

**Validate:**
```bash
# Post-cutover, every pre-v2 dashboard still renders (pixel-diff ≤ 2%)
python3 validation/dashboard_render_diff.py \
  --baseline "${OUT}/fix/dashboards-pre-v2/" \
  --url "${GRAFANA_URL_NEW}" \
  --max-diff-pct 2.0
```

---

## 7. 🔴 Old UI extension APIs removed (12.0)

**What breaks:** Deprecated UI extension APIs are gone; only the reactive APIs introduced in Grafana 11.4 work. Custom app plugins that haven't migrated will fail to register UI extensions.

**Detect:**
```bash
# Find any private app plugin using old extension API
grep -rnE 'registerExtension|ExtensionsRegistry\.register' \
  <custom-plugin-repos>/src/ \
  > "${OUT}/audit/07-old-extension-api.txt" || true
```

**Fix:**
```bash
# For each affected plugin, migrate to @grafana/runtime reactive APIs.
# Run the official codemod:
for plugin_dir in plugins/custom/*/; do
  (cd "$plugin_dir" && npx @grafana/create-plugin@latest migrate)
done
```

**Validate:**
```bash
# No plugin load errors post-upgrade
gapi "${GRAFANA_URL_NEW}" /api/plugins/errors \
  | jq -e 'length == 0' \
  || { echo "FAIL: plugin load errors"; exit 1; }
```

---

## 8. 🔴 Plugin CLI `grafanaDependency` enforcement (12.0)

**What breaks:** Since v10.2 the compatibility endpoint changed and `grafanaDependency` in `plugin.json` was ignored — some plugins ended up installed on incompatible Grafana versions. 12 re-enforces the check, so `grafana-cli plugins install` now refuses incompatible plugins.

**Detect:**
```bash
# Audit plugin.json files in any vendored/private plugins
find plugins/custom -name "plugin.json" -exec \
  jq -r '"\(.id) requires \(.dependencies.grafanaDependency)"' {} \; \
  > "${OUT}/audit/08-plugin-deps.txt"
```

**Fix:**
```bash
# Update each plugin.json to declare a valid 12.4.3-compatible range
# Example: ">=11.0.0 <13.0.0"
python3 migration/fix_plugin_dependency.py \
  --target "12.4.3" \
  --root plugins/custom/
```

**Validate:**
```bash
# CLI install must succeed for every custom plugin
for p in $(ls plugins/custom); do
  grafana-cli --pluginsDir plugins/custom plugins install "${p}" || exit 1
done
```

---

## 9. 🔴 Data source UID format enforcement tightened (12.0)

**What breaks:** REST and provisioning paths now strictly enforce the UID format: alphanumeric + `-` + `_`, length ≤ 40. Older provisioning files with spaces, dots, or long UIDs get rejected.

**Detect:**
```bash
gapi "${GRAFANA_URL_OLD}" /api/datasources \
  | jq -r '.[] | select(.uid | test("^[a-zA-Z0-9_-]{1,40}$") | not) | .uid' \
  > "${OUT}/audit/09-bad-uids.txt"

grep -rEn 'uid:.*["'\'']?[^a-zA-Z0-9_-]' provisioning/datasources/ \
  >> "${OUT}/audit/09-bad-uids.txt" || true
```

**Fix:**
```bash
# Map each bad UID to a conformant one; rewrite every panel's datasource reference
python3 migration/rewrite_bad_uids.py \
  --bad-uids "${OUT}/audit/09-bad-uids.txt" \
  --provisioning provisioning/ \
  --dashboards "${OUT}/fix/dashboards-pre-v2/" \
  --mapping "${OUT}/fix/09-uid-mapping.json"
```

**Validate:**
```bash
gapi "${GRAFANA_URL_NEW}" /api/datasources \
  | jq -e 'all(.[]; .uid | test("^[a-zA-Z0-9_-]{1,40}$"))'
```

---

## 10. 🔴 Tempo — `Aggregate by` / metrics-summary API removed (12.0)

**What breaks:** The Aggregate-by UI and `/api/metrics/summary` endpoint are gone. Dashboards using these show broken panels; users must switch to Traces Drilldown + TraceQL metrics.

**Detect:**
```bash
# Find panels using the old metrics-summary via Tempo DS
python3 audit/find_tempo_aggregate_by.py \
  --dashboards "${OUT}/fix/dashboards-pre-v2/" \
  > "${OUT}/audit/10-tempo-aggregate-panels.json"
```

**Fix:**
```bash
# Rewrite each panel to use TraceQL metrics (`{ } | rate()`)
python3 migration/rewrite_tempo_metrics.py \
  --panels "${OUT}/audit/10-tempo-aggregate-panels.json" \
  --out "${OUT}/fix/dashboards-tempo-fixed/"
```

**Validate:**
```bash
# No panel uses the removed metrics-summary API
! grep -rn 'metrics/summary' "${OUT}/fix/dashboards-tempo-fixed/"
```

---

## 11. 🔴 HA Alertmanager cluster metrics prefix changed (12.4)

**What breaks:** The metric name prefix for HA Alertmanager cluster metrics changed in 12.4 (PR #121481). Any Mimir recording rules, Prometheus alert rules, or self-monitoring dashboards referencing the old prefix silently drop to zero.

**Detect:**
```bash
# Scan every dashboard and rule file for the old prefix
grep -rnE 'alertmanager_cluster_[a-z_]+|alertmanager_peer_' \
  dashboards/ provisioning/alerting/ observability/ \
  > "${OUT}/audit/11-old-am-metrics.txt" || true

# And any Mimir recording rules pushed to your Mimir
curl -s "${MIMIR_URL}/prometheus/config/v1/rules" \
  | yq -o=json | jq -r '..|.query?//empty' \
  | grep -E 'alertmanager_(cluster|peer)_' \
  >> "${OUT}/audit/11-old-am-metrics.txt" || true
```

**Fix:**
```bash
# Confirm the new prefix against a live 12.4.3 instance
gapi "${GRAFANA_URL_NEW}" /metrics \
  | grep -E 'alertmanager_(cluster|peer)' \
  > "${OUT}/fix/11-new-am-metrics.txt"

# Generate a sed mapping and apply
python3 migration/rewrite_am_metric_prefix.py \
  --old "${OUT}/audit/11-old-am-metrics.txt" \
  --new "${OUT}/fix/11-new-am-metrics.txt" \
  --apply-to dashboards/ provisioning/alerting/ observability/
```

**Validate:**
```bash
# New metrics must be present and non-zero
gapi "${GRAFANA_URL_NEW}" /metrics \
  | awk '/^alertmanager_cluster_members/ {print $2}' \
  | grep -qE '^[1-9]' \
  || { echo "FAIL: HA Alertmanager metrics not reporting"; exit 1; }
```

---

## 12. 🔴 Scenes-powered dashboard architecture mandatory (12.0, hard-locked in 13.0)

**What breaks:** The feature flag to disable Scenes is gone in 13 and effectively mandatory in 12. Any custom tooling that manipulated dashboards through the pre-Scenes DOM/state model breaks.

**Detect:**
```bash
# Identify custom scripts/tests that hit non-Scenes DOM selectors
grep -rnE 'data-panelid=|panel-container|getPanelCtrl' \
  validation/ ci/ tests/ \
  > "${OUT}/audit/12-pre-scenes-selectors.txt" || true
```

**Fix:**
```bash
# Rewrite selectors against Scenes test-IDs
# Reference: https://github.com/grafana/scenes
python3 migration/rewrite_scenes_selectors.py --root validation/
```

**Validate:**
```bash
# Every validation k6 / Playwright script passes against 12.4.3
npx playwright test --config validation/playwright.config.ts
```

---

# PART B — BEHAVIORAL (🟠) — will not break start-up, but users will notice

## 13. 🟠 Google OAuth HD parameter validation added (12.1)

**What changes:** Grafana now validates the Google `hd` (hosted-domain) claim against `allowed_domains`. Mismatched tokens are rejected — if your Google OAuth uses the legacy `api_url` flow, it may lack `hd` entirely and users will be denied.

**Detect:**
```bash
grep -nE 'api_url|allowed_domains' helm/ provisioning/ grafana.ini 2>/dev/null \
  > "${OUT}/audit/13-google-oauth.txt"
```

**Fix:**
```ini
# Switch to the modern Google OAuth flow and list allowed domains explicitly
[auth.google]
enabled = true
scopes = openid email profile
# Remove api_url; use the auto-discovery flow
allowed_domains = yourcompany.com other.com
```

**Validate:**
```bash
# Log in with a user from allowed_domains + one from outside — first succeeds, second 403s
python3 validation/oauth_smoke.py --url "${GRAFANA_URL_NEW}"
```

---

## 14. 🟠 Table visualization refactored to `react-data-grid` (GA in 12.2)

**What changes:** Faster loads, different default column widths, changed cell rendering (cell types, links, footer positioning). Dashboards may look different even though functionally equivalent.

**Detect:**
```bash
# Count table panels for diff coverage
python3 audit/count_panel_types.py \
  --dashboards "${OUT}/fix/dashboards-pre-v2/" \
  --filter table \
  > "${OUT}/audit/14-table-panels.json"
```

**Fix:**
```bash
# No fix required — regression test with pixel-diff on top-N table dashboards
python3 validation/dashboard_render_diff.py \
  --panels "${OUT}/audit/14-table-panels.json" \
  --max-diff-pct 5.0 \
  --url-old "${GRAFANA_URL_OLD}" \
  --url-new "${GRAFANA_URL_NEW}"
```

**Validate:**
Pixel-diff ≤ 5% on top-25 most-viewed table dashboards. Any regressions → file a rewrite PR via Git Sync.

---

## 15. 🟠 `cache_size` metric deprecated → split into two (12.0, removed in 13.0)

**What changes:** The duplicated `cache_size` metric is now reported as two metrics. Your Grafana self-monitoring dashboards break silently.

**Detect:**
```bash
grep -rn 'cache_size' observability/ dashboards/ \
  > "${OUT}/audit/15-cache-size.txt" || true
```

**Fix:**
```bash
# Find replacement metric names on the running 12.4.3 instance
gapi "${GRAFANA_URL_NEW}" /metrics | grep -iE '^grafana.*cache'

# Update panels — typical mapping is grafana_cache_gets_total /
# grafana_cache_usage_bytes (confirm against /metrics output)
python3 migration/rewrite_cache_size_metric.py \
  --hits "${OUT}/audit/15-cache-size.txt" \
  --apply-to dashboards/ observability/
```

**Validate:**
```bash
# New metric names present & non-empty
gapi "${GRAFANA_URL_NEW}" /metrics | grep -q 'grafana_cache_gets_total'
```

---

## 16. 🟠 Legacy single-tenant Alertmanager config API endpoints deprecated (12.0, removed 13.0)

**What changes:** Several `/api/alertmanager/grafana/...` single-tenant config endpoints are deprecated; 13.0 removes or restricts them. Automation should migrate **now**.

**Detect:**
```bash
# Grep your automation for affected endpoints
grep -rnE '/api/alertmanager/grafana/(api/v[12]/alerts|config|silences)' \
  terraform/ ci/ scripts/ \
  > "${OUT}/audit/16-deprecated-am-endpoints.txt" || true
```

**Fix:**
```bash
# Migrate each call to the per-tenant or provisioning equivalent
# Reference: https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/
python3 migration/rewrite_am_endpoints.py \
  --hits "${OUT}/audit/16-deprecated-am-endpoints.txt"
```

**Validate:**
```bash
# Every rewritten call exits 0 against 12.4.3
bash ci/replay-am-calls.sh "${GRAFANA_URL_NEW}"
```

---

## 17. 🟠 Short URLs now persistent (12.4 storage migration)

**What changes:** Short URLs used to be ephemeral; 12.4 persists them via a storage migration on first start. First start of 12.4.x takes longer and writes to the unified storage backend.

**Detect:**
```bash
# Count existing short URLs (SQL) — sets your migration window expectation
psql "${POSTGRES_DSN}" -c "SELECT count(*) FROM short_url;" \
  > "${OUT}/audit/17-short-url-count.txt"
```

**Fix:** Nothing to do — but budget extra 2–5 min per 100k rows for the first-boot migration. Monitor `grafana_database_conn_*` metrics during rollout.

**Validate:**
```bash
# First pod ready within SLA
kubectl -n grafana rollout status sts/grafana --timeout=15m

# And existing short-URL IDs still resolve
curl -fsSL -o /dev/null -w '%{http_code}\n' "${GRAFANA_URL_NEW}/goto/<sample-id>"
# Expect 302 → dashboard
```

---

## 18. 🟠 Datagrid visualization deprecated (12.4, removed in 13.0)

**What changes:** The experimental Datagrid panel is deprecated. Existing panels still work in 12.4 but cannot be newly created; removal is scheduled for 13.0.

**Detect:**
```bash
python3 audit/find_panel_type.py \
  --type datagrid \
  --dashboards "${OUT}/fix/dashboards-pre-v2/" \
  > "${OUT}/audit/18-datagrid-panels.json"
```

**Fix:**
```bash
# Migrate Datagrid → Table (react-data-grid) proactively
python3 migration/rewrite_datagrid_to_table.py \
  --panels "${OUT}/audit/18-datagrid-panels.json"
```

**Validate:**
```bash
# Zero Datagrid panels remaining
[[ "$(jq 'length' "${OUT}/audit/18-datagrid-panels.json")" -eq 0 ]]
```

---

## 19. 🟠 Visualization Suggestions are now the default panel picker (12.4)

**What changes:** The Visualization Suggestions replace the classic panel-type grid as the default selection UI. Cosmetic, but user-facing — announce it.

**Detect / Fix:** N/A (UX change only).

**Validate:** Include a screenshot in the post-migration comms.

---

## 20. 🟠 Gauge panel redesign — new `Style` option (12.4)

**What changes:** The gauge now has Circular and Arc `Style` variants. Existing gauges pick the closest match automatically but thresholds and label positions may shift slightly.

**Detect:**
```bash
python3 audit/find_panel_type.py \
  --type gauge \
  --dashboards "${OUT}/fix/dashboards-pre-v2/" \
  > "${OUT}/audit/20-gauge-panels.json"
```

**Validate:**
```bash
# Pixel-diff each gauge
python3 validation/dashboard_render_diff.py \
  --panels "${OUT}/audit/20-gauge-panels.json" \
  --max-diff-pct 10.0
```

---

## 21. 🟠 Correlations: `org_id=0` support removed (backported to 12.0.x / 12.1.x / 12.2.x / 12.3.x)

**What changes:** Correlations API no longer accepts `org_id=0` as a wildcard. Any automation creating correlations with `org_id=0` fails post-upgrade.

**Detect:**
```bash
grep -rn '"org_id":\s*0\|org_id=0' terraform/ ci/ \
  > "${OUT}/audit/21-correlations-org-zero.txt" || true
```

**Fix:**
```bash
# Replace with the actual org ID (usually 1 for single-tenant OSS)
sed -i 's/"org_id":\s*0/"org_id": 1/g' <files>
```

**Validate:**
```bash
gapi "${GRAFANA_URL_NEW}" /api/datasources/correlations \
  | jq -e 'all(.correlations[]; .orgId != 0)'
```

---

## 22. 🟠 Public dashboard annotations — time-range behavior hardened (security fix, backported)

**What changes:** When a public dashboard has time selection disabled, annotations now strictly use the dashboard's configured time range. Public dashboards that relied on wider annotation ranges show fewer annotations.

**Detect:**
```bash
gapi "${GRAFANA_URL_OLD}" /api/dashboards/public-dashboards \
  | jq '[.[] | select(.timeSelectionEnabled == false) | .dashboardUid]' \
  > "${OUT}/audit/22-public-dash-no-time-select.json"
```

**Validate:** Post-cutover, review those public dashboards — if the annotation count drops unexpectedly, re-enable time selection.

---

## 23. 🟠 TraceView HTML sanitized (security fix, backported)

**What changes:** Span `attributes`/`events` no longer render raw HTML — they are sanitized. Tooling that embedded HTML in span attributes to render as clickable content stops rendering styled.

**Detect:**
```bash
# Look for span-attribute HTML usage in your trace producers
grep -rnE '<a href=|<img src=' <your-instrumentation-repos>/ \
  > "${OUT}/audit/23-html-in-spans.txt" || true
```

**Fix:** Replace HTML-in-spans with Grafana's span-link configuration on the Tempo data source.

---

# PART C — DEPRECATIONS (🟡) — removed in 13.0; fix now to avoid a forced rush

## 24. 🟡 `/api` path deprecated in favor of `/apis` (warned in 12; removed path-by-path in 13)

**Action:** Migrate all automation that hits `/api/dashboards/...`, `/api/folders/...` to the new `/apis/dashboard.grafana.app/...` and `/apis/folder.grafana.app/...` namespaced endpoints. These coexist in 12.4.3.

```bash
grep -rnE 'https?://[^ ]+/api/(dashboards|folders|datasources)' \
  terraform/ ci/ scripts/ > "${OUT}/audit/24-api-path.txt"
```

---

## 25. 🟡 Numeric data source `id` APIs (deprecated since 9.0, disabled by default in 13.0)

**Action:** Every API call that references a data source by numeric `id` must switch to `uid`.

```bash
grep -rnE '/api/datasources/[0-9]+(/|"|\s)' terraform/ ci/ scripts/
```

---

## 26. 🟡 React-Router v5 deprecation (marked in v11; expect removal)

**Action:** Any custom app plugin still on `react-router` v5 must migrate to v6 before 13. See Grafana plugin developer portal migration guide.

---

## 27. 🟡 `grafana/e2e` (Cypress) deprecated → `grafana/plugin-e2e` (Playwright)

**Action:** Migrate any plugin e2e suite to `@grafana/plugin-e2e`.

---

## 28. 🟡 `ArrayVector` / `Vector` interfaces deprecated

**Action:** Remove `ArrayVector` usage in custom plugins; use plain arrays. Build-time TS errors appear in 12; runtime still works but is slated for removal.

---

# PART D — ONE-SHOT POST-CUTOVER FIXES (must run on the new 12.4.3 instance)

## 29. 🔴 Force-save every auto-migrated Angular dashboard (12.0+)

**Why:** Grafana auto-migrates Angular core panels to React on load, but the migration is only persisted when the dashboard is **saved**. Unsaved dashboards re-migrate every load (slow) and appear unchanged in Git Sync diffs.

```bash
python3 migration/force_save_all_dashboards.py \
  --url "${GRAFANA_URL_NEW}" \
  --only-if-angular-pre \
  --inventory "${OUT}/audit/01-core-angular-panels.tsv"
```

**Validate:** No dashboard shows a "This dashboard uses Angular plugins" banner.

---

## 30. 🔴 Enable all v12 feature toggles and verify each is `active`

```ini
[feature_toggles]
enable = provisioning,kubernetesDashboards,dashboardsNewLayouts,dashboardScene,grafanaManagedRecordingRules,sqlExpressions,regressionTransformation,adhocFiltersNew,logsPanelControls,panelTimeSettings,gitSync,templateVariablesRegexTransform,multiVariableProperties,suggestedDashboards,otlpLogs,metricsDrilldown,logsDrilldown,tracesDrilldown,profilesDrilldown
```

**Validate:**
```bash
REQUIRED=(provisioning kubernetesDashboards dashboardsNewLayouts dashboardScene \
  grafanaManagedRecordingRules sqlExpressions regressionTransformation \
  adhocFiltersNew logsPanelControls panelTimeSettings gitSync \
  templateVariablesRegexTransform multiVariableProperties suggestedDashboards \
  otlpLogs metricsDrilldown logsDrilldown tracesDrilldown profilesDrilldown)

for tog in "${REQUIRED[@]}"; do
  gapi "${GRAFANA_URL_NEW}" /api/featuremgmt \
    | jq -e --arg t "$tog" 'any(.features[]; .name == $t and .enabled == true)' \
    || { echo "FAIL: toggle $tog not enabled"; exit 1; }
done
```

---

# PART E — CONSOLIDATED GO/NO-GO GATE

All 30 items above roll up into this single gate. Claude Code runs `make validate` which executes:

```bash
python3 validation/gate.py \
  --audit-dir "${OUT}/audit" \
  --fix-dir   "${OUT}/fix" \
  --url       "${GRAFANA_URL_NEW}" \
  --report    "${OUT}/validate/go-no-go.html"
```

Gate emits pass/fail per row. **All 🔴 must be pass; 🟠 may warn; 🟡 informational.**

| # | Item | Severity | Gate |
|---|---|---|---|
| 1 | AngularJS removed — plugin count 0 | 🔴 | MUST |
| 2 | `editors_can_admin` removed | 🔴 | MUST |
| 3 | Legacy API keys migrated to SA | 🔴 | MUST |
| 4 | Provisioning full-replace ACL parity | 🔴 | MUST |
| 5 | Top-level folder creator admin preserved | 🔴 | MUST |
| 6 | DB backup exists before v2 schema flip | 🔴 | MUST |
| 7 | Plugin UI extension APIs migrated | 🔴 | MUST |
| 8 | Plugin `grafanaDependency` valid | 🔴 | MUST |
| 9 | Data source UIDs conformant | 🔴 | MUST |
| 10 | Tempo `Aggregate by` panels rewritten | 🔴 | MUST |
| 11 | HA Alertmanager metric prefix updated | 🔴 | MUST |
| 12 | Scenes-based selectors in tests | 🔴 | MUST |
| 13 | Google OAuth `hd`/`allowed_domains` | 🟠 | SHOULD |
| 14 | Table (react-data-grid) pixel-diff ≤ 5% | 🟠 | SHOULD |
| 15 | `cache_size` replaced in self-monitoring | 🟠 | SHOULD |
| 16 | Legacy AM endpoints rewritten | 🟠 | SHOULD |
| 17 | Short-URL migration completes in SLA | 🟠 | SHOULD |
| 18 | Datagrid panels rewritten to Table | 🟠 | SHOULD |
| 19 | Visualization Suggestions UX comms sent | 🟠 | SHOULD |
| 20 | Gauge pixel-diff ≤ 10% | 🟠 | SHOULD |
| 21 | Correlations `org_id=0` fixed | 🟠 | SHOULD |
| 22 | Public dashboard annotations review | 🟠 | SHOULD |
| 23 | TraceView HTML-in-spans addressed | 🟠 | SHOULD |
| 24 | `/api` → `/apis` migration started | 🟡 | INFO |
| 25 | Numeric DS `id` → `uid` migration | 🟡 | INFO |
| 26 | react-router v6 migration | 🟡 | INFO |
| 27 | `@grafana/plugin-e2e` migration | 🟡 | INFO |
| 28 | `ArrayVector` removed | 🟡 | INFO |
| 29 | Every Angular dash force-saved | 🔴 | MUST |
| 30 | All v12 feature toggles `enabled=true` | 🔴 | MUST |

---

# PART F — How Claude Code should execute this

Drop this file into the repo as `docs/01-breaking-changes-matrix.md` (referenced from §4 of the master prompt). Then:

1. **`/init`** — Claude Code reads this file plus the master prompt, scaffolds the scripts listed (`audit/*.py`, `migration/*.py`, `validation/*.py`) as stubs.
2. **`make audit`** — Claude Code runs every **Detect** block in this file in order, emitting `${OUT}/audit/*` artifacts and a summary `${OUT}/audit/report.md` with a BLOCKER count.
3. **`make migrate`** — Claude Code runs every **Fix** block in order, gated by `CONFIRM=yes` and the presence of a ≤ 30-min-old DB backup.
4. **`make validate`** — Claude Code runs every **Validate** block, emits `${OUT}/validate/go-no-go.html`, exit 0 iff every 🔴 row passes.
5. **`make report`** — Claude Code renders the HTML gate report plus a CSV for stakeholders.

Every Python stub Claude Code creates must:
- Be ≥ 3.11, typed (`from __future__ import annotations`, `typing`), use `rich` for progress.
- Write structured JSON logs: `{"ts","run_id","severity","item","detect|fix|validate","status","detail"}`.
- Be idempotent.
- Refuse to do destructive operations without `CONFIRM=yes`.
- Pin every dep in `pyproject.toml`.

---

**Canonical sources (Claude Code: re-fetch these at audit time to catch any late-breaking patch-level notices)**

- Releases index: `https://github.com/grafana/grafana/releases`
- `v12.4.3` tag: `https://github.com/grafana/grafana/releases/tag/v12.4.3`
- Full changelog: `https://raw.githubusercontent.com/grafana/grafana/main/CHANGELOG.md`
- What's new 12.0: `https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-0/`
- What's new 12.1: `https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-1/`
- What's new 12.2: `https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-2/`
- What's new 12.3: `https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-3/`
- What's new 12.4: `https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-4/`
- Upgrade guide 12.4: `https://grafana.com/docs/grafana/latest/upgrade-guide/upgrade-v12.4/`

**End of document.**
