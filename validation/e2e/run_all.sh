#!/usr/bin/env bash
# End-to-end harness entrypoint.
#
# Three layers:
#   1) API-level coverage  (validation/api_smoke.py, feature_toggles_verify.py, alerting_parity.py)
#   2) k6-browser journeys (validation/k6/*.js) — headless UX scenarios against every v12 feature
#   3) Playwright feature specs (validation/e2e/specs/*.spec.ts) — 1 per §5 feature
#
# Modes:
#   full   (default)  — run every spec; gate for cutover acceptance
#   smoke             — subset used at T-0 step 8 to stay inside the maintenance window
#
# Usage: validation/e2e/run_all.sh <out-dir> [mode]

set -euo pipefail
OUT="${1:?}"
MODE="${2:-full}"
mkdir -p "$OUT/e2e"

log() { printf '{"ts":"%s","level":"%s","step":"e2e","event":"%s"}\n' "$(date -u +%FT%TZ)" "$1" "$2"; }

# 1) API layer
python3 validation/feature_toggles_verify.py --out "$OUT"
python3 validation/api_smoke.py --out "$OUT"
python3 validation/alerting_parity.py --out "$OUT" || true

# 2) k6-browser
if command -v k6 >/dev/null; then
  for f in validation/k6/*.js; do
    name=$(basename "$f" .js)
    K6_BROWSER_HEADLESS=true k6 run --out json="$OUT/e2e/k6-${name}.json" "$f"
  done
else
  log warn k6_not_installed
fi

# 3) Playwright specs
if [[ -f validation/e2e/package.json ]]; then
  pushd validation/e2e >/dev/null
  npm ci --silent
  if [[ "$MODE" == "smoke" ]]; then
    npx playwright test --grep '@smoke' --reporter=json > "$OUT/e2e/playwright-smoke.json"
  else
    npx playwright test --reporter=json > "$OUT/e2e/playwright-full.json"
  fi
  popd >/dev/null
else
  log warn playwright_not_initialised
fi

# 4) Dashboard render diff baseline → current
python3 validation/dashboard_render_diff.py --out "$OUT" --mode diff \
  --baseline-dir "$(ls -td out/audit-*/render-baseline 2>/dev/null | head -1 || echo /tmp/nonexistent)" \
  || log warn render_diff_nonzero

# 5) Acceptance gate aggregates everything.
python3 validation/acceptance_gate.py --out "$OUT"
