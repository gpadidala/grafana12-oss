#!/usr/bin/env python3
"""Download curated advanced dashboards from grafana.com and normalize them for the lab.

For each (id, revision, datasource-map) entry in CURATED:
  1. GET https://grafana.com/api/dashboards/{id}/revisions/{rev}/download
  2. Strip import-only fields (__inputs, __requires, __elements, inputs).
  3. Rewrite every ${DS_FOO} placeholder to the matching lab datasource UID.
  4. Rewrite every "datasource" field to the {type, uid} shape.
  5. Prefix the uid with "g12-" to avoid collision with our own stubs.
  6. Rewrite title to "[grafana.com #<id>] <title>" so they're easy to spot.
  7. Write to lab/grafana/lab-dashboards/advanced/<slug>.json

Corporate proxies: honors HTTPS_PROXY / HTTP_PROXY from env.

Run:  python3 lab/scripts/fetch_advanced_dashboards.py
"""
from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError


# (grafana.com dashboard id, revision or 'latest', datasource map)
# The datasource map translates the dashboard's ${DS_*} input names to our lab UIDs.
CURATED: list[tuple[int, str, dict[str, dict[str, str]]]] = [
    # --- Grafana / platform self-monitoring (will show real data) ---
    ( 3590, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),   # Grafana Dashboard
    (12019, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),   # Grafana metrics (by Alex)
    # --- Prometheus itself ---
    ( 3662, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),   # Prometheus 2.0 Overview
    (11074, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),   # Prometheus Overview (Node + Prom)
    # --- Loki ---
    (13639, "latest", {"DS_LOKI": {"type": "loki", "uid": "loki"}}),               # Logs/App
    (17781, "latest", {                                                             # Loki Dashboard quick search
        "DS_LOKI": {"type": "loki", "uid": "loki"},
        "DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"},
    }),
    # --- Tempo ---
    (17975, "latest", {"DS_TEMPO": {"type": "tempo", "uid": "tempo"}}),             # Tempo / Writes
    # --- Node Exporter Full (the classic — partially functional without node_exporter) ---
    ( 1860, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),
    # --- Docker / cAdvisor ---
    (  193, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),    # Docker monitoring
    (14282, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),    # cAdvisor-exporter
    # --- Postgres (needs postgres_exporter — we add one in compose) ---
    ( 9628, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),    # PostgreSQL Database
    # --- Alertmanager ---
    (    9, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),    # Prometheus Stats
    # --- k6 / load testing vibes ---
    ( 2587, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),    # k6 Load Testing Results
    # --- Kubernetes cluster (aspirational — will be "No data" without k8s) ---
    (15757, "latest", {"DS_PROMETHEUS": {"type": "prometheus", "uid": "prom"}}),    # K8s / Views / Global
]


DS_URL = "https://grafana.com/api/dashboards/{id}/revisions/{rev}/download"


def http_get(url: str) -> bytes:
    """Fetch a URL, tolerating corporate SSL interception.

    Order: urllib (verified) → urllib (unverified) → curl with -k.
    Lab-only insecure fallback — we only hit grafana.com.
    """
    req = urllib.request.Request(url, headers={
        "User-Agent": "grafana12-oss/lab fetcher",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except (URLError, HTTPError) as e:
        if isinstance(e, HTTPError) and e.code >= 400:
            raise
        # SSL cert chain failure → retry unverified.
        ctx = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                return r.read()
        except Exception:
            # Final fallback: curl -k (uses system trust + insecure).
            out = subprocess.run(
                ["curl", "-fsSL", "-k", "--max-time", "30", url],
                capture_output=True, check=True,
            )
            return out.stdout


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "dashboard"


def rewrite_datasource_field(val, ds_map: dict[str, dict[str, str]]):
    """Normalize a panel/variable `datasource` field.

    Accepts string placeholders `${DS_FOO}`, bare strings, or dict forms.
    Returns the {type, uid} dict form.
    """
    if isinstance(val, str):
        m = re.match(r"\$\{?([A-Z0-9_]+)\}?$", val)
        if m and m.group(1) in ds_map:
            return dict(ds_map[m.group(1)])
        # Bare string like "Prometheus" / "prometheus" — best-effort map by plugin name
        guess = {"prometheus": "prom", "loki": "loki", "tempo": "tempo", "pyroscope": "pyroscope"}
        u = guess.get(val.lower())
        if u:
            return {"type": val.lower(), "uid": u}
        return val
    if isinstance(val, dict):
        uid = val.get("uid", "")
        m = re.match(r"\$\{?([A-Z0-9_]+)\}?$", str(uid))
        if m and m.group(1) in ds_map:
            return dict(ds_map[m.group(1)])
    return val


def walk(obj, ds_map):
    if isinstance(obj, dict):
        if "datasource" in obj:
            obj["datasource"] = rewrite_datasource_field(obj["datasource"], ds_map)
        # A few dashboards set the placeholder at the variable query level.
        for k, v in list(obj.items()):
            obj[k] = walk(v, ds_map)
        return obj
    if isinstance(obj, list):
        return [walk(x, ds_map) for x in obj]
    if isinstance(obj, str):
        # Substitute raw placeholders anywhere (queries, titles, etc.)
        out = obj
        for name, mapping in ds_map.items():
            out = out.replace("${" + name + "}", mapping["uid"])
            out = out.replace("$" + name, mapping["uid"])
        return out
    return obj


def normalize(dash: dict, ds_map: dict[str, dict[str, str]], gid: int) -> dict:
    # Strip import-only blocks.
    for key in ("__inputs", "__requires", "__elements", "inputs"):
        dash.pop(key, None)
    dash = walk(dash, ds_map)

    # Re-uid + title so we never collide with our own stubs.
    base_uid = dash.get("uid") or slugify(str(dash.get("title", f"gdot-{gid}")))
    dash["uid"] = f"g12-{base_uid}"[:40]
    title = dash.get("title", f"grafana.com/{gid}")
    if not title.startswith("[grafana.com"):
        dash["title"] = f"[grafana.com #{gid}] {title}"

    # Tag so we can filter them out later.
    tags = set(dash.get("tags") or [])
    tags.update({"grafana.com", "advanced"})
    dash["tags"] = sorted(tags)

    # Bump schemaVersion if present and low — 12.4 will auto-migrate anyway.
    if isinstance(dash.get("schemaVersion"), int) and dash["schemaVersion"] < 36:
        dash["schemaVersion"] = 36

    return dash


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "grafana" / "lab-dashboards" / "advanced"
    out_dir.mkdir(parents=True, exist_ok=True)

    ok, failed = 0, 0
    for gid, rev, ds_map in CURATED:
        try:
            raw = http_get(DS_URL.format(id=gid, rev=rev))
            dash = json.loads(raw)
            dash = normalize(dash, ds_map, gid)
            title = dash.get("title", f"dashboard-{gid}")
            path = out_dir / f"{gid:05d}-{slugify(title)}.json"
            path.write_text(json.dumps(dash, indent=2))
            print(f"  OK  {gid:>5}  {title}  ({len(dash.get('panels', []))} panels)")
            ok += 1
        except HTTPError as e:
            print(f"  FAIL {gid:>5}  HTTP {e.code}")
            failed += 1
        except URLError as e:
            print(f"  FAIL {gid:>5}  {e.reason}  (corporate proxy? set HTTPS_PROXY)")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {gid:>5}  {type(e).__name__}: {e}")
            failed += 1

    print(f"\nFetched {ok} / {ok + failed} dashboards into {out_dir}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
