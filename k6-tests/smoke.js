import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, API_URL, DATA, checkOk, get, think } from './lib/helpers.js';

export const options = {
  scenarios: {
    smoke_publico: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<800'],
  },
};

export default function () {
  const health = http.get(`${BASE_URL}/health`, { tags: { endpoint: 'health' } });
  checkOk(health, 'health');
  check(health, {
    'health: status ok': (res) => res.json('status') === 'ok',
  });

  const geo = get(`/geo/municipios/${DATA.uf}`, 'geo_municipios_uf');
  check(geo, {
    'geo: feature collection': (res) => res.json('type') === 'FeatureCollection',
  });

  const dbHealth = http.get(`${BASE_URL}/health/db`, { tags: { endpoint: 'health_db' } });
  checkOk(dbHealth, 'health_db', [200, 503]);

  const redisHealth = http.get(`${BASE_URL}/health/redis`, { tags: { endpoint: 'health_redis' } });
  checkOk(redisHealth, 'health_redis', [200, 503]);

  const docs = http.get(`${API_URL.replace('/api', '')}/docs`, { tags: { endpoint: 'docs' } });
  checkOk(docs, 'docs');

  think();
}
