import { jornadaCompleta } from '../flows/jornadaCompleta.flow.js';

export const options = {
  stages: [
    { duration: '2m', target: 10 },
    { duration: '3m', target: 30 },
    { duration: '3m', target: 60 },
    { duration: '3m', target: 100 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<3000'],
    checks: ['rate>0.90'],
    login_failure_rate: ['rate<0.05'],
    critical_validation_failure_rate: ['rate<0.05'],
  },
};

export default function () {
  jornadaCompleta();
}
