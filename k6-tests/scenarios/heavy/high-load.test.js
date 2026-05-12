import { jornadaCompleta } from '../../flows/jornadaCompleta.flow.js';
import { ensureTestUser } from '../../helpers/auth.js';

const targetVus = Number(__ENV.TARGET_VUS || 30);
const firstStepVus = Math.max(1, Math.ceil(targetVus / 3));
const secondStepVus = Math.max(firstStepVus, Math.ceil((targetVus * 2) / 3));
const holdDuration = __ENV.TEST_DURATION || '5m';

export const options = {
  stages: [
    { duration: '3m', target: firstStepVus },
    { duration: holdDuration, target: secondStepVus },
    { duration: holdDuration, target: targetVus },
    { duration: '3m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.03'],
    http_req_duration: ['p(95)<3000'],
    checks: ['rate>0.93'],
    login_failure_rate: ['rate<0.03'],
  },
};

export function setup() {
  ensureTestUser();
}

export default function () {
  jornadaCompleta();
}
