import { jornadaCompleta } from '../../flows/jornadaCompleta.flow.js';

export const options = {
  stages: [
    { duration: '2m', target: 5 },
    { duration: '5m', target: 5 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
    checks: ['rate>0.95'],
    login_failure_rate: ['rate<0.01'],
    auth_validation_failure_rate: ['rate<0.01'],
  },
};

export default function () {
  jornadaCompleta();
}
