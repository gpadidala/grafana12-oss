import { test, expect, request } from '@playwright/test';

test('@smoke /api/health database=ok', async ({ request }) => {
  const r = await request.get('/api/health');
  expect(r.ok()).toBeTruthy();
  const body = await r.json();
  expect(body.database).toBe('ok');
  expect(body.version).toMatch(/^12\.4\./);
});

test('@smoke every required feature toggle is enabled', async ({ request }) => {
  const required = [
    'provisioning','kubernetesDashboards','dashboardsNewLayouts','dashboardScene',
    'grafanaManagedRecordingRules','sqlExpressions','regressionTransformation',
    'adhocFiltersNew','logsPanelControls','panelTimeSettings','gitSync',
    'templateVariablesRegexTransform','multiVariableProperties','suggestedDashboards',
    'otlpLogs','metricsDrilldown','logsDrilldown','tracesDrilldown','profilesDrilldown',
  ];
  const r = await request.get('/api/featuremgmt');
  expect(r.ok()).toBeTruthy();
  const toggles = await r.json();
  const state = Object.fromEntries(toggles.map((t: any) => [t.name, !!t.enabled]));
  for (const name of required) {
    expect.soft(state[name], `toggle ${name}`).toBe(true);
  }
});

test('@smoke zero Angular panels remain', async ({ request }) => {
  const ANG = new Set(['graph','singlestat','table-old','grafana-piechart-panel','grafana-worldmap-panel']);
  const s = await request.get('/api/search?type=dash-db&limit=5000');
  expect(s.ok()).toBeTruthy();
  const dashes = await s.json();
  let angular = 0;
  for (const row of dashes) {
    const d = await (await request.get(`/api/dashboards/uid/${row.uid}`)).json();
    for (const p of (d?.dashboard?.panels ?? [])) {
      if (ANG.has(p.type)) angular++;
    }
  }
  expect(angular, 'angular panel count must be zero').toBe(0);
});
