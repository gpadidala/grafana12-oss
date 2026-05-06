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
# /usr/share/grafana-dashboards is OUTSIDE the /var/lib/grafana named volume
# so baked dashboards stay visible even when the volume is pre-populated.
COPY --chown=grafana:root lab-dashboards/   /usr/share/grafana-dashboards/

# Bake the plugins required by provisioned datasources + dashboards INTO the
# image. The .zip files ship in the repo (lab/grafana/plugins-bundle/) so the
# build does not need internet access — works on corporate networks behind a
# TLS-intercepting proxy where `grafana cli plugins install` fails with
# "x509: certificate signed by unknown authority".
ARG TARGETARCH
COPY --chown=grafana:root plugins-bundle/ /tmp/plugins-bundle/
USER root
RUN mkdir -p /var/lib/grafana/plugins && \
    if [ "$TARGETARCH" = "arm64" ]; then \
      unzip -q /tmp/plugins-bundle/infinity-arm64.zip -d /var/lib/grafana/plugins && \
      unzip -q /tmp/plugins-bundle/polystat-arm64.zip -d /var/lib/grafana/plugins && \
      unzip -q /tmp/plugins-bundle/clock-arm64.zip    -d /var/lib/grafana/plugins ; \
    else \
      unzip -q /tmp/plugins-bundle/infinity.zip -d /var/lib/grafana/plugins && \
      unzip -q /tmp/plugins-bundle/polystat.zip -d /var/lib/grafana/plugins && \
      unzip -q /tmp/plugins-bundle/clock.zip    -d /var/lib/grafana/plugins ; \
    fi && \
    rm -rf /tmp/plugins-bundle && \
    chown -R grafana:root /var/lib/grafana/plugins
USER grafana
