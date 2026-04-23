#!/usr/bin/env bash
# Linux / macOS bootstrap for the grafana12-oss lab.
# Same contract as setup.ps1 on Windows.
#
# Usage:  ./setup.sh [up|down|reset|status|logs|build]
#
# `make up` on Mac/Linux runs the same flow via the Makefile. This script is
# here so the "no make, no problem" path is identical on every platform.

set -euo pipefail

ACTION="${1:-up}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found. Install Docker Desktop or Docker Engine and retry." >&2
  exit 1
fi
if [[ ! -f .env.example ]]; then
  echo "ERROR: run this from the lab/ directory (where .env.example lives)." >&2
  echo "pwd: $(pwd)" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo ">> .env not found — seeding from .env.example"
  cp .env.example .env
  # Replace CHANGE_ME placeholders with lab-only defaults
  sed -i.bak \
    -e 's|GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME.*|GF_SECURITY_ADMIN_PASSWORD=admin|' \
    -e 's|GF_SECURITY_SECRET_KEY=CHANGE_ME.*|GF_SECURITY_SECRET_KEY=lab-only-32bytes-0123456789abcdef0123456789|' \
    -e 's|GF_DATABASE_PASSWORD=CHANGE_ME.*|GF_DATABASE_PASSWORD=grafana-lab-db|' \
    -e 's|POSTGRES_ROOT_PASSWORD=CHANGE_ME.*|POSTGRES_ROOT_PASSWORD=grafana-lab-root|' \
    -e 's|RENDERER_AUTH_TOKEN=CHANGE_ME.*|RENDERER_AUTH_TOKEN=lab-only-renderer-token-32bytes|' \
    .env
  rm -f .env.bak
  echo ">> .env created with lab defaults"
fi

# Prefer 'docker compose' v2 plugin over legacy 'docker-compose'.
if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  COMPOSE=(docker-compose)
fi

COMPOSE_ARGS=(--env-file .env -f compose/docker-compose.yml -p grafana12-oss-lab)

case "$ACTION" in
  up)
    echo ">> Building images + starting stack (first run pulls ~1.5GB)..."
    "${COMPOSE[@]}" "${COMPOSE_ARGS[@]}" up -d --build
    echo
    echo ">> Waiting for Grafana /api/health (up to 2 min)..."
    for _ in $(seq 1 60); do
      if curl -fsS http://localhost:3012/api/health 2>/dev/null | grep -q '"database":"ok"'; then
        break
      fi
      sleep 2
    done
    "${COMPOSE[@]}" "${COMPOSE_ARGS[@]}" ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
    echo
    echo "  Grafana UI    → http://localhost:3012   (anonymous Admin, or admin/admin)"
    echo "  Prometheus UI → http://localhost:9092"
    echo "  Loki API      → http://localhost:3112"
    echo "  Tempo API     → http://localhost:3212"
    echo "  Pyroscope UI  → http://localhost:4042"
    echo "  Alloy UI      → http://localhost:12346"
    ;;
  down)   "${COMPOSE[@]}" "${COMPOSE_ARGS[@]}" down ;;
  reset)  "${COMPOSE[@]}" "${COMPOSE_ARGS[@]}" down -v --remove-orphans ;;
  status) "${COMPOSE[@]}" "${COMPOSE_ARGS[@]}" ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}' ;;
  logs)   "${COMPOSE[@]}" "${COMPOSE_ARGS[@]}" logs -f grafana ;;
  build)  "${COMPOSE[@]}" "${COMPOSE_ARGS[@]}" build --pull ;;
  *) echo "Unknown action: $ACTION"; echo "Valid: up | down | reset | status | logs | build"; exit 1 ;;
esac
