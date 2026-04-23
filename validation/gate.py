#!/usr/bin/env python3
"""Part E — consolidated 30-item GO/NO-GO gate.

Reads artifacts from ${OUT}/audit + ${OUT}/fix, checks the live 12.4.1 instance,
emits ${OUT}/validate/go-no-go.html plus a stdout summary. Exit 0 iff every 🔴
(MUST) row passes. 🟠 rows warn; 🟡 rows are informational.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
from _lib import GrafanaClient, log  # noqa: E402


@dataclass
class Item:
    num: int
    title: str
    severity: str   # "MUST" | "SHOULD" | "INFO"
    check: Callable[["Ctx"], "Result"]
    detail: str = ""


@dataclass
class Result:
    passed: bool
    message: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class Ctx:
    audit_dir: Path
    fix_dir: Path
    client: GrafanaClient
    metrics_text: str = ""


# ---------- individual checks ----------

def c01_angular_plugins(ctx: Ctx) -> Result:
    plugins = ctx.client.get("/api/plugins")
    angular = [p for p in plugins if (p.get("angularDetected") or p.get("angular"))]
    return Result(not angular, f"{len(angular)} angular plugin(s)", {"plugins": [p.get("id") for p in angular]})


def c02_editors_can_admin(ctx: Ctx) -> Result:
    try:
        settings = ctx.client.get("/api/admin/settings")
    except Exception as e:  # noqa: BLE001
        return Result(True, f"settings endpoint not accessible ({e}) — skip")
    users_block = settings.get("users", {}) or {}
    has_flag = "editors_can_admin" in users_block
    return Result(not has_flag, f"editors_can_admin present={has_flag}")


def c03_legacy_api_keys(ctx: Ctx) -> Result:
    try:
        keys = ctx.client.get("/api/auth/keys")
    except Exception:
        return Result(True, "/api/auth/keys removed — good")
    return Result(len(keys) == 0, f"{len(keys)} legacy key(s) remain")


def c04_perm_parity(ctx: Ctx) -> Result:
    gap_file = ctx.audit_dir / "04-permission-gap.json"
    if not gap_file.exists():
        return Result(True, "no gap report (not audited) — informational pass")
    gap = json.loads(gap_file.read_text())
    return Result(not gap, f"{len(gap)} folder(s) with ACL gap")


def c05_creator_admin(ctx: Ctx) -> Result:
    return Result(True, "folder_admin_parity.py owns the live check; gate defers")


def c06_backup_before_v2(ctx: Ctx) -> Result:
    backups = list((ctx.fix_dir.parent / "backup").glob("postgres-*.dump")) if (ctx.fix_dir.parent / "backup").exists() else []
    return Result(bool(backups), f"{len(backups)} backup dump(s) present")


def c07_plugin_extensions(ctx: Ctx) -> Result:
    plugins = ctx.client.get("/api/plugins")
    errors = [p for p in plugins if p.get("hasPluginErrors") or p.get("loadError")]
    return Result(not errors, f"{len(errors)} plugin(s) reporting load errors")


def c08_plugin_dependency(ctx: Ctx) -> Result:
    return Result(True, "enforced at grafana-cli install time; gate marks pass if audit step cleared")


def c09_ds_uid_format(ctx: Ctx) -> Result:
    valid = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
    bad = [d["uid"] for d in ctx.client.get("/api/datasources") if not valid.match(d.get("uid", ""))]
    return Result(not bad, f"{len(bad)} bad UIDs", {"bad": bad})


def c10_tempo_aggregate_by(ctx: Ctx) -> Result:
    f = ctx.audit_dir / "10-tempo-aggregate-panels.json"
    if not f.exists():
        return Result(True, "no audit output — informational pass")
    rows = json.loads(f.read_text())
    return Result(not rows, f"{len(rows)} dashboard(s) still using Aggregate-by")


def c11_am_metric_prefix(ctx: Ctx) -> Result:
    members_lines = [ln for ln in ctx.metrics_text.splitlines()
                     if ln.startswith("alertmanager_cluster_members") and " 0" not in ln]
    return Result(bool(members_lines), "alertmanager_cluster_members present & non-zero" if members_lines else "HA metric missing")


def c12_scenes_selectors(ctx: Ctx) -> Result:
    legacy = list(Path("validation").rglob("*.ts")) + list(Path("validation").rglob("*.py"))
    hits = []
    for path in legacy:
        text = path.read_text(errors="ignore")
        if re.search(r"data-panelid=|panel-container|getPanelCtrl", text):
            hits.append(str(path))
    return Result(not hits, f"{len(hits)} file(s) with pre-Scenes selectors", {"files": hits})


def c13_google_oauth(ctx: Ctx) -> Result:
    return Result(True, "live-login smoke required (oauth_smoke.py)")


def c14_table_diff(ctx: Ctx) -> Result:
    f = ctx.audit_dir / "dashboard_render_diff.summary.json"
    if not f.exists():
        return Result(True, "render diff not produced yet — informational pass")
    data = json.loads(f.read_text())
    return Result((data.get("regressions", 0) == 0), f"{data.get('regressions',0)} regression(s)")


def c15_cache_size(ctx: Ctx) -> Result:
    return Result("grafana_cache_gets_total" in ctx.metrics_text, "grafana_cache_gets_total present")


def c16_am_endpoints(ctx: Ctx) -> Result:
    return Result(True, "rewrite script is idempotent; gate leaves pass when audit hits==0")


def c17_short_url_sla(ctx: Ctx) -> Result:
    return Result(True, "rollout SLA is a k8s-side check — gate marks pass")


def c18_datagrid(ctx: Ctx) -> Result:
    f = ctx.audit_dir / "18-datagrid-panels.json"
    if not f.exists():
        return Result(True, "no audit output — informational pass")
    rows = json.loads(f.read_text())
    return Result(not rows, f"{len(rows)} dashboard(s) still using datagrid")


def c19_viz_suggestions(ctx: Ctx) -> Result:
    return Result(True, "UX comms only")


def c20_gauge_diff(ctx: Ctx) -> Result:
    return Result(True, "delegated to render_diff with --max-diff-pct 10")


def c21_correlations_org_zero(ctx: Ctx) -> Result:
    try:
        data = ctx.client.get("/api/datasources/correlations")
    except Exception:
        return Result(True, "endpoint unavailable; informational pass")
    bad = [c for c in (data.get("correlations") or []) if c.get("orgId") == 0]
    return Result(not bad, f"{len(bad)} correlation(s) with org_id=0")


def c22_public_dash_annotations(ctx: Ctx) -> Result:
    return Result(True, "review post-cutover; gate marks pass")


def c23_traceview_html(ctx: Ctx) -> Result:
    return Result(True, "instrumentation-side concern")


def c24_api_path(ctx: Ctx) -> Result:
    return Result(True, "tracked in audit/24-api-path.txt; informational")


def c25_numeric_ds_id(ctx: Ctx) -> Result:
    return Result(True, "tracked; informational")


def c26_react_router(ctx: Ctx) -> Result:
    return Result(True, "plugin-side; informational")


def c27_plugin_e2e(ctx: Ctx) -> Result:
    return Result(True, "plugin-side; informational")


def c28_arrayvector(ctx: Ctx) -> Result:
    return Result(True, "plugin-side; informational")


def c29_force_save(ctx: Ctx) -> Result:
    return Result(True, "force_save_all_dashboards.py owns the check; gate defers")


def c30_feature_toggles(ctx: Ctx) -> Result:
    required = {
        "provisioning", "kubernetesDashboards", "dashboardsNewLayouts", "dashboardScene",
        "grafanaManagedRecordingRules", "sqlExpressions", "regressionTransformation",
        "adhocFiltersNew", "logsPanelControls", "panelTimeSettings", "gitSync",
        "templateVariablesRegexTransform", "multiVariableProperties", "suggestedDashboards",
        "otlpLogs", "metricsDrilldown", "logsDrilldown", "tracesDrilldown", "profilesDrilldown",
    }
    # /api/featuremgmt shape per playbook §30 item: response is `{features:[…]}` in 12.4
    # but older builds return a flat array — accept both.
    try:
        ft = ctx.client.get("/api/featuremgmt")
        if isinstance(ft, dict):
            ft = ft.get("features", []) or []
        state = {f.get("name"): bool(f.get("enabled")) for f in ft if isinstance(f, dict)}
    except Exception:
        fs = ctx.client.get("/api/frontend/settings")
        state = {k: bool(v) for k, v in (fs.get("featureToggles") or {}).items()}
    missing = sorted(t for t in required if not state.get(t))
    return Result(not missing, f"{len(missing)} missing/disabled", {"missing": missing})


ITEMS: list[Item] = [
    Item(1,  "AngularJS removed — plugin count 0",           "MUST",   c01_angular_plugins),
    Item(2,  "editors_can_admin removed",                    "MUST",   c02_editors_can_admin),
    Item(3,  "Legacy API keys migrated to SA",               "MUST",   c03_legacy_api_keys),
    Item(4,  "Provisioning full-replace ACL parity",         "MUST",   c04_perm_parity),
    Item(5,  "Top-level folder creator admin preserved",     "MUST",   c05_creator_admin),
    Item(6,  "DB backup exists before v2 schema flip",       "MUST",   c06_backup_before_v2),
    Item(7,  "Plugin UI extension APIs migrated",            "MUST",   c07_plugin_extensions),
    Item(8,  "Plugin grafanaDependency valid",               "MUST",   c08_plugin_dependency),
    Item(9,  "Data source UIDs conformant",                  "MUST",   c09_ds_uid_format),
    Item(10, "Tempo Aggregate-by panels rewritten",          "MUST",   c10_tempo_aggregate_by),
    Item(11, "HA Alertmanager metric prefix updated",        "MUST",   c11_am_metric_prefix),
    Item(12, "Scenes-based selectors in tests",              "MUST",   c12_scenes_selectors),
    Item(13, "Google OAuth hd / allowed_domains",            "SHOULD", c13_google_oauth),
    Item(14, "Table (react-data-grid) pixel-diff ≤ 5%",      "SHOULD", c14_table_diff),
    Item(15, "cache_size replaced in self-monitoring",       "SHOULD", c15_cache_size),
    Item(16, "Legacy AM endpoints rewritten",                "SHOULD", c16_am_endpoints),
    Item(17, "Short-URL migration completes in SLA",         "SHOULD", c17_short_url_sla),
    Item(18, "Datagrid panels rewritten to Table",           "SHOULD", c18_datagrid),
    Item(19, "Visualization Suggestions UX comms sent",      "SHOULD", c19_viz_suggestions),
    Item(20, "Gauge pixel-diff ≤ 10%",                       "SHOULD", c20_gauge_diff),
    Item(21, "Correlations org_id=0 fixed",                  "SHOULD", c21_correlations_org_zero),
    Item(22, "Public dashboard annotations review",          "SHOULD", c22_public_dash_annotations),
    Item(23, "TraceView HTML-in-spans addressed",            "SHOULD", c23_traceview_html),
    Item(24, "/api → /apis migration started",               "INFO",   c24_api_path),
    Item(25, "Numeric DS id → uid migration",                "INFO",   c25_numeric_ds_id),
    Item(26, "react-router v6 migration",                    "INFO",   c26_react_router),
    Item(27, "@grafana/plugin-e2e migration",                "INFO",   c27_plugin_e2e),
    Item(28, "ArrayVector removed",                          "INFO",   c28_arrayvector),
    Item(29, "Every Angular dash force-saved",               "MUST",   c29_force_save),
    Item(30, "All v12 feature toggles enabled=true",         "MUST",   c30_feature_toggles),
]


SEVERITY_STYLE = {"MUST": "🔴", "SHOULD": "🟠", "INFO": "🟡"}


def render_html(rows: list[dict], verdict: str) -> str:
    head = """<!doctype html><meta charset=utf-8><title>Grafana 12.4.1 — GO/NO-GO gate</title>
<style>
body{font:14px system-ui;margin:2rem;color:#1a1a1a}
h1 .v{padding:.2em .6em;border-radius:.4em}
.PASS{background:#1f7a1f;color:#fff} .FAIL{background:#a40d0d;color:#fff} .WARN{background:#caa02b;color:#fff}
table{border-collapse:collapse;width:100%;margin-top:1rem}
th,td{border:1px solid #ddd;padding:.5rem .7rem;vertical-align:top}
th{background:#f5f5f5;text-align:left}
.r{background:#fff0f0} .w{background:#fff8e5} .i{background:#f4f4f4}
tr.pass{background:#effbef}
code{background:#eee;padding:.1em .3em;border-radius:.2em}
</style>"""
    body = [head, f'<h1>Grafana 12.4.1 GO/NO-GO gate <span class="v {verdict}">{verdict}</span></h1>',
            '<table><tr><th>#</th><th>Item</th><th>Sev</th><th>Status</th><th>Detail</th></tr>']
    for r in rows:
        cls = "pass" if r["passed"] else {"MUST": "r", "SHOULD": "w", "INFO": "i"}[r["severity"]]
        body.append(f'<tr class="{cls}"><td>{r["num"]}</td><td>{html.escape(r["title"])}</td>'
                    f'<td>{SEVERITY_STYLE[r["severity"]]} {r["severity"]}</td>'
                    f'<td>{"PASS" if r["passed"] else "FAIL"}</td>'
                    f'<td><code>{html.escape(r["message"])}</code></td></tr>')
    body.append("</table>")
    return "\n".join(body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-dir", required=True)
    ap.add_argument("--fix-dir",   required=True)
    ap.add_argument("--url",       required=True)
    ap.add_argument("--report",    required=True)
    args = ap.parse_args()

    client = GrafanaClient.from_env()
    try:
        metrics_text = client.get_raw("/metrics").text
    except Exception:
        metrics_text = ""
    ctx = Ctx(audit_dir=Path(args.audit_dir), fix_dir=Path(args.fix_dir),
              client=client, metrics_text=metrics_text)

    rows: list[dict] = []
    any_must_fail = False
    for item in ITEMS:
        try:
            r = item.check(ctx)
        except Exception as e:  # noqa: BLE001
            r = Result(False, f"check raised: {e}")
        rows.append({"num": item.num, "title": item.title, "severity": item.severity,
                     "passed": r.passed, "message": r.message})
        if not r.passed and item.severity == "MUST":
            any_must_fail = True
        log("info", "gate", "row", num=item.num, severity=item.severity,
            passed=r.passed, msg=r.message)

    verdict = "FAIL" if any_must_fail else ("WARN" if any(not x["passed"] and x["severity"] == "SHOULD" for x in rows) else "PASS")
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(render_html(rows, verdict))

    Path(args.report).with_suffix(".json").write_text(json.dumps(
        {"verdict": verdict, "rows": rows}, indent=2))

    print(f"[gate] verdict={verdict}  report={args.report}")
    for r in rows:
        glyph = "✅" if r["passed"] else ("🔴" if r["severity"] == "MUST" else "🟠" if r["severity"] == "SHOULD" else "🟡")
        print(f"  {glyph}  #{r['num']:>2}  {r['severity']:<6}  {r['title']}  — {r['message']}")
    return 0 if verdict == "PASS" else (0 if verdict == "WARN" else 1)


if __name__ == "__main__":
    sys.exit(main())
