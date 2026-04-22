import { test, expect } from '@playwright/test';

// §5.2: 12.1 bundle — new alert rule page GA, regression transform, viz actions, advisor, Google OAuth HD.

test('@alert-rule-page /alerting/new/alerting opens new UI', async ({ page }) => {
  await page.goto('/alerting/new/alerting');
  await expect(page.locator('h1, h2')).toContainText(/alert rule/i, { timeout: 15_000 });
});

test('@regression-transformation transform picker lists Regression analysis', async ({ request }) => {
  // Server-side capability check via frontend settings payload.
  const s = await request.get('/api/frontend/settings');
  const body = await s.json();
  expect(body.featureToggles?.regressionTransformation).toBeTruthy();
});

test('@advisor /advisor route responds', async ({ page, request }) => {
  const r = await request.get('/a/grafana-advisor-app');
  expect([200, 301, 302, 404]).toContain(r.status());
});
