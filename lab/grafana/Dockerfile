# Bakes provisioning + dashboards into the Grafana 12.4 image so the lab boots
# cleanly on macOS Docker Desktop without relying on /Volumes bind mounts.
#
# Usage: compose builds this automatically. See compose/docker-compose.yml.
#
# Argument is injected at build time so the Dockerfile always tracks .env.
ARG GRAFANA_IMAGE_TAG=12.4.3
FROM grafana/grafana-oss:${GRAFANA_IMAGE_TAG}

COPY --chown=grafana:root lab-provisioning/ /etc/grafana/provisioning/
COPY --chown=grafana:root lab-dashboards/   /var/lib/grafana/dashboards/
