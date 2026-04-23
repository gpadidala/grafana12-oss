SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

COMPOSE      ?= docker compose
COMPOSE_FILE := compose/docker-compose.yml
ENV_FILE     := .env
PROJECT      := grafana12-oss-lab
GRAFANA_URL  ?= http://localhost:3012

.PHONY: help up down reset restart logs health toggles ds build pull status verify office

help:         ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(ENV_FILE):
	@echo "creating $(ENV_FILE) from .env.example"
	@cp .env.example $(ENV_FILE)
	@echo "  edit $(ENV_FILE) to customize admin password, proxy, etc."

build: $(ENV_FILE)   ## Build all local images (Grafana + LGTM) with proxy args
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) -p $(PROJECT) build --pull

pull: $(ENV_FILE)    ## Pull any pre-built base images
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) -p $(PROJECT) pull --ignore-buildable

up: $(ENV_FILE)      ## Bring the lab up end-to-end (build + start + wait for health)
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) -p $(PROJECT) up -d --build
	@echo
	@echo ">> waiting for Grafana $(GRAFANA_URL)/api/health"
	@for i in $$(seq 1 60); do \
	  curl -fsS $(GRAFANA_URL)/api/health >/dev/null 2>&1 && break; \
	  sleep 2; \
	done
	@$(MAKE) --no-print-directory status

down:         ## Stop the stack (preserve volumes)
	$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) down

reset:        ## Nuke everything including volumes (destructive)
	$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) down -v --remove-orphans

restart:      ## Restart Grafana only
	$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) restart grafana

logs:         ## Tail Grafana logs (Ctrl+C to exit)
	$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) logs -f grafana

status:       ## Show container status + URLs
	@$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
	@echo
	@echo "  Grafana UI    → $(GRAFANA_URL)   (anonymous Admin OR admin / see .env)"
	@echo "  Prometheus UI → http://localhost:9092"
	@echo "  Loki API      → http://localhost:3112"
	@echo "  Tempo API     → http://localhost:3212"
	@echo "  Pyroscope UI  → http://localhost:4042"
	@echo "  Alloy UI      → http://localhost:12346"

health:       ## Assert /api/health is green
	@curl -fsS $(GRAFANA_URL)/api/health | python3 -m json.tool

ds:           ## Show every data source and its /health result
	@curl -fsS -u admin:admin $(GRAFANA_URL)/api/datasources | python3 -c 'import json,sys,urllib.request,base64; auth=base64.b64encode(b"admin:admin").decode(); dss=json.load(sys.stdin); [print(f"  {d[\"name\"]:<12} {d[\"type\"]:<32} uid={d[\"uid\"]:<10} -> " + (json.load(urllib.request.urlopen(urllib.request.Request(f"$(GRAFANA_URL)/api/datasources/uid/{d[\"uid\"]}/health", headers={\"Authorization\": f\"Basic {auth}\"}), timeout=10)).get("status","?") if True else "?")) for d in dss]'

toggles:      ## Verify every §5.6 feature toggle is enabled
	@curl -fsS -u admin:admin $(GRAFANA_URL)/api/frontend/settings | python3 ../validation/feature_toggles_from_frontend.py

dashboards:   ## Print direct URLs for every provisioned dashboard
	@GRAFANA_URL=$(GRAFANA_URL) python3 ../validation/print_dashboards.py

verify:       ## Full verification suite (health + DS + toggles)
	@$(MAKE) --no-print-directory health
	@echo
	@$(MAKE) --no-print-directory ds
	@echo
	@$(MAKE) --no-print-directory toggles

office:       ## Alias for `up` — intent-named for office / corporate proxy runs
	@$(MAKE) --no-print-directory up
