ARG PYROSCOPE_TAG=1.8.0
FROM grafana/pyroscope:${PYROSCOPE_TAG}
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} https_proxy=${HTTPS_PROXY} no_proxy=${NO_PROXY}
COPY pyroscope-config.yaml /etc/pyroscope/pyroscope-config.yaml
