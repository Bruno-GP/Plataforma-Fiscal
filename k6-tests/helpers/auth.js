import { check } from 'k6';
import { DEFAULT_HEADERS, get, jsonBody, postJson } from './httpClient.js';
import { authValidationFailureRate, loginDuration, loginFailureRate } from './metrics.js';

export function getTestUser() {
  return {
    email: __ENV.K6_EMAIL || __ENV.K6_USER_EMAIL || 'usuario1@teste.com',
    senha: __ENV.K6_PASSWORD || __ENV.K6_USER_PASSWORD || 'senha_teste',
  };
}

export function login() {
  const credentials = getTestUser();
  const response = postJson('/auth/entrar', credentials, 'auth_login', [200], 2000, DEFAULT_HEADERS);
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
