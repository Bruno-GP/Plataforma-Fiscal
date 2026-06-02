import { loginFlow } from '../../flows/login.flow.js';
import { dashboardFlow } from '../../flows/dashboard.flow.js';
import { consultaFlow } from '../../flows/consulta.flow.js';
import { operacaoCriticaFlow } from '../../flows/operacaoCritica.flow.js';
import { think } from '../../helpers/httpClient.js';

export const options = {
  scenarios: {
    dashboard_users: {
      executor: 'ramping-vus',
      exec: 'dashboardUser',
      stages: [
        { duration: '2m', target: 5 },
        { duration: '5m', target: 5 },
        { duration: '2m', target: 0 },
      ],
    },
    consulta_users: {
      executor: 'ramping-vus',
      exec: 'consultaUser',
      stages: [
        { duration: '2m', target: 10 },
        { duration: '5m', target: 10 },
        { duration: '2m', target: 0 },
      ],
    },
    critical_users: {
      executor: 'ramping-vus',
      exec: 'criticalUser',
      stages: [
        { duration: '2m', target: 3 },
        { duration: '5m', target: 3 },
        { duration: '2m', target: 0 },
      ],
    },
    slow_users: {
      executor: 'ramping-vus',
      exec: 'slowUser',
      stages: [
        { duration: '2m', target: 3 },
        { duration: '5m', target: 3 },
        { duration: '2m', target: 0 },
      ],
    },
    intense_users: {
      executor: 'ramping-vus',
      exec: 'intenseUser',
      stages: [
        { duration: '2m', target: 2 },
        { duration: '5m', target: 2 },
        { duration: '2m', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.03'],
    http_req_duration: ['p(95)<3000'],
    checks: ['rate>0.93'],
    login_failure_rate: ['rate<0.03'],
    auth_validation_failure_rate: ['rate<0.03'],
    critical_validation_failure_rate: ['rate<0.03'],
  },
};

export function dashboardUser() {
  const auth = loginFlow();
  think(0.5, 1.5);
  dashboardFlow(auth.session);
  think(1, 3);
}

export function consultaUser() {
  const auth = loginFlow();
  think(0.3, 1);
  consultaFlow(auth.session);
  think(0.7, 2);
}

export function criticalUser() {
  const auth = loginFlow();
  think(0.5, 1.5);
  operacaoCriticaFlow(auth.session);
  think(1, 2.5);
}

export function slowUser() {
  const auth = loginFlow();
  think(2, 5);
  dashboardFlow(auth.session);
  think(3, 6);
  consultaFlow(auth.session);
  think(3, 7);
}

export function intenseUser() {
  const auth = loginFlow();
  dashboardFlow(auth.session);
  consultaFlow(auth.session);
  operacaoCriticaFlow(auth.session);
  think(0.1, 0.4);
}
