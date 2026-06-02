import { jornadaCompleta } from '../../flows/jornadaCompleta.flow.js';

const rate = Number(__ENV.THROUGHPUT_RATE || 2);
const duration = __ENV.TEST_DURATION || '5m';
const preAllocatedVUs = Number(__ENV.TARGET_VUS || 10);
const maxVUs = Number(__ENV.MAX_VUS || 50);

export const options = {
  scenarios: {
    throughput_test: {
      executor: 'constant-arrival-rate',
      rate,
      timeUnit: '1s',
      duration,
      preAllocatedVUs,
      maxVUs,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.03'],
    http_req_duration: ['p(95)<3000'],
    checks: ['rate>0.93'],
    login_failure_rate: ['rate<0.03'],
    auth_validation_failure_rate: ['rate<0.03'],
  },
};

export default function () {
  jornadaCompleta();
}
