// k6 script. Point it ONLY at your own staging environment, never at anyone else's service.
//   k6 run -e BASE=https://staging.example.com load-test.example.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '3m', target: 20 },
    { duration: '1m', target: 0 },
  ],
  thresholds: { http_req_failed: ['rate<0.01'], http_req_duration: ['p(95)<800'] },
};

export default function () {
  const res = http.get(`${__ENV.BASE}/api/health`);
  check(res, { 'healthy': (r) => r.status === 200 });
  sleep(1);
}
