resource "grafana_team" "sre" {
  name  = "sre"
  email = "sre@example.com"
}

resource "grafana_team" "platform" {
  name  = "platform"
  email = "platform@example.com"
}
