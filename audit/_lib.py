"""Shared helpers for audit scripts.

Structured JSON logging, Grafana HTTP client, artifact writers.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


RUN_ID = os.environ.get("RUN_ID") or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def log(level: str, step: str, event: str, **detail: Any) -> None:
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "level": level,
        "run_id": RUN_ID,
        "step": step,
        "event": event,
        "detail": detail,
    }
    print(json.dumps(rec), flush=True)


@dataclass
class GrafanaClient:
    base_url: str
    token: str
    org_id: str = "1"
    session: requests.Session | None = None

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "X-Grafana-Org-Id": self.org_id,
                "Accept": "application/json",
                "User-Agent": f"grafana12-oss/audit run={RUN_ID}",
            }
        )

    @classmethod
    def from_env(cls) -> "GrafanaClient":
        url = os.environ.get("GRAFANA_URL")
        tok = os.environ.get("GRAFANA_SA_TOKEN")
        org = os.environ.get("GRAFANA_ORG_ID", "1")
        if not url or not tok:
            log("fatal", "init", "missing_env", required=["GRAFANA_URL", "GRAFANA_SA_TOKEN"])
            sys.exit(2)
        return cls(base_url=url.rstrip("/"), token=tok, org_id=org)

    def get(self, path: str, **kw: Any) -> Any:
        r = self.session.get(f"{self.base_url}{path}", timeout=30, **kw)
        r.raise_for_status()
        return r.json()

    def get_raw(self, path: str, **kw: Any) -> requests.Response:
        r = self.session.get(f"{self.base_url}{path}", timeout=30, **kw)
        r.raise_for_status()
        return r


def out_dir(override: str | None = None) -> Path:
    p = Path(override) if override else Path("out") / f"audit-{RUN_ID}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))
