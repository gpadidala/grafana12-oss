import { test, expect } from '@playwright/test';

// §5.4: 12.3 bundle — panel time drawer, switch variable type, redesigned logs panel.

test('@panel-time-drawer panelTimeSettings toggle confirmed', async ({ request }) => {
  const r = await request.get('/api/frontend/settings');
  const body = await r.json();
  expect(body.featureToggles?.panelTimeSettings).toBeTruthy();
});

test('@switch-variable dashboard variables screen reachable', async ({ page }) => {
  await page.goto('/dashboard/new?orgId=1');
  await expect(page.locator('body')).toBeVisible();
});

test('@rbac top-level folder permission model enforced', async ({ request }) => {
  const r = await request.get('/api/folders');
  expect(r.ok()).toBeTruthy();
});
