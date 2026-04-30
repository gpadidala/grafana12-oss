# grafana12-oss

Everything you need to migrate Grafana OSS from **11.6.4 to 12.4.3** — the production runbook plus a self-contained Docker Compose lab with 34 dashboards, LGTM + exporters wired end-to-end, and a 30-item breaking-change gate you can run against your real instance.

Repo split:

| Path | What it's for |
|---|---|
| [`lab/`](lab/) | Local Docker Compose stack · **run this to try everything** |
| [`helm/`](helm/) · [`terraform/`](terraform/) · [`provisioning/`](provisioning/) · [`migration/`](migration/) · [`audit/`](audit/) · [`validation/`](validation/) | Production migration toolkit for AKS + GKE |
| [`docs/`](docs/) | Playbooks — the canonical 30-item breaking-changes matrix lives here |
| [`ci/`](ci/) | GitHub Actions + Jenkins pipelines for `audit` / `validate` / Git Sync PR checks |

---

## 1. Quick start — run with `docker compose` (no `make` needed)

Prereqs: **Docker Desktop** running. That's it.

### Three rules that make it work every time

1. **`cd` into the `lab/` directory** — NOT `lab/compose/`. The `.env` file lives in `lab/` and compose looks there.
2. **Create `.env` before the first run** — it's gitignored; only `.env.example` ships with the repo.
3. **Pass `--env-file .env -f compose/docker-compose.yml`** to `docker compose` explicitly so the path isn't ambiguous.

### Exact commands

#### macOS / Linux

```bash
cd lab
cp .env.example .env    # first time only
docker compose --env-file .env -f compose/docker-compose.yml -p grafana12-oss-lab up -d --build
```

#### Windows (PowerShell)

```powershell
cd lab
Copy-Item .env.example .env     # first time only
docker compose --env-file .env -f compose/docker-compose.yml -p grafana12-oss-lab up -d --build
```

#### Legacy `docker-compose` v1 (hyphenated, still works)

```bash
cd lab
docker-compose --env-file .env -f compose/docker-compose.yml -p grafana12-oss-lab up -d --build
```

**Do not run from `lab/compose/`** — that's the `unable to get image 'grafana12-oss-lab/prometheus:': invalid reference format` error. `docker compose` v1 only reads `.env` from the current directory, so image-tag substitution comes up blank if you're in the wrong folder.

### Verify

```bash
docker compose -f compose/docker-compose.yml -p grafana12-oss-lab ps
curl http://localhost:3012/api/health
```

Open **http://localhost:3012** — lands on the *v12 Upgrade Overview* (anonymous Admin, no login).

### Common commands

| Action | Command (run from `lab/`) |
|---|---|
| Stop, keep volumes | `docker compose -f compose/docker-compose.yml -p grafana12-oss-lab down` |
| Nuke + reset volumes | `docker compose -f compose/docker-compose.yml -p grafana12-oss-lab down -v` |
| Tail Grafana logs | `docker compose -f compose/docker-compose.yml -p grafana12-oss-lab logs -f grafana` |
| Rebuild after changing dashboards/configs | `docker compose --env-file .env -f compose/docker-compose.yml -p grafana12-oss-lab build --no-cache grafana && docker compose --env-file .env -f compose/docker-compose.yml -p grafana12-oss-lab up -d --force-recreate grafana` |

### Shortcut helpers (optional)

- `make up` / `make down` / `make status` (macOS / Linux) — same commands wrapped
- `.\setup.ps1` (Windows) — bootstraps `.env` and runs `docker compose` for you
- `./setup.sh` (macOS / Linux) — same as setup.ps1

The compose file has built-in defaults for every image tag — `${POSTGRES_TAG:-16-alpine}`, `${GRAFANA_IMAGE_TAG:-12.4.3}`, etc. — so even if `.env` is missing the build won't fail with blank tags. Only the Grafana admin password + secret key need to come from `.env`.

---

## 2. What you get — 34 live dashboards, all v12-themed

Every dashboard is hand-built and has **real queries against live lab data**. Nothing is an empty stub.

### 🎤 Enterprise presentation (share these with leadership)

| | Dashboard |
|---|---|
| ✨ | [**Grafana 12 — What's New**](http://localhost:3012/d/v12-enterprise-whats-new) — slide-deck-quality feature tour, card grids grouped by theme |
| ⚠️ | [**Deprecations & Breaking Changes**](http://localhost:3012/d/v12-enterprise-deprecations) — risk + mitigation story with removal timeline |

### 🛡 Admin dashboards (for the cutover)

| | Dashboard |
|---|---|
| 🔴 | [Pre / Post Upgrade Comparison](http://localhost:3012/d/v12-admin-prepost) — 11.6.4 baseline vs 12.4.3 live with add/remove diffs |
| 🔴 | [Migration Readiness Scorecard](http://localhost:3012/d/v12-admin-readiness) — single-pane GO/NO-GO |
| 🔴 | [Breaking Changes Tracker](http://localhost:3012/d/v12-admin-bct) — all 30 playbook items visualized |
| 🔴 | [Angular & Plugin Deep Audit](http://localhost:3012/d/v12-admin-angular) |
| 🔴 | [Dashboard Schema & Scenes Migration](http://localhost:3012/d/v12-admin-schema) |
| 🔴 | [Deprecated UI Panel Inventory](http://localhost:3012/d/v12-admin-deprecated-panels) |
| 🔴 | [Deprecated API / Endpoint Scanner](http://localhost:3012/d/v12-admin-endpoints) |
| 🔴 | [Cutover Observability](http://localhost:3012/d/v12-admin-cutover) |

### 🎯 v12.0 – v12.4 feature demos (24)

| 12.0 | 12.1 | 12.2 | 12.3 | 12.4 |
|---|---|---|---|---|
| [Drilldown Suite](http://localhost:3012/d/v12-0-drilldown) | [Regression Transform](http://localhost:3012/d/v12-1-regression) | [Ad-hoc Filters](http://localhost:3012/d/v12-2-adhoc) | [Panel Time Drawer](http://localhost:3012/d/v12-3-time-drawer) | [Multi-property Variables](http://localhost:3012/d/v12-4-multiprop) |
| [React Data Grid](http://localhost:3012/d/v12-0-table) | [Visualization Actions](http://localhost:3012/d/v12-1-viz-actions) | [Logs JSON Viewer](http://localhost:3012/d/v12-2-logs-json) | [Switch Variable](http://localhost:3012/d/v12-3-switch-var) | [Regex Variable Transforms](http://localhost:3012/d/v12-4-regex-vars) |
| [SQL Expressions](http://localhost:3012/d/v12-0-sql-expr) | [New Alert Rule Page](http://localhost:3012/d/v12-1-alert-rule-page) | | [Redesigned Logs Panel](http://localhost:3012/d/v12-3-logs-panel) | [Gauge Styles](http://localhost:3012/d/v12-4-gauge) |
| [Recording Rules](http://localhost:3012/d/v12-0-recording-rules) | [Grafana Advisor](http://localhost:3012/d/v12-1-advisor) | | | [OTLP Log Defaults](http://localhost:3012/d/v12-4-otlp) |
| [Scenes Chained Vars](http://localhost:3012/d/v12-0-scenes-vars) | | | | [HA Alertmanager](http://localhost:3012/d/v12-4-am-ha) |
| [Git Sync](http://localhost:3012/d/v12-0-git-sync) | | | | [Traces Drilldown](http://localhost:3012/d/v12-4-traces-dd) |
| | | | | [Profiles + Flame Graph](http://localhost:3012/d/v12-4-profiles-dd) |
| | | | | [Dynamic Dashboards](http://localhost:3012/d/v12-4-dynamic) |

Run `make dashboards` in `lab/` to print every URL grouped by tag.

---

## 3. Lab architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  localhost:3012   Grafana 12.4.3 (grafana-oss)                               │
│                   ├─ 3 plugins preinstalled: Infinity DS / Polystat / Clock  │
│                   ├─ 5 datasources provisioned                                │
│                   └─ 34 dashboards in one folder                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  localhost:9092   Prometheus v2.55.0      scrapes grafana, loki, tempo,      │
│                                            pyroscope, alloy, node, cadvisor, │
│                                            postgres_exporter                  │
│  localhost:3112   Loki 3.3.0              Docker container logs (via Alloy)  │
│  localhost:3212   Tempo 2.6.0             OTLP receivers on 4317/4318        │
│  localhost:4042   Pyroscope 1.8.0         self-profiling source              │
│  localhost:12346  Alloy v1.6.0            ships docker logs → Loki, metrics  │
│                                            → Prometheus, traces → Tempo      │
├──────────────────────────────────────────────────────────────────────────────┤
│  (internal)       Postgres 16-alpine      grafana backend store              │
│  (internal)       Image Renderer 3.12.0   separate service (not core plugin) │
│  (internal)       node_exporter v1.8.2    host-ish metrics for dashboards    │
│  (internal)       cAdvisor v0.49.1        per-container resource metrics     │
│  (internal)       postgres_exporter 0.16  pg_up, pg_stat_*                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

**11 containers**, all pinned to exact versions. Ports are shifted off the defaults to coexist peacefully with a grafana13-lab or any existing stack on `:3000 / :9090 / :3100 / :3200 / :4040 / :4317-8`.

All service configs (Prometheus rules, Loki schema, Tempo layout, Alloy pipeline, Grafana provisioning, dashboards) are **baked into each service's Dockerfile** — not bind-mounted. That's what sidesteps the Docker Desktop `/Volumes/` file-sharing issue on macOS.

---

## 4. Make targets

### `lab/Makefile` — local lab

```bash
make up         # idempotent bring-up (auto-creates .env; waits for /api/health)
make down       # stop (preserve volumes)
make reset      # nuke everything including volumes
make restart    # restart Grafana only
make build      # build local images with --pull
make pull       # pull pre-built base images
make logs       # tail Grafana logs
make status     # container status + all URLs
make health     # /api/health assert
make ds         # per-DS /health probe
make toggles    # §5.6 feature toggle verification
make dashboards # print every dashboard URL grouped by tag
make verify     # health + ds + toggles rollup
make office     # alias for `up` (intent-named for office network runs)
make help       # self-documenting target list
```

### Root `Makefile` — production migration toolkit

```bash
make audit              # §3 pre-upgrade audit → out/audit-<ts>/ (GO/NO-GO)
make migrate CONFIRM=yes  # §9 cutover runbook (helm upgrade)
make validate           # §8 + §11 validation + 30-item go-no-go.html
make e2e                # Playwright + k6-browser end-to-end harness
make feature-toggles-verify  # assert every §5.6 toggle enabled=true
make rollback CONFIRM=yes CONFIRM_IRREVERSIBLE=yes  # §10 rollback
make report             # render HTML report from out/
make clean              # remove out/
```

---

## 5. Office-network / insecure mode

Lab ships with **insecure defaults on** so it works through a corporate proxy with self-signed certs. The relevant `.env` knobs:

| Env | Lab default | Purpose |
|---|---|---|
| `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` | blank | Set once; passed as `docker build` ARG + container env to every service |
| `GF_AUTH_ANONYMOUS_ENABLED` | `true` | No login while iterating |
| `GF_AUTH_ANONYMOUS_ORG_ROLE` | `Admin` | Anon has full edit rights |
| `GF_SECURITY_COOKIE_SECURE` | `false` | HTTP at the edge |
| `GF_SECURITY_STRICT_TRANSPORT_SECURITY` | `false` | HSTS off |
| `GF_SECURITY_CONTENT_SECURITY_POLICY` | `false` | CSP off |
| `GF_SECURITY_ALLOW_EMBEDDING` | `true` | iframe embed ok |
| `GF_PANELS_DISABLE_SANITIZE_HTML` | `true` | Rich HTML in text panels (needed by enterprise dashboards) |
| `GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS` | `*` | Any plugin |
| `GF_ANALYTICS_*` / `GF_NEWS_*` | all `false` | No phone-home through the proxy |
| DS `tlsSkipVerify` | `true` | Self-signed upstream OK |
| Renderer `IGNORE_HTTPS_ERRORS` | `true` | Chromium accepts self-signed |
| `GF_DATAPROXY_TLS_HANDSHAKE_TIMEOUT_SECONDS` | `30` | Tolerates slow office nets |

**None of these defaults are safe in production** — they're lab convenience. The production Helm values in `helm/values.common.yaml` flip them the other way (CSP on, HSTS on, strict signatures, OIDC required).

---

## 6. Production migration toolkit

The repo is wired for a real 11.6.4 → 12.4.3 cutover on AKS + GKE, independent of the lab:

```
docs/01-breaking-changes-matrix.md      30-item playbook — every breaking change
                                         has Detect / Fix / Validate blocks

audit/                                   pre-upgrade audit scripts
  pre_upgrade_audit.py                   orchestrator
  dashboard_inventory.py                 dump every dashboard JSON
  plugin_inventory.py                    flag Angular / unsigned / missing deps
  datasource_inventory.py                validate UID format, /health-probe each DS
  alert_rule_inventory.py                dump every Grafana-managed rule
  schema_diff.py                         schemaVersion distribution report
  compare_permissions.py                 full-replace ACL gap analysis
  find_tempo_aggregate_by.py             detect removed metrics-summary usage
  find_panel_type.py                     datagrid / gauge / angular panel finder
  count_panel_types.py                   panel type tally

migration/                               idempotent remediators (CONFIRM=yes gated)
  00_preflight.sh                        env + connectivity + pin validation
  10_backup.sh                           pg_dump + PVC snapshot (one-run scoped)
  20_angular_purge.py                    rewrite angular panels -> React equivalents
  30_schema_upgrade.py                   force-save every dashboard (persists migration)
  40_helm_upgrade.sh                     rolling helm upgrade
  50_postflight.sh                       post-cutover assertions
  99_rollback.sh                         double-confirmation rollback
  migrate_api_keys_to_sa.py              legacy keys -> service accounts
  rewrite_permissions_full_replace.py    12.3 full-replace ACL rewriter
  grant_creator_admin.py                 explicit Admin grants on top-level folders
  fix_plugin_dependency.py               plugin.json grafanaDependency patcher
  rewrite_bad_uids.py                    DS UID format normalizer
  rewrite_tempo_metrics.py               metrics-summary -> TraceQL metrics
  rewrite_am_metric_prefix.py            alertmanager_cluster_* -> grafana_alerting_ha_*
  rewrite_scenes_selectors.py            pre-Scenes DOM selector replacer
  rewrite_cache_size_metric.py           cache_size -> gets_total + usage_bytes
  rewrite_am_endpoints.py                deprecated AM endpoints -> provisioning
  rewrite_datagrid_to_table.py           datagrid -> table (react-data-grid)
  force_save_all_dashboards.py           post-cutover angular persistence (item #29)

validation/                              post-cutover gates
  api_smoke.py                           /api/health + /api/datasources + /api/featuremgmt
  dashboard_render_diff.py               pixel-diff top-50 dashboards pre/post
  alerting_parity.py                     pre/post alert rule evaluation parity
  feature_toggles_verify.py              every §5.6 toggle enabled=true
  feature_toggles_from_frontend.py       same check via /api/frontend/settings (no SA)
  permissions_parity.py                  provisioned ACL exactly matches live
  folder_admin_parity.py                 post-12.3 folder admin parity
  oauth_smoke.py                         Google OAuth HD validation check
  gate.py                                THE consolidated 30-row GO/NO-GO → HTML + JSON
  print_dashboards.py                    CLI dashboard URL printer
  acceptance_gate.py                     §11 acceptance-criteria rollup
  render_report.py                       HTML report renderer
  e2e/                                   Playwright + k6-browser harness (Part D)
    specs/00_smoke.spec.ts               version + toggles + 0-angular gate
    specs/10_drilldown.spec.ts
    specs/20_dynamic_dashboards.spec.ts
    specs/30_git_sync.spec.ts
    specs/40_sql_expressions.spec.ts
    specs/50_recording_rules.spec.ts
    specs/60_12_1_features.spec.ts
    specs/70_12_2_features.spec.ts
    specs/80_12_3_features.spec.ts
    specs/90_12_4_features.spec.ts
    specs/99_acceptance.spec.ts
  k6/
    browser_home.js                      k6-browser UX smoke
    api_load.js                          constant-VU API load

helm/                                    production Helm values
  values.common.yaml                     feature toggles, pod SC, HA AM, etc.
  values.aks.yaml                        Azure-specific (AGIC, Azure Files, Azure AD OIDC)
  values.gke.yaml                        GCP-specific (GCE ingress, Filestore, Google OIDC)

terraform/                               Grafana-provider resources (folders, teams, SAs)

git-sync/                                Git Sync bootstrap + config
  git-sync-config.yaml                   provisioning.grafana.app Repository CR
  bootstrap.sh                           apply ExternalSecret + Repository

ci/
  github-actions/audit.yml               daily audit against prod
  github-actions/validate.yml            PR validation on dashboards/provisioning
  github-actions/gitsync-pr-check.yml    render-diff + JSON lint on dashboard PRs
  jenkins/Jenkinsfile                    parallel pipeline for audit/validate/e2e/migrate
```

---

## 7. The 30-item playbook

[`docs/01-breaking-changes-matrix.md`](docs/01-breaking-changes-matrix.md) is the canonical list. Every item has a **Detect** block, a **Fix** block, and a **Validate** block. Severity:

- 🔴 **MUST** — 12 hard breaking items (1-12 + 29-30). Cutover blocker.
- 🟠 **SHOULD** — 11 behavioral items (13-23). Users will notice.
- 🟡 **INFO** — 5 deprecations (24-28). Removal scheduled for 13.0.

`validation/gate.py` runs all 30 against the live instance, emits `out/<run>/validate/go-no-go.html` + matching JSON, exits `0` only when every MUST passes. CI runs it on every PR.

Other docs:

| | |
|---|---|
| [`00-executive-summary.md`](docs/00-executive-summary.md) | For the VP pack |
| [`01-breaking-changes-matrix.md`](docs/01-breaking-changes-matrix.md) | The 30-item playbook |
| [`02-feature-enablement-plan.md`](docs/02-feature-enablement-plan.md) | Every v12 feature with demo dashboard + E2E spec |
| [`03-runbook-cutover.md`](docs/03-runbook-cutover.md) | T-14d → T+7d schedule |
| [`04-rollback-playbook.md`](docs/04-rollback-playbook.md) | Rollback procedure + triggers |
| [`05-post-migration-acceptance.md`](docs/05-post-migration-acceptance.md) | 24-hour acceptance gate |
| [`06-feature-toggle-reference.md`](docs/06-feature-toggle-reference.md) | §5.6 toggle block source of truth |

---

## 8. Feature toggles (all 19 ON)

The lab ships with every Grafana 12 feature toggle enabled so every demo has something to show:

```
provisioning · kubernetesDashboards · dashboardsNewLayouts · dashboardScene
grafanaManagedRecordingRules · sqlExpressions · regressionTransformation
adhocFiltersNew · logsPanelControls · panelTimeSettings · gitSync
templateVariablesRegexTransform · multiVariableProperties · suggestedDashboards
otlpLogs · metricsDrilldown · logsDrilldown · tracesDrilldown · profilesDrilldown
```

Source of truth: [`docs/06-feature-toggle-reference.md`](docs/06-feature-toggle-reference.md) + `GF_FEATURE_TOGGLES_ENABLE` in `lab/.env`. `make toggles` verifies every one is live.

---

## 9. Troubleshooting

**`invalid reference format` / all env vars "not set"** — you're running `docker compose up` from `lab/compose/` directly. Compose only reads `.env` from the CWD, and the `.env` lives one level up in `lab/`. Fix:

```bash
cd lab                               # NOT lab/compose/
docker compose --env-file .env -f compose/docker-compose.yml -p grafana12-oss-lab up -d --build
```

See §1 — the `--env-file` + `-f` flags make the invocation work from anywhere.

**`Cannot connect to the Docker daemon` / `npipe:////./pipe/dockerDesktopLinuxEngine`** — Docker Desktop isn't running. Start it (macOS: `open -a Docker`; Windows: Start menu → Docker Desktop) and wait ~30s for the whale icon to stop animating.

**Docker Desktop / `/Volumes` bind-mount error** — this used to kill bring-up. Fixed: all configs baked into service Dockerfiles. If you still see `mkdir /host_mnt/Volumes/Gopalmac: file exists`, do `make reset && make up`.

**Port already in use** — `:3012 / :9092 / :3112 / :3212 / :4042 / :12346` are the host ports. Another stack (a second `grafana13-lab`?) holding one of them: `docker ps` to find, `docker stop <that>`, then `make up`.

**Grafana container keeps restarting** — likely old Postgres volume with a stale password. `docker compose -f compose/docker-compose.yml -p grafana12-oss-lab down -v && make up`.

**Dashboards not showing up after edits** — the Grafana image bakes `lab-dashboards/` at build time. Re-build: `make build && make restart`. Docker caches the COPY layer aggressively — use `docker compose ... build --no-cache grafana` if you changed a file and the image timestamp is older than the file.

**Plugin install failed** — corporate SSL interception blocks plugin downloads from grafana.com. Confirm `HTTPS_PROXY` is set in `.env`. If your proxy still refuses, pre-download the plugin ZIPs and bind-mount `/var/lib/grafana/plugins`.

**Enterprise dashboard HTML renders as raw `<div>`** — `GF_PANELS_DISABLE_SANITIZE_HTML` defaults to `true` in `.env`. If you removed it, put it back.

**Can't reach `/api/plugins` from admin dashboards** — the Infinity DS is configured with `basicAuth: admin/admin`. If you changed `GF_SECURITY_ADMIN_PASSWORD`, update `lab/grafana/lab-provisioning/datasources/infinity.yaml` to match.

---

## 10. Hard rules (never break)

1. **Never** flip Dynamic Dashboards schema v2 without a same-run DB backup — migration is one-way.
2. **Never** force-push to the Git Sync repo.
3. **Never** run destructive commands without `CONFIRM=yes`.
4. **Never** skip the Angular audit — cost of a missed Angular dashboard is unrecoverable UX regression.
5. **Never** pin to minor version; always exact patch (e.g. `12.4.3`, not `12.4`).
6. **Never** use `latest` or unpinned chart versions.
7. **Never** commit secrets — `.env` is gitignored; only `.env.example` gets committed.
8. Keep the 11.6.4 `pg_dump` as source of truth for rollback for **30 days**.

---

## 11. License & attribution

Lab-only defaults are insecure on purpose; production values (`helm/values.*.yaml`) flip them back. Third-party plugins shipped via `GF_PLUGINS_PREINSTALL` retain their upstream licenses.

Authored against the Grafana 12.0–12.4 what's-new pages:

- https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-0/
- https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-1/
- https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-2/
- https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-3/
- https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-4/
- https://grafana.com/docs/grafana/latest/upgrade-guide/upgrade-v12.4/
