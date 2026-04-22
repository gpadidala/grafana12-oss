# Service accounts replacing the legacy API keys that were removed in 12.3.
# Tokens are written to the Vault secret path referenced by .envrc.

resource "grafana_service_account" "ci" {
  name = "ci-dashboards"
  role = "Editor"
}

resource "grafana_service_account_token" "ci" {
  name               = "ci-token"
  service_account_id = grafana_service_account.ci.id
}

resource "grafana_service_account" "audit" {
  name = "audit-readonly"
  role = "Viewer"
}

resource "grafana_service_account_token" "audit" {
  name               = "audit-token"
  service_account_id = grafana_service_account.audit.id
}
