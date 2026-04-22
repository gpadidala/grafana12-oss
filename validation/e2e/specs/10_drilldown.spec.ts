import { test, expect } from '@playwright/test';

// Covers §5.1: Drilldown GA (Metrics/Logs/Traces/Profiles).

const targets = [
  { slug: 'metrics',  path: '/a/grafana-metricsdrilldown-app'  },
  { slug: 'logs',     path: '/a/grafana-lokiexplore-app'       },
  { slug: 'traces',   path: '/a/grafana-exploretraces-app'     },
  { slug: 'profiles', path: '/a/grafana-pyroscope-app'         },
];

for (const t of targets) {
  test(`@drilldown ${t.slug} drilldown loads`, async ({ page }) => {
    await page.goto(t.path);
    await expect(page).toHaveURL(new RegExp(t.path));
    await expect(page.locator('[data-testid="data-testid Panel header"], main')).toBeVisible({ timeout: 15_000 });
  });
}
