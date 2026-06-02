import { jornadaCompleta } from '../flows/jornadaCompleta.flow.js';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '10s', target: 100 },
    { duration: '2m', target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    checks: ['rate>0.90'],
    login_failure_rate: ['rate<0.05'],
  },
};

export default function () {
  jornadaCompleta();
}
