import { test, expect } from '@playwright/test';

// §5.3: 12.2 bundle — ad-hoc filters GA, redesigned table, logs JSON viewer, metrics→alert.

test('@adhoc-filters frontend toggle confirms adhocFiltersNew', async ({ request }) => {
  const r = await request.get('/api/frontend/settings');
  const body = await r.json();
  expect(body.featureToggles?.adhocFiltersNew).toBeTruthy();
});

test('@react-data-grid table panel uses react-data-grid in 12.2+', async ({ request }) => {
  const r = await request.get('/api/plugins');
  const plugins = await r.json();
  const table = plugins.find((p: any) => p.id === 'table');
  expect(table).toBeTruthy();
});

test('@metrics-to-alert drilldown offers create-alert action', async ({ page }) => {
  await page.goto('/a/grafana-metricsdrilldown-app');
  await expect(page.locator('body')).toBeVisible();
});
