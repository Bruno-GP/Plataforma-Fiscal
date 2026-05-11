import { Rate, Trend } from 'k6/metrics';

export const loginDuration = new Trend('login_duration', true);
export const loginFailureRate = new Rate('login_failure_rate');
export const dashboardDuration = new Trend('dashboard_duration', true);
export const consultaDuration = new Trend('consulta_duration', true);
export const operacaoCriticaDuration = new Trend('operacao_critica_duration', true);
export const authValidationFailureRate = new Rate('auth_validation_failure_rate');
export const criticalValidationFailureRate = new Rate('critical_validation_failure_rate');

export const commonThresholds = {
  http_req_failed: ['rate<0.01'],
  http_req_duration: ['p(95)<2000'],
  checks: ['rate>0.95'],
  login_failure_rate: ['rate<0.01'],
  auth_validation_failure_rate: ['rate<0.01'],
};
