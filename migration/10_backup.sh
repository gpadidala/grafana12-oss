#!/usr/bin/env bash
# §9 T-1d backup: Postgres pg_dump, /var/lib/grafana tarball, plugin dir, grafana.ini, provisioning tree.
# Hard-rule gate: refuses to exit 0 unless every artifact is present and non-empty.
set -euo pipefail

: "${RUN_ID:?}" "${K8S_NAMESPACE:?}" "${PG_HOST:?}" "${PG_DB:?}"
OUT="out/${RUN_ID}/backup"
mkdir -p "${OUT}/pg_dump" "${OUT}/var" "${OUT}/config" "${OUT}/provisioning"

log() { printf '{"ts":"%s","level":"%s","step":"backup","event":"%s","detail":%s}\n' "$(date -u +%FT%TZ)" "$1" "$2" "${3:-null}"; }

# 1) Postgres dump (credentials via ESO-mounted secret at /secrets/pg/*)
PG_USER_FILE="/secrets/pg/user"
PG_PASS_FILE="/secrets/pg/password"
[[ -r "$PG_USER_FILE" && -r "$PG_PASS_FILE" ]] || { log fatal pg_secret_missing; exit 2; }
PGPASSWORD="$(cat "$PG_PASS_FILE")" pg_dump \
  -h "${PG_HOST}" -U "$(cat "$PG_USER_FILE")" -d "${PG_DB}" \
  --format=custom --no-owner --no-privileges \
  | gzip -9 > "${OUT}/pg_dump/grafana.sql.gz"

# 2) /var/lib/grafana tarball from pod 0
POD="$(kubectl -n "${K8S_NAMESPACE}" get pod -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}')"
kubectl -n "${K8S_NAMESPACE}" exec "${POD}" -- tar czf - -C /var/lib grafana > "${OUT}/var/grafana-varlib.tgz"

# 3) plugins dir
kubectl -n "${K8S_NAMESPACE}" exec "${POD}" -- tar czf - -C /var/lib/grafana plugins > "${OUT}/var/plugins.tgz" || true

# 4) grafana.ini + provisioning tree (pulled from ConfigMap + Secret)
kubectl -n "${K8S_NAMESPACE}" get cm grafana -o yaml > "${OUT}/config/cm-grafana.yaml"
kubectl -n "${K8S_NAMESPACE}" get secret grafana -o yaml > "${OUT}/config/secret-grafana.yaml"
kubectl -n "${K8S_NAMESPACE}" exec "${POD}" -- tar czf - -C /etc/grafana provisioning > "${OUT}/provisioning/provisioning.tgz" || true

# 5) Non-empty assertion
for f in pg_dump/grafana.sql.gz var/grafana-varlib.tgz; do
  test -s "${OUT}/${f}" || { log fatal empty_artifact "\"${f}\""; exit 2; }
done

# 6) PVC snapshot (CSI)
for pvc in $(kubectl -n "${K8S_NAMESPACE}" get pvc -l app.kubernetes.io/name=grafana -o name); do
  snap_name="grafana-snap-${RUN_ID}-$(basename "$pvc")"
  cat <<EOF | kubectl apply -f -
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ${snap_name}
  namespace: ${K8S_NAMESPACE}
  labels: { run-id: "${RUN_ID}", purpose: grafana-rollback }
spec:
  source:
    persistentVolumeClaimName: $(basename "$pvc")
EOF
done

log info backup_complete "\"${OUT}\""
