#!/usr/bin/env bash
# §9 T-0 step 7: postflight. Asserts feature toggles, version, Angular==0.
set -euo pipefail

: "${GRAFANA_URL:?}" "${GRAFANA_SA_TOKEN:?}" "${RUN_ID:?}"

log() { printf '{"ts":"%s","level":"%s","step":"postflight","event":"%s"}\n' "$(date -u +%FT%TZ)" "$1" "$2"; }

# 1) Feature toggles
python3 validation/feature_toggles_verify.py --out "out/${RUN_ID}" \
  || { log fatal feature_toggle_mismatch; exit 2; }

# 2) build_info version assertion via /api/health
v=$(curl -fsS -H "Authorization: Bearer ${GRAFANA_SA_TOKEN}" "${GRAFANA_URL}/api/health" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
case "$v" in
  12.4.*) log info version_ok ;;
  *) log fatal version_mismatch; exit 2 ;;
esac

# 3) Angular panel count must be 0
python3 - <<'PY'
import json, os, sys, requests
base = os.environ["GRAFANA_URL"].rstrip("/")
tok = os.environ["GRAFANA_SA_TOKEN"]
h = {"Authorization": f"Bearer {tok}"}
r = requests.get(f"{base}/api/search?type=dash-db&limit=5000", headers=h, timeout=30)
r.raise_for_status()
angular_panels = 0
for row in r.json():
    uid = row["uid"]
    d = requests.get(f"{base}/api/dashboards/uid/{uid}", headers=h, timeout=30).json().get("dashboard", {})
    for p in d.get("panels", []) or []:
        t = (p.get("type") or "")
        if t in {"graph","singlestat","table-old","grafana-piechart-panel","grafana-worldmap-panel"}:
            angular_panels += 1
print(json.dumps({"angular_panels": angular_panels}))
sys.exit(0 if angular_panels == 0 else 2)
PY

# 4) API smoke
python3 validation/api_smoke.py --out "out/${RUN_ID}"

# 5) Force-save every dashboard once (persists server-side schema migration)
python3 migration/30_schema_upgrade.py --run-id "${RUN_ID}" || true

log info postflight_ok
