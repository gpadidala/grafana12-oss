# grafana12-oss

Production migration repo: **Grafana OSS 11.6.4 → 12.4.x** across AKS + GKE multi-cluster.

Role: Staff Grafana Platform Admin. Idempotent, reversible, auditable, fail-fast, version-pinned.

## Targets

| | |
|---|---|
| Source | `grafana/grafana-oss:11.6.4` |
| Target | `grafana/grafana-oss:12.4.x` (exact patch pinned at audit) |
| Chart | `grafana/grafana` (pinned at audit) |
| Clusters | AKS + GKE (identical Helm values) |

## Entrypoints

```bash
make audit        # §3 pre-upgrade audit → out/audit-<ts>/
make migrate      # §9 cutover runbook (requires CONFIRM=yes)
make validate     # §8 + §11 validation & acceptance gates
make rollback     # §10 rollback (requires CONFIRM=yes twice)
make report       # render HTML report from out/
```

## Layout

See [docs/00-executive-summary.md](docs/00-executive-summary.md). Full layout, deliverables, and hard rules follow §2 and §15 of the master prompt.

## Hard rules (§15)

1. Never flip Dynamic Dashboards schema v2 without a fresh DB backup in the same run — migration is one-way.
2. Never force-push to the Git Sync repo.
3. Never run destructive commands without `CONFIRM=yes`.
4. Never skip the Angular audit.
5. Never pin to minor version; always exact patch.
6. Never use `latest` or unpinned chart versions.
7. Never commit secrets.
8. Keep the 11.6.4 `pg_dump` as source of truth for rollback for 30 days.
