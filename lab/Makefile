SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

COMPOSE ?= docker compose
COMPOSE_FILE := compose/docker-compose.yml
ENV_FILE := .env
PROJECT := grafana12-oss-lab

.PHONY: help up down reset restart logs health toggles

help:
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up:          ## Bring the lab stack up (idempotent)
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_FILE) -p $(PROJECT) up -d
	@echo "Grafana → http://localhost:3012  (admin / see .env)"

down:        ## Stop the stack (preserve volumes)
	$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) down

reset:       ## Nuke everything including volumes (destructive)
	$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) down -v --remove-orphans

restart:     ## Restart Grafana only
	$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) restart grafana

logs:        ## Tail Grafana logs
	$(COMPOSE) -f $(COMPOSE_FILE) -p $(PROJECT) logs -f grafana

health:      ## Assert /api/health and version == 12.4.x
	@curl -fsS http://localhost:3000/api/health | python3 -m json.tool

toggles:     ## Assert every §5.6 feature toggle is enabled
	@PYTHONPATH=../audit:../validation GRAFANA_URL=http://localhost:3000 \
	  GRAFANA_SA_TOKEN=$$(curl -fsS -u admin:$$(grep ^GF_SECURITY_ADMIN_PASSWORD .env | cut -d= -f2) \
	    -H 'Content-Type: application/json' \
	    -X POST http://localhost:3000/api/auth/keys \
	    -d '{"name":"lab-verify","role":"Admin","secondsToLive":60}' 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("key",""))') \
	  python3 ../validation/feature_toggles_verify.py --out ../out/lab
