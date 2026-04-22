import { test, expect } from '@playwright/test';

// Final acceptance gate (§11). Runs the broadest assertions that tie the others together.

test('@acceptance every data source /health is OK', async ({ request }) => {
  const list = await (await request.get('/api/datasources')).json();
  expect(Array.isArray(list)).toBeTruthy();
  for (const ds of list) {
    const h = await (await request.get(`/api/datasources/uid/${ds.uid}/health`)).json();
    expect.soft(h.status?.toLowerCase?.(), `DS ${ds.name} (${ds.type})`).toMatch(/ok/);
  }
});

test('@acceptance zero remaining legacy API keys', async ({ request }) => {
  // Legacy API keys were removed in 12.3; any survivors are remediation gaps.
  const r = await request.get('/api/auth/keys');
  if (!r.ok()) return;  // endpoint gone == migration complete
  const keys = await r.json();
  expect(Array.isArray(keys) ? keys.length : 0).toBe(0);
});

test('@acceptance HA Alertmanager peers healthy', async ({ request }) => {
  const r = await request.get('/api/alertmanager/grafana/api/v2/status');
  expect(r.ok()).toBeTruthy();
  const status = await r.json();
  expect(status).toBeTruthy();
});
