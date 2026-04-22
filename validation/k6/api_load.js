// k6 API load test: SLO sanity under moderate load.
// Run:  k6 run validation/k6/api_load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-vus',
      vus: 20,
      duration: '2m',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.001'],
    http_req_duration: ['p(95)<500'],
  },
};

const BASE = __ENV.GRAFANA_URL || 'http://localhost:3000';
const TOKEN = __ENV.GRAFANA_SA_TOKEN || '';

export default function () {
  const h = { Authorization: `Bearer ${TOKEN}` };
  check(http.get(`${BASE}/api/health`, { headers: h }), { health: (r) => r.status === 200 });
  check(http.get(`${BASE}/api/datasources`, { headers: h }), { ds: (r) => r.status === 200 });
  check(http.get(`${BASE}/api/search?type=dash-db&limit=100`, { headers: h }), { search: (r) => r.status === 200 });
  sleep(1);
}
