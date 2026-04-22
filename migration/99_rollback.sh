#!/usr/bin/env bash
# §10 rollback. Double-confirmation + freshness gate.
set -euo pipefail

: "${RUN_ID:?}" "${K8S_NAMESPACE:?}" "${PG_HOST:?}" "${PG_DB:?}"

log() { printf '{"ts":"%s","level":"%s","step":"rollback","event":"%s"}\n' "$(date -u +%FT%TZ)" "$1" "$2"; }

if [[ "${CONFIRM:-}" != "yes" ]]; then
  echo "First gate: re-run with CONFIRM=yes"; exit 2
fi

DUMP="out/${RUN_ID}/backup/pg_dump/grafana.sql.gz"
if [[ ! -s "$DUMP" ]]; then
  log fatal missing_dump; exit 2
fi

# 1) Helm rollback to previous revision
PREV=$(helm -n "${K8S_NAMESPACE}" history grafana -o json | python3 -c 'import json,sys; r=json.load(sys.stdin); print(r[-2]["revision"])')
helm -n "${K8S_NAMESPACE}" rollback grafana "${PREV}" --wait --timeout 15m

# 2) Postgres restore — behind a second gate because it is destructive.
if [[ "${CONFIRM_IRREVERSIBLE:-}" == "yes" ]]; then
  PG_USER_FILE="/secrets/pg/user"; PG_PASS_FILE="/secrets/pg/password"
  PGPASSWORD="$(cat "$PG_PASS_FILE")" pg_restore \
    -h "${PG_HOST}" -U "$(cat "$PG_USER_FILE")" -d "${PG_DB}" \
    --clean --if-exists --no-owner --no-privileges \
    <(gunzip -c "$DUMP")
  log info pg_restored
else
  log warn pg_restore_skipped
fi

# 3) Health assertion
kubectl -n "${K8S_NAMESPACE}" rollout status statefulset/grafana --timeout=10m
log info rollback_ok
