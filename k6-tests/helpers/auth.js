import { check } from 'k6';
import { DEFAULT_HEADERS, get, jsonBody, postJson } from './httpClient.js';
import { authValidationFailureRate, loginDuration, loginFailureRate } from './metrics.js';

export function getTestUser() {
  return {
    email: __ENV.K6_EMAIL || __ENV.K6_USER_EMAIL || 'usuario1@teste.com',
    senha: __ENV.K6_PASSWORD || __ENV.K6_USER_PASSWORD || 'SenhaTeste@123',
    empresaNome: __ENV.K6_EMPRESA_NOME || 'Empresa Teste K6',
    cnpj: __ENV.K6_AUTH_CNPJ || __ENV.K6_XML_CNPJ || __ENV.K6_CNPJ || '28942600000198',
    temSped: String(__ENV.K6_TEM_SPED || '').toLowerCase() === 'true',
  };
}

function errorDetail(response) {
  const body = jsonBody(response);
  return body?.detail || response.body || `HTTP ${response.status}`;
}

export function ensureTestUser() {
  const credentials = getTestUser();
  const loginPayload = { email: credentials.email, senha: credentials.senha };
  const cadastro = postJson(
    '/auth/registrar',
    {
      empresa_nome: credentials.empresaNome,
      email: credentials.email,
      senha: credentials.senha,
      cnpj: credentials.cnpj,
      tem_sped: credentials.temSped,
    },
    'auth_register_setup',
    [201, 400],
    3000,
    DEFAULT_HEADERS
  );

  if (cadastro.status === 400 && !String(errorDetail(cadastro)).includes('E-mail')) {
    throw new Error(`Falha ao preparar usuario k6: ${errorDetail(cadastro)}`);
  }

  const loginResponse = postJson('/auth/entrar', loginPayload, 'auth_login_setup', [200], 3000, DEFAULT_HEADERS);

  if (loginResponse.status !== 200) {
    throw new Error(
      `Usuario k6 nao conseguiu autenticar (${credentials.email}). ` +
        `Confira K6_EMAIL/K6_PASSWORD ou remova o cadastro antigo com outra senha. Detalhe: ${errorDetail(loginResponse)}`
    );
  }
}

export function login() {
  const credentials = getTestUser();
  const loginPayload = { email: credentials.email, senha: credentials.senha };
  const response = postJson('/auth/entrar', loginPayload, 'auth_login', [200], 2000, DEFAULT_HEADERS);
  const body = jsonBody(response);
  const setCookie = String(response.headers['Set-Cookie'] || '');

  loginDuration.add(response.timings.duration);

  const ok = check(response, {
    'login: autenticado': (res) => res.status === 200,
    'login: cookie de sessao recebido': () => setCookie.length > 0,
    'login: email retornado': () => body?.email === credentials.email,
    'login: cnpj retornado': () => String(body?.cnpj || '').replace(/\D/g, '').length === 14,
  });

  loginFailureRate.add(!ok);

  return {
    ok,
    response,
    session: body,
    headers: { Accept: 'application/json' },
  };
}

export function validateAuthenticatedSession(expectedEmail) {
  const response = get('/auth/sessao', 'auth_session', [200], 1000);
  const body = jsonBody(response);
  const ok = check(response, {
    'sessao: autenticada': (res) => res.status === 200,
    'sessao: email esperado': () => !expectedEmail || body?.email === expectedEmail,
  });

  authValidationFailureRate.add(!ok);
  return body;
}
