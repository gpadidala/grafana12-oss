# Cutover Runbook — T-minus schedule

All times in the cluster's local timezone. Every step emits structured JSON logs and writes artifacts to `out/$RUN_ID/`.

## T-14 days

- [ ] `make audit` against live 11.6.4; publish `out/audit-*/report.md`.
- [ ] Remediate every Angular dashboard/plugin flagged.
- [ ] Announce authoring freeze window (communicate; do not enforce yet).
- [ ] Stand up staging cluster with `12.4.x` chart version from audit resolver.
- [ ] Restore a fresh copy of prod Postgres into staging.

## T-7 days

- [ ] `make validate` on staging — all 15 validation dashboards green.
- [ ] `make e2e` — full end-to-end suite green (see `docs/05-post-migration-acceptance.md`).
- [ ] `validation/alerting_parity.py` — alert evaluation parity ≥ 99% between 11.6.4 snapshot replay and 12.4.x staging.
- [ ] `validation/dashboard_render_diff.py` — top-50 most-viewed dashboards pixel diff ≤ 2%.

## T-1 day

- [ ] `bash migration/10_backup.sh` — Postgres `pg_dump`, `/var/lib/grafana` tarball, plugin dir, `grafana.ini`, provisioning tree.
- [ ] PVC snapshot via CSI (Azure Disk / PD).
- [ ] Tag `grafana/grafana-oss:11.6.4` as `:rollback-candidate` in internal registry.
- [ ] Announce 30-minute maintenance window.

## T-0 cutover (≈ 30 min)

1. Status page → maintenance.
2. Temporary RBAC override → editors read-only.
3. `helm upgrade grafana grafana/grafana -f helm/values.common.yaml -f helm/values.$CLUSTER.yaml --version $HELM_CHART_VERSION`.
4. `kubectl rollout status statefulset/grafana -n grafana --timeout=5m` per replica.
5. First pod ready → assert `/api/health` and `buildInfo.version` starts `12.4.`.
6. Let remaining pods roll.
7. `bash migration/50_postflight.sh` — runs:
   - `validation/feature_toggles_verify.py` (every §5.6 toggle enabled=true)
   - `grafana_build_info{version=~"12\\.4\\..*"}` assertion
   - Angular panel count == 0
   - Force-save every force-migrated dashboard via API
   - `validation/api_smoke.py`
8. Run `validation/e2e/run_all.sh` in smoke mode (fast subset).
9. Lift RBAC override.
10. Close maintenance window.

## T+1 day

- [ ] Review `migration-cutover.json` dashboard.
- [ ] Triage any panel regressions via Git Sync PR.

## T+7 days

- [ ] Decommission `:rollback-candidate` image tag.
- [ ] Delete PVC snapshot (retain DB dump 30 days).

## Abort conditions (triggers §10 rollback)

- Render p95 > 2× baseline > 15 min
- Alerting parity < 99% over 1 hour
- P1 plugin broken with no workaround
- Persistent HA Alertmanager split-brain
