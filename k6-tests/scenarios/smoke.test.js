import http from 'k6/http';
import { check } from 'k6';
import { env } from '../config/environments.js';
import { rootPath } from '../helpers/httpClient.js';
import { commonThresholds } from '../helpers/metrics.js';
import { jornadaCompleta } from '../flows/jornadaCompleta.flow.js';

export const options = {
  vus: 1,
  duration: '1m',
  thresholds: commonThresholds,
};

export default function () {
  const health = http.get(rootPath('/health'), {
    responseCallback: http.expectedStatuses(200),
    tags: { endpoint: 'health' },
  });

  check(health, {
    'health: api online': (res) => res.status === 200,
    'health: status ok': (res) => res.json('status') === 'ok',
    'ambiente: nao production por padrao': () => env.name !== 'production',
  });

  jornadaCompleta();
}
