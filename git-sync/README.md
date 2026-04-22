# Git Sync

Enabled via the `gitSync` + `provisioning` feature toggles. See `docs/06-feature-toggle-reference.md`.

## Setup

1. Create GitHub repo `grafana-dashboards-<env>` with branch protection on `main`.
2. Provision a GitHub App scoped **only** to that repo with contents:read/write.
3. Store the App ID + private key in Vault/ESO; reference names from `.envrc`.
4. `bash git-sync/bootstrap.sh`.
5. Seed the repo with dashboards from the latest audit: `out/audit-*/dashboards/snapshot-pre/`.
6. Verify the branch selector appears in the Grafana save drawer.

## CI gate

Every PR runs `ci/github-actions/gitsync-pr-check.yml`:
- JSON schema validation
- Headless render diff against staging
- Block merge on failure
