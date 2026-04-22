terraform {
  required_version = ">= 1.7"
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = ">= 3.0"
    }
  }
  backend "s3" {}  # configure per env
}

provider "grafana" {
  url  = var.grafana_url
  auth = var.grafana_sa_token
  org_id = var.grafana_org_id
}

variable "grafana_url" { type = string }
variable "grafana_sa_token" {
  type      = string
  sensitive = true
}
variable "grafana_org_id" {
  type    = number
  default = 1
}
