import http from 'k6/http';
import { check } from 'k6';
import { API_URL, AUTH, DEFAULT_HEADERS, login, think } from './lib/helpers.js';

export const options = {
  scenarios: {
    autenticacao: {
      executor: 'ramping-vus',
      stages: [
        { duration: '20s', target: 3 },
        { duration: '40s', target: 3 },
        { duration: '20s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
    'http_req_duration{endpoint:auth_session_pre_login}': ['p(95)<800'],
    'http_req_duration{endpoint:auth_login}': ['p(95)<1200'],
    'http_req_duration{endpoint:auth_session}': ['p(95)<800'],
  },
};

export default function () {
  const preLoginSession = http.get(`${API_URL}/auth/sessao`, {
    headers: { Accept: 'application/json' },
    responseCallback: http.expectedStatuses(401),
    tags: { endpoint: 'auth_session_pre_login' },
  });
  check(preLoginSession, {
    'sessao antes do login: retorna 401': (res) => res.status === 401,
  });

  login();

  const session = http.get(`${API_URL}/auth/sessao`, {
    headers: { Accept: 'application/json' },
    tags: { endpoint: 'auth_session' },
  });
  check(session, {
    'sessao: autenticada': (res) => res.status === 200,
    'sessao: email correto': (res) => res.json('email') === AUTH.email,
  });

  const logout = http.post(`${API_URL}/auth/sair`, null, {
    headers: { Accept: 'application/json' },
    tags: { endpoint: 'auth_logout' },
  });
  check(logout, {
    'logout: sem conteudo': (res) => res.status === 204,
  });

  const postLogoutSession = http.get(`${API_URL}/auth/sessao`, {
    headers: { Accept: 'application/json' },
    responseCallback: http.expectedStatuses(401),
    tags: { endpoint: 'auth_session_post_logout' },
  });
  check(postLogoutSession, {
    'sessao apos logout: retorna 401': (res) => res.status === 401,
  });

  think();
}
