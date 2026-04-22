# Rollback Playbook

Triggered by `make rollback CONFIRM=yes` OR any one of the abort conditions in `03-runbook-cutover.md`.

## Procedure

1. **Freeze writes** — set RBAC override to read-only for all editors.
2. `helm rollback grafana <previous-revision> -n grafana` — returns the chart + pod spec to 11.6.4.
3. **Restore Postgres** from `out/<run-id>/pg_dump/grafana.sql.gz` — mandatory if Dynamic Dashboards schema v2 was flipped (one-way migration). Even if not, restore if any provisioning full-replace permissions landed.
4. **Restore PVC** from CSI snapshot taken in `10_backup.sh`.
5. Re-tag `grafana/grafana-oss:11.6.4` as the pinned image for the rolled-back revision.
6. Verify `/api/health` returns `{"database":"ok"}`.
7. Assert `grafana_build_info` reports `11.6.4` across all pods.
8. Run the 11.6.4 version of the validation suite (`validation/api_smoke.py --version 11.6.4`).
9. Lift RBAC override.
10. Status page → operational.
11. File incident postmortem in the standard template.

## Hard safeguards (enforced by `99_rollback.sh`)

- Requires `CONFIRM=yes` on first invocation.
- Requires `CONFIRM_IRREVERSIBLE=yes` on second invocation before the Postgres restore step.
- Refuses to run if `out/<run-id>/pg_dump/grafana.sql.gz` is missing or older than 24 h.
- Refuses to run if the previous Helm revision is not tagged with `rollback-candidate` annotation.

## What rollback does NOT restore

- Any dashboard edits made through the UI during the maintenance window (editors were read-only — should be none).
- Git Sync PR history — the Git repo is independent; dashboards re-sync on revision restore.
- Alertmanager silences created during the window — re-create if needed.
