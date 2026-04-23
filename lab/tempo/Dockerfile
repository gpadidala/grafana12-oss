ARG TEMPO_TAG=2.6.0
FROM grafana/tempo:${TEMPO_TAG}
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} https_proxy=${HTTPS_PROXY} no_proxy=${NO_PROXY}
COPY tempo-config.yaml /etc/tempo/tempo-config.yaml
