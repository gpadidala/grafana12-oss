#!/usr/bin/env python3
"""Item 3 — migrate every legacy API key to a Service Account + token.

Legacy /api/auth/keys are still usable in 12.4.1 but their role actions were
removed in 12.3. Each key gets a paired service account + fresh token; the
mapping is written so owners can rotate consumers via Vault before cutover.

Destructive against the 11.6.4 side. Gated by CONFIRM=yes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--inventory", required=True, help="JSON from /api/auth/keys")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if os.environ.get("CONFIRM") != "yes":
        print("CONFIRM=yes required — this creates service accounts + tokens", file=sys.stderr)
        return 2

    c = GrafanaClient.from_env()
    keys = json.loads(Path(args.inventory).read_text())
    mapping: list[dict] = []
    for k in keys:
        name = f"sa-migrated-{k.get('name','unknown')}"
        role = k.get("role", "Viewer")
        try:
            sa = c.session.post(
                f"{c.base_url}/api/serviceaccounts",
                json={"name": name, "role": role, "isDisabled": False},
                timeout=30,
            ).json()
            tok = c.session.post(
                f"{c.base_url}/api/serviceaccounts/{sa['id']}/tokens",
                json={"name": f"{name}-token"},
                timeout=30,
            ).json()
            mapping.append({
                "legacy_key_id": k.get("id"), "legacy_key_name": k.get("name"),
                "service_account_id": sa.get("id"), "service_account_name": name,
                "token": tok.get("key"),
            })
            log("info", "migrate_api_keys_to_sa", "migrated", legacy=k.get("name"), sa=name)
        except Exception as e:  # noqa: BLE001
            log("warn", "migrate_api_keys_to_sa", "failed", legacy=k.get("name"), err=str(e))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(mapping, indent=2))
    log("info", "migrate_api_keys_to_sa", "done", count=len(mapping))
    return 0


if __name__ == "__main__":
    sys.exit(main())
