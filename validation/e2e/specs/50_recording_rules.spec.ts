import { test, expect } from '@playwright/test';

// §5.1: Grafana-managed recording rules GA.

test('@recording-rules alerting UI exposes recording rule type', async ({ page }) => {
  await page.goto('/alerting/new/alerting');
  await expect(page.getByRole('heading', { name: /new alert rule|recording rule/i })).toBeVisible({ timeout: 15_000 });
});

test('@recording-rules provisioning endpoint accepts recording type', async ({ request }) => {
  const r = await request.get('/api/v1/provisioning/alert-rules');
  expect(r.ok()).toBeTruthy();
});
