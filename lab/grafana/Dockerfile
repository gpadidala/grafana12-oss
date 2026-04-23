# Bakes provisioning + dashboards into the Grafana 12.4 image so the lab boots
# cleanly on macOS Docker Desktop without /Volumes bind mounts and inside a
# corporate proxy (proxy args passed through at build time).
ARG GRAFANA_IMAGE_TAG=12.4.1
FROM grafana/grafana-oss:${GRAFANA_IMAGE_TAG}

# Proxy passthrough — only takes effect if you set these in .env.
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY}

COPY --chown=grafana:root lab-provisioning/ /etc/grafana/provisioning/
COPY --chown=grafana:root lab-dashboards/   /var/lib/grafana/dashboards/
