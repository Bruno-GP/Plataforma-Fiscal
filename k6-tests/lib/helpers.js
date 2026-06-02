import http from 'k6/http';
import { check, sleep } from 'k6';

export const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
export const API_URL = BASE_URL.endsWith('/api') ? BASE_URL : `${BASE_URL}/api`;

export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  Accept: 'application/json',
};

export const AUTH = {
  email: __ENV.K6_EMAIL || 'admin@example.com',
  senha: __ENV.K6_PASSWORD || 'change-me-in-env',
};

export const DATA = {
  xmlCnpj: __ENV.K6_XML_CNPJ || __ENV.K6_CNPJ || '28942600000198',
  spedCnpj: __ENV.K6_SPED_CNPJ || __ENV.K6_CNPJ || '35317121000146',
  ano: Number(__ENV.K6_PERIODO_ANO || 2026),
  mes: Number(__ENV.K6_PERIODO_MES || 2),
  uf: __ENV.K6_UF || 'SP',
  ncm: __ENV.K6_NCM || '01012100',
};

export function jsonBody(response) {
  try {
    return response.json();
  } catch {
    return null;
  }
}

export function checkOk(response, name, expectedStatuses = [200], maxDurationMs = 2000) {
  return check(response, {
    [`${name}: status esperado`]: (res) => expectedStatuses.includes(res.status),
    [`${name}: resposta em ate ${maxDurationMs}ms`]: (res) => res.timings.duration < maxDurationMs,
  });
}

export function login() {
  const response = http.post(`${API_URL}/auth/entrar`, JSON.stringify(AUTH), {
    headers: DEFAULT_HEADERS,
    responseCallback: http.expectedStatuses(200),
    tags: { endpoint: 'auth_login' },
  });

  check(response, {
    'login: autenticado': (res) => res.status === 200,
    'login: cookie de sessao recebido': (res) => String(res.headers['Set-Cookie'] || '').length > 0,
  });

  return response;
}

export function get(path, name, expectedStatuses = [200], maxDurationMs = 2000) {
  const response = http.get(`${API_URL}${path}`, {
    headers: { Accept: 'application/json' },
    responseCallback: http.expectedStatuses(...expectedStatuses),
    tags: { endpoint: name },
  });
  checkOk(response, name, expectedStatuses, maxDurationMs);
  return response;
}

export function postJson(path, payload, name, expectedStatuses = [200, 201, 202], maxDurationMs = 2000) {
  const response = http.post(`${API_URL}${path}`, JSON.stringify(payload), {
    headers: DEFAULT_HEADERS,
    responseCallback: http.expectedStatuses(...expectedStatuses),
    tags: { endpoint: name },
  });
  checkOk(response, name, expectedStatuses, maxDurationMs);
  return response;
}

export function think(minSeconds = 0.2, maxSeconds = 1) {
  const delay = minSeconds + Math.random() * (maxSeconds - minSeconds);
  sleep(delay);
}

export function shouldRunUploads() {
  return String(__ENV.K6_RUN_UPLOADS || '').toLowerCase() === 'true';
}
