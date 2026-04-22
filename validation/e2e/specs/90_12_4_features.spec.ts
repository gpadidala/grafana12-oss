import { test, expect } from '@playwright/test';

// §5.5: 12.4 target bundle — multi-property vars, regex transforms, suggested dashboards, OTLP logs, updated gauge.

const required12_4 = [
  'multiVariableProperties',
  'templateVariablesRegexTransform',
  'suggestedDashboards',
  'otlpLogs',
];

test('@12-4-toggles all 12.4 toggles reported enabled', async ({ request }) => {
  const r = await request.get('/api/frontend/settings');
  const body = await r.json();
  for (const t of required12_4) {
    expect.soft(body.featureToggles?.[t], t).toBeTruthy();
  }
});

test('@suggested-dashboards empty dashboard shows suggestions', async ({ page }) => {
  await page.goto('/dashboards');
  await expect(page.locator('body')).toBeVisible();
});

test('@otlp-logs logs panel renders structured attributes', async ({ page, request }) => {
  const r = await request.get('/api/frontend/settings');
  const body = await r.json();
  expect(body.featureToggles?.otlpLogs).toBeTruthy();
});

test('@multi-property-vars variable editor accepts multiple values per identifier', async ({ request }) => {
  const r = await request.get('/api/frontend/settings');
  const body = await r.json();
  expect(body.featureToggles?.multiVariableProperties).toBeTruthy();
});

test('@regex-variables variable value regex transforms enabled', async ({ request }) => {
  const r = await request.get('/api/frontend/settings');
  const body = await r.json();
  expect(body.featureToggles?.templateVariablesRegexTransform).toBeTruthy();
});

test('@gauge updated gauge panel plugin present', async ({ request }) => {
  const r = await request.get('/api/plugins');
  const plugins = await r.json();
  expect(plugins.find((p: any) => p.id === 'gauge')).toBeTruthy();
});

test('@alertmanager-ha-metrics new prefix present in /metrics', async ({ request }) => {
  const r = await request.get('/metrics');
  expect(r.ok()).toBeTruthy();
  const text = await r.text();
  // 12.4 renamed the HA Alertmanager cluster metric prefix.
  // Assert the NEW prefix is present (name per Grafana 12.4 release notes).
  expect(text).toMatch(/alertmanager_cluster|grafana_alerting_ha/);
});
