SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

RUN_ID ?= $(shell date -u +%Y%m%dT%H%M%SZ)
OUT_DIR := out/$(RUN_ID)
PY ?= python3

export RUN_ID OUT_DIR

.PHONY: help audit migrate validate rollback report e2e feature-toggles-verify clean

help:
	@echo "grafana12-oss — Grafana OSS 11.6.4 → 12.4.x migration"
	@echo ""
	@echo "  make audit                 Run §3 pre-upgrade audit"
	@echo "  make migrate CONFIRM=yes   Run §9 cutover runbook"
	@echo "  make validate              Run §8 + §11 acceptance gates"
	@echo "  make e2e                   Run full end-to-end test suite"
	@echo "  make feature-toggles-verify  Assert every §5.6 toggle is enabled=true"
	@echo "  make rollback CONFIRM=yes  Run §10 rollback"
	@echo "  make report                Render HTML report from out/"
	@echo "  make clean                 Remove out/ artifacts"

audit:
	@mkdir -p $(OUT_DIR)
	$(PY) audit/pre_upgrade_audit.py --out $(OUT_DIR)
	$(PY) audit/dashboard_inventory.py --out $(OUT_DIR)
	$(PY) audit/plugin_inventory.py --out $(OUT_DIR)
	$(PY) audit/datasource_inventory.py --out $(OUT_DIR)
	$(PY) audit/alert_rule_inventory.py --out $(OUT_DIR)
	$(PY) audit/schema_diff.py --out $(OUT_DIR)
	@echo "[audit] GO/NO-GO report: $(OUT_DIR)/report.md"

migrate:
ifneq ($(CONFIRM),yes)
	@echo "ERROR: destructive operation; re-run with CONFIRM=yes"; exit 2
endif
	bash migration/00_preflight.sh
	bash migration/10_backup.sh
	$(PY) migration/20_angular_purge.py
	$(PY) migration/30_schema_upgrade.py
	bash migration/40_helm_upgrade.sh
	bash migration/50_postflight.sh

validate: feature-toggles-verify
	$(PY) validation/api_smoke.py --out $(OUT_DIR)
	$(PY) validation/dashboard_render_diff.py --out $(OUT_DIR)
	$(PY) validation/alerting_parity.py --out $(OUT_DIR)
	$(PY) validation/acceptance_gate.py --out $(OUT_DIR)
	@mkdir -p $(OUT_DIR)/validate
	$(PY) validation/gate.py \
	  --audit-dir $(OUT_DIR) \
	  --fix-dir   $(OUT_DIR) \
	  --url       $${GRAFANA_URL} \
	  --report    $(OUT_DIR)/validate/go-no-go.html
	@echo "[validate] 30-item gate: $(OUT_DIR)/validate/go-no-go.html"

e2e:
	@mkdir -p $(OUT_DIR)
	bash validation/e2e/run_all.sh $(OUT_DIR)

feature-toggles-verify:
	$(PY) validation/feature_toggles_verify.py --out $(OUT_DIR)

rollback:
ifneq ($(CONFIRM),yes)
	@echo "ERROR: destructive operation; re-run with CONFIRM=yes"; exit 2
endif
	bash migration/99_rollback.sh

report:
	$(PY) validation/render_report.py --in out --out out/report.html
	@echo "[report] out/report.html"

clean:
	rm -rf out/
