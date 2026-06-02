import { jornadaCompleta } from '../../flows/jornadaCompleta.flow.js';

const spikeVus = Number(__ENV.TARGET_VUS || 80);

export const options = {
  stages: [
    { duration: '30s', target: 5 },
    { duration: '15s', target: spikeVus },
    { duration: '2m', target: spikeVus },
    { duration: '30s', target: 5 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.10'],
    http_req_duration: ['p(95)<6000'],
    checks: ['rate>0.85'],
  },
};

export default function () {
  jornadaCompleta();
}
