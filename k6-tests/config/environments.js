const environmentName = __ENV.ENVIRONMENT || 'local';

export const environments = {
  local: {
    baseUrl: __ENV.K6_BASE_URL || __ENV.BASE_URL || 'http://localhost:8000',
    frontendUrl: __ENV.K6_FRONTEND_URL || 'http://localhost:5173',
    defaultMode: __ENV.K6_RUN_MODE || 'auto',
    allowSideEffects: false,
  },
  staging: {
    baseUrl: __ENV.K6_BASE_URL || 'https://staging.exemplo.com',
    frontendUrl: __ENV.K6_FRONTEND_URL || 'https://staging.exemplo.com',
    defaultMode: __ENV.K6_RUN_MODE || 'auto',
    allowSideEffects: false,
  },
  production: {
    baseUrl: __ENV.K6_BASE_URL || 'https://app.exemplo.com',
    frontendUrl: __ENV.K6_FRONTEND_URL || 'https://app.exemplo.com',
    defaultMode: __ENV.K6_RUN_MODE || 'auto',
    allowSideEffects: false,
  },
};

function normalizeUrl(url) {
  return String(url || '').replace(/\/$/, '');
}

export function getEnvironment() {
  const environment = environments[environmentName];

  if (!environment) {
    throw new Error(`Ambiente k6 desconhecido: ${environmentName}`);
  }

  if (environmentName === 'production' && String(__ENV.K6_ALLOW_PRODUCTION || '').toLowerCase() !== 'true') {
    throw new Error('Execucao contra production bloqueada. Defina K6_ALLOW_PRODUCTION=true explicitamente.');
  }

  const baseUrl = normalizeUrl(environment.baseUrl);
  const frontendUrl = normalizeUrl(environment.frontendUrl);

  return {
    ...environment,
    name: environmentName,
    baseUrl,
    apiUrl: baseUrl.endsWith('/api') ? baseUrl : `${baseUrl}/api`,
    frontendUrl,
    mode: String(__ENV.K6_RUN_MODE || environment.defaultMode || 'auto').toLowerCase(),
    allowSideEffects: environment.allowSideEffects || String(__ENV.K6_ENABLE_SIDE_EFFECTS || '').toLowerCase() === 'true',
  };
}

export const env = getEnvironment();
