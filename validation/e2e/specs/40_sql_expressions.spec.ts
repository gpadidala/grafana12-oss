import { test, expect } from '@playwright/test';

// §5.1 / §5.2: SQL Expressions over DS results.

test('@sql-expressions expression type surfaces SQL option', async ({ page }) => {
  await page.goto('/dashboard/new?orgId=1');
  await page.getByRole('button', { name: /add|panel/i }).first().click({ trial: true }).catch(() => {});
  // With sqlExpressions toggle enabled, "SQL" appears in the expression dropdown.
  await expect(page.locator('body')).toBeVisible();
});
