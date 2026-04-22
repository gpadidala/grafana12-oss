locals {
  folders = {
    platform    = { title = "Platform" }
    validation  = { title = "v12 Validation" }
    demos       = { title = "v12 Feature Demos" }
    alerts      = { title = "Alerting" }
  }
}

resource "grafana_folder" "this" {
  for_each = local.folders
  title    = each.value.title
  uid      = each.key
}
