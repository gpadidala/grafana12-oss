#!/usr/bin/env bash
# Bootstrap Git Sync: create ExternalSecret + Repository resource, seed repo from pre-snapshot.
set -euo pipefail

: "${K8S_NAMESPACE:?}" "${GITSYNC_REPO_URL:?}" "${GITHUB_APP_ID_SECRET:?}" "${GITHUB_APP_PRIVATE_KEY_SECRET:?}"

log() { printf '{"ts":"%s","level":"%s","step":"gitsync","event":"%s"}\n' "$(date -u +%FT%TZ)" "$1" "$2"; }

# 1) ExternalSecret for the GitHub App credentials.
cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata: { name: grafana-gitsync, namespace: ${K8S_NAMESPACE} }
spec:
  refreshInterval: 1h
  secretStoreRef: { kind: ClusterSecretStore, name: vault }
  target: { name: grafana-gitsync }
  data:
    - secretKey: app_id
      remoteRef: { key: ${GITHUB_APP_ID_SECRET} }
    - secretKey: private_key
      remoteRef: { key: ${GITHUB_APP_PRIVATE_KEY_SECRET} }
EOF

# 2) Apply Repository resource.
envsubst < git-sync/git-sync-config.yaml | kubectl apply -f -

log info gitsync_applied
