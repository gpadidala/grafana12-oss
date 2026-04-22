#!/usr/bin/env bash
# §9 T-0 step 3: rolling Helm upgrade to pinned 12.4.x.
set -euo pipefail

: "${K8S_NAMESPACE:?}" "${HELM_CHART_VERSION:?}" "${GRAFANA_IMAGE_TAG:?}" "${CLUSTER:?aks|gke}"

log() { printf '{"ts":"%s","level":"%s","step":"helm_upgrade","event":"%s"}\n' "$(date -u +%FT%TZ)" "$1" "$2"; }

VALUES_CLUSTER="helm/values.${CLUSTER}.yaml"
test -f "${VALUES_CLUSTER}" || { log fatal missing_values; exit 2; }

helm upgrade --install grafana grafana/grafana \
  --namespace "${K8S_NAMESPACE}" \
  --version "${HELM_CHART_VERSION}" \
  --values helm/values.common.yaml \
  --values "${VALUES_CLUSTER}" \
  --set "image.tag=${GRAFANA_IMAGE_TAG}" \
  --atomic \
  --timeout 15m \
  --wait

# Per-pod rollout verification
kubectl -n "${K8S_NAMESPACE}" rollout status statefulset/grafana --timeout=10m

# Assert build info
for pod in $(kubectl -n "${K8S_NAMESPACE}" get pod -l app.kubernetes.io/name=grafana -o name); do
  v=$(kubectl -n "${K8S_NAMESPACE}" exec "${pod}" -- \
        curl -sf http://localhost:3000/api/health | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])') || true
  case "$v" in
    12.4.*) log info pod_ok ;;
    *) log fatal pod_version_mismatch; exit 2 ;;
  esac
done

log info helm_upgrade_ok
