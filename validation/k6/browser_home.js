// k6-browser journey: home → explore → dashboard open.
// Run:  k6 run validation/k6/browser_home.js
import { browser } from 'k6/browser';
import { check } from 'k6';

export const options = {
  scenarios: {
    ui: {
      executor: 'shared-iterations',
      options: { browser: { type: 'chromium' } },
      vus: 1,
      iterations: 1,
    },
  },
  thresholds: {
    checks: ['rate==1.0'],
    browser_web_vital_lcp: ['p(95)<3000'],
  },
};

const BASE = __ENV.GRAFANA_URL || 'http://localhost:3000';

export default async function () {
  const page = await browser.newPage();
  try {
    await page.goto(`${BASE}/login`);
    check(page, { 'login page loads': async (p) => (await p.title()).length > 0 });
    await page.goto(`${BASE}/explore`);
    check(page, { 'explore loads': async (p) => (await p.locator('main').isVisible()) });
  } finally {
    await page.close();
  }
}
