# Executive Summary — Grafana OSS 11.6.4 → 12.4.x Migration

**Audience:** VP Platform, SRE leadership, Compliance.
**Owner:** Staff Grafana Platform Admin.
**Scope:** AKS + GKE multi-cluster, Postgres-backed, Redis remote-cache, StatefulSet x 3 replicas per cluster.
**Outcome:** Pinned `12.4.x` patch, every v12 feature enabled, full validation dashboard suite green, end-to-end test harness green, zero-surprise breaking-change remediation.

## Why now

1. **Angular removal forces the move** — 12.0 ripped out AngularJS entirely. Any delay accrues dashboard/plugin debt faster.
2. **Git Sync (public preview in 12.4)** — native GitOps for dashboards without stitching JSON API + external controllers.
3. **Drilldown suite GA (12.0)** + **Alerting UX GA (12.1)** — reduces MTTR tooling surface for the AIOps hub.
4. **Scenes-powered architecture mandatory** — blocks any delay to 13 where the flag is removed.
5. **Dynamic Dashboards + Multi-property variables (12.4)** — unblocks the multi-stack/multi-cluster variable pattern already standardized on this platform.

## Approach

1. `make audit` against the live 11.6.4 instance. Produce GO/NO-GO with Angular purge list, plugin compat, schema distribution, RBAC/API-key exposure, alert parity baseline.
2. Remediate Angular dashboards/plugins; export all dashboards; stage DB clone; run full migration + validation + E2E on staging.
3. Freeze dashboard authoring 24h pre-cutover.
4. 30-minute maintenance window rolling Helm upgrade; post-flight asserts version + feature toggles + Angular count == 0.
5. 24h soak on acceptance gate (§11). Decommission rollback artifacts at T+7d.

## Risk register

| Risk | Mitigation |
|---|---|
| Dynamic Dashboards schema v2 is one-way | Mandatory DB dump + PVC snapshot in same run; rollback restores Postgres |
| Angular panels without React equivalent | Pre-audit replaces or deletes before cutover — no surprises at runtime |
| HA Alertmanager cluster metric prefix change (12.4) | Prometheus scrape + Mimir recording rules updated pre-cutover; `unified-alerting-ha.json` validates new prefix |
| API-key removal (12.3) | Full service-account migration landed in audit phase |
| Top-level folder admin change (12.3) | Explicit RBAC provisioning file preserves creator-admin where required |
| Provisioning full-replace permissions (12.3) | Every permission file rewritten to complete ACL before cutover |

## Deliverables

- Pinned Helm values for AKS + GKE (`helm/values.*.yaml`).
- Full feature-toggle enablement (§5.6 of master prompt) — verified post-cutover by `validate` target.
- 15 validation dashboards (§8) in Git Sync repo.
- End-to-end test harness (k6-browser + API smoke + alerting parity + dashboard render diff) wired into CI and `make e2e`.
- Runbook (§9), rollback playbook (§10), acceptance gate (§11).

## Required inputs (blocker for audit)

See §16.3 of the master prompt — I still need: AKS + GKE cluster names, Postgres DSN source, Git Sync repo URL, OIDC provider, target `12.4.x` patch version.
