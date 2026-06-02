import { jornadaCompleta } from '../../flows/jornadaCompleta.flow.js';

const targetVus = Number(__ENV.TARGET_VUS || 10);
const holdDuration = __ENV.TEST_DURATION || '30m';

export const options = {
  stages: [
    { duration: '5m', target: targetVus },
    { duration: holdDuration, target: targetVus },
    { duration: '5m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<3000'],
    checks: ['rate>0.95'],
  },
};

export default function () {
  jornadaCompleta();
}
