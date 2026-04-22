#!/usr/bin/env bash
# §9 T-0 step 0: preflight checks — environment, connectivity, pin resolution.
set -euo pipefail

: "${GRAFANA_URL:?}" "${GRAFANA_SA_TOKEN:?}" "${K8S_NAMESPACE:?}"
: "${GRAFANA_IMAGE_TAG:?set target patch, e.g. 12.4.3}"
: "${HELM_CHART_VERSION:?pin chart version, never latest}"

log() { printf '{"ts":"%s","level":"%s","step":"preflight","event":"%s"}\n' "$(date -u +%FT%TZ)" "$1" "$2"; }

# Version pin guard — refuse minor-only tags.
if ! [[ "$GRAFANA_IMAGE_TAG" =~ ^12\.4\.[0-9]+$ ]]; then
  log fatal invalid_image_tag
  echo "ERROR: GRAFANA_IMAGE_TAG must be exact patch like 12.4.3, got: $GRAFANA_IMAGE_TAG" >&2
  exit 2
fi

# Connectivity
curl -fsS -H "Authorization: Bearer ${GRAFANA_SA_TOKEN}" "${GRAFANA_URL}/api/health" | grep -q '"database":"ok"' \
  || { log fatal grafana_unreachable; exit 2; }

kubectl get ns "${K8S_NAMESPACE}" >/dev/null \
  || { log fatal ns_missing; exit 2; }

# Chart pin guard
helm search repo grafana/grafana --versions | awk -v v="$HELM_CHART_VERSION" 'NR>1 && $2==v {found=1} END{exit !found}' \
  || { log fatal chart_version_not_found; exit 2; }

log info preflight_ok
