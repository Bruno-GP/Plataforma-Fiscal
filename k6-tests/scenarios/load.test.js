import { jornadaCompleta } from '../flows/jornadaCompleta.flow.js';
import { commonThresholds } from '../helpers/metrics.js';

export const options = {
  stages: [
    { duration: '2m', target: 10 },
    { duration: '5m', target: 10 },
    { duration: '2m', target: 0 },
  ],
  thresholds: commonThresholds,
};

export default function () {
  jornadaCompleta();
}
