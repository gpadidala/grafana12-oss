import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.GRAFANA_URL ?? 'http://localhost:3000';
const token = process.env.GRAFANA_SA_TOKEN ?? '';

export default defineConfig({
  testDir: './specs',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list'], ['html', { open: 'never' }], ['json', { outputFile: 'playwright-report.json' }]],
  use: {
    baseURL,
    extraHTTPHeaders: token ? { Authorization: `Bearer ${token}` } : {},
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
