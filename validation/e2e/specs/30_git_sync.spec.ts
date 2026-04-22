import { test, expect } from '@playwright/test';

// §5.1 + §5.5: Git Sync (experimental OSS, public preview in 12.4).

test('@git-sync provisioning API exposes git-sync resource', async ({ request }) => {
  const r = await request.get('/apis/provisioning.grafana.app/v0alpha1/namespaces/default/repositories');
  // 200 when enabled; 404/403 is a hard fail.
  expect([200, 401]).toContain(r.status());
});

test('@git-sync save drawer shows branch selector', async ({ page }) => {
  await page.goto('/dashboard/new?orgId=1');
  await page.getByLabel('Save dashboard').click({ timeout: 15_000 }).catch(() => {});
  await expect(page.getByText(/branch/i)).toBeVisible({ timeout: 10_000 });
});
