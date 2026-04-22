# Post-Migration Acceptance Gate

The migration is **accepted** only when all checks hold for ≥ 24 h post-cutover. `validation/acceptance_gate.py` enforces each programmatically and emits `out/<run-id>/acceptance.md`.

## Runtime health

- [ ] `/api/health` → `{"database":"ok"}` on every pod
- [ ] `grafana_build_info{version=~"12\\.4\\.[0-9]+"}` on every pod
- [ ] Every §5.6 feature toggle reports `enabled=true` via `/api/featuremgmt`
- [ ] Zero unsigned plugins loaded
- [ ] Zero Angular panels across all dashboards (enforced by `angular-regression-guard.json`)

## Data plane

- [ ] Every data source `/api/datasources/uid/*/health` → OK
- [ ] Postgres error rate < 0.1% (5 min avg)
- [ ] Redis remote-cache error rate < 0.1%

## Alerting

- [ ] Every alert rule from pre-migration snapshot present (ID parity via `alert_rule_inventory.py` diff)
- [ ] HA Alertmanager peer gossip healthy across all pods
- [ ] Alertmanager metrics present under the **new 12.4 prefix**
- [ ] Recording-rule evaluation lag < 60 s

## Dashboard UX

- [ ] Dashboard render p95 within ±10% of 11.6.4 baseline
- [ ] Top-50 most-viewed dashboards pixel-diff ≤ 2% pre/post
- [ ] Scenes v2 adoption reaches 100% of dashboards
- [ ] No v1 schemaVersion dashboards remain (`schemaVersion >= 40` across the board)

## Git Sync

- [ ] End-to-end PR merge → live dashboard in < 120 s
- [ ] Zero sync conflicts in the first 24 h
- [ ] PR CI checks pass (lint + render diff)

## Identity & access

- [ ] Zero remaining legacy API keys
- [ ] RBAC diff clean (no user lost access except via intentional `editors_can_admin` removal)
- [ ] OIDC login success rate > 99.5%

## End-to-end (`make e2e`)

- [ ] `validation/e2e/run_all.sh` exits 0 in full mode
- [ ] Every v12 feature-demo dashboard from §5 opens, renders, and passes its Playwright/k6-browser spec
- [ ] All 12.4 new features (multi-property variables, regex transforms, panel time drawer, gauge, OTLP logs, suggested dashboards, Dynamic dashboards PP, Git Sync PP, dashboards-from-templates) have green specs

## Tickets

- [ ] Zero P1/P2 support tickets related to dashboards or alerts in the 24 h soak window
