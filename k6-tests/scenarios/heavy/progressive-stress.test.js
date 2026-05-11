import { jornadaCompleta } from '../../flows/jornadaCompleta.flow.js';

const maxVus = Number(__ENV.MAX_VUS || 100);

export const options = {
  stages: [
    { duration: '2m', target: Math.min(5, maxVus) },
    { duration: '3m', target: Math.min(10, maxVus) },
    { duration: '3m', target: Math.min(20, maxVus) },
    { duration: '3m', target: Math.min(40, maxVus) },
    { duration: '3m', target: Math.min(60, maxVus) },
    { duration: '3m', target: Math.min(80, maxVus) },
    { duration: '3m', target: maxVus },
    { duration: '5m', target: maxVus },
    { duration: '3m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.08'],
    http_req_duration: ['p(95)<5000'],
    checks: ['rate>0.90'],
  },
};

export default function () {
  jornadaCompleta();
}
