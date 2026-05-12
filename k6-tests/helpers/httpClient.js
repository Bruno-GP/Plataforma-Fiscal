import http from 'k6/http';
import { check, sleep } from 'k6';
import { env } from '../config/environments.js';

export const DEFAULT_HEADERS = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
};

export const testData = {
  xmlCnpj: __ENV.K6_XML_CNPJ || __ENV.K6_CNPJ || '28942600000198',
  spedCnpj: __ENV.K6_SPED_CNPJ || __ENV.K6_CNPJ || '35317121000146',
  ano: Number(__ENV.K6_PERIODO_ANO || 2026),
  mes: Number(__ENV.K6_PERIODO_MES || 2),
  uf: __ENV.K6_UF || 'SP',
  ncm: __ENV.K6_NCM || '01012100',
  fiscalNivel: __ENV.K6_FISCAL_NIVEL || 'estado',
};

export function apiPath(path) {
  return `${env.apiUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

export function rootPath(path) {
  return `${env.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

export function jsonBody(response) {
  try {
    return response.json();
  } catch {
    return null;
  }
}

export function checkStatus(response, name, expectedStatuses = [200], maxDurationMs = 2000) {
  return check(response, {
    [`${name}: status esperado`]: (res) => expectedStatuses.includes(res.status),
    [`${name}: resposta abaixo de ${maxDurationMs}ms`]: (res) => res.timings.duration < maxDurationMs,
  });
}

export function checkJsonStatusOk(response, name) {
  return check(response, {
    [`${name}: payload status ok`]: (res) => {
      const body = jsonBody(res);
      return !body || body.status === undefined || body.status === 'ok';
    },
  });
}

export function get(path, name, expectedStatuses = [200], maxDurationMs = 2000, headers = { Accept: 'application/json' }) {
  const response = http.get(apiPath(path), {
    headers,
    responseCallback: http.expectedStatuses(...expectedStatuses),
    tags: { endpoint: name },
  });

  logUnexpectedResponse(response, name, expectedStatuses);
  checkStatus(response, name, expectedStatuses, maxDurationMs);
  checkJsonStatusOk(response, name);

  return response;
}

export function postJson(path, payload, name, expectedStatuses = [200, 201, 202], maxDurationMs = 2000, headers = DEFAULT_HEADERS) {
  const response = http.post(apiPath(path), JSON.stringify(payload), {
    headers,
    responseCallback: http.expectedStatuses(...expectedStatuses),
    tags: { endpoint: name },
  });

  logUnexpectedResponse(response, name, expectedStatuses);
  checkStatus(response, name, expectedStatuses, maxDurationMs);
  checkJsonStatusOk(response, name);

  return response;
}

export function logUnexpectedResponse(response, name, expectedStatuses = [200]) {
  if (String(__ENV.K6_DEBUG_HTTP || '').toLowerCase() !== 'true') {
    return;
  }

  if (expectedStatuses.includes(response.status)) {
    return;
  }

  const body = String(response.body || '').replace(/\s+/g, ' ').slice(0, 500);
  console.error(
    `[${name}] status inesperado=${response.status} esperado=${expectedStatuses.join(',')} ` +
      `duracao=${Math.round(response.timings.duration)}ms body=${body}`
  );
}

export function think(minSeconds = 0.3, maxSeconds = 1.5) {
  const delay = minSeconds + Math.random() * (maxSeconds - minSeconds);
  sleep(delay);
}

export function getCompanyMode(session) {
  if (env.mode === 'nfe' || env.mode === 'xml') {
    return 'nfe';
  }

  if (env.mode === 'sped') {
    return 'sped';
  }

  return session?.tem_sped ? 'sped' : 'nfe';
}

export function getCompanyCnpj(session, mode) {
  const sessionCnpj = String(session?.cnpj || '').replace(/\D/g, '');

  if (sessionCnpj.length === 14) {
    return sessionCnpj;
  }

  return mode === 'sped' ? testData.spedCnpj : testData.xmlCnpj;
}
