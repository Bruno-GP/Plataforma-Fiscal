import { jornadaCompleta } from '../flows/jornadaCompleta.flow.js';

export const options = {
  stages: [
    { duration: '5m', target: 30 },
    { duration: '60m', target: 30 },
    { duration: '5m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<3000'],
    checks: ['rate>0.95'],
    login_failure_rate: ['rate<0.01'],
    critical_validation_failure_rate: ['rate<0.01'],
  },
};

export default function () {
  jornadaCompleta();
}
