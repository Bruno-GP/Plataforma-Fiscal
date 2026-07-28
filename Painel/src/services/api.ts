interface ApiEnvironment {
  PROD: boolean;
  VITE_API_URL?: string;
}

const DEFAULT_DEV_API_BASE_URL = 'http://localhost:8000';
const LOCALHOST_API_URL_PATTERN = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/i;
const HTTP_API_URL_PATTERN = /^https?:\/\//i;

export const resolveRawApiBaseUrl = (env: ApiEnvironment) => {
  const configuredUrl = env.VITE_API_URL?.trim();

  if (!configuredUrl) {
    if (env.PROD) {
      throw new Error(
        'VITE_API_URL deve apontar para a API publica no build de producao.',
      );
    }

    return DEFAULT_DEV_API_BASE_URL;
  }

  if (!HTTP_API_URL_PATTERN.test(configuredUrl)) {
    throw new Error(
      'VITE_API_URL deve ser uma URL absoluta iniciando com http:// ou https://.',
    );
  }

  if (env.PROD && LOCALHOST_API_URL_PATTERN.test(configuredUrl)) {
    throw new Error(
      'VITE_API_URL nao pode apontar para localhost no build de producao.',
    );
  }

  return configuredUrl;
};

const RAW_API_BASE_URL = resolveRawApiBaseUrl(import.meta.env);

export const API_BASE_URL = RAW_API_BASE_URL.endsWith('/api')
  ? RAW_API_BASE_URL
  : `${RAW_API_BASE_URL.replace(/\/$/, '')}/api`;

const SESSION_STORAGE_KEY = 'auth_session';
const LEGACY_USER_STORAGE_KEY = 'user';

export interface SessionUser {
  id: string;
  name: string;
  email: string;
  emitente_cnpj: string;
  avatar?: string;
  tem_sped?: boolean;
  tem_conta_azul?: boolean;
  tem_xml?: boolean;
  tem_xml_importado_valido?: boolean;
}

export interface AuthSession {
  user: SessionUser;
  expiresAt: number;
  accessToken?: string;
}

export const readAuthSession = (): AuthSession | null => {
  const rawValue = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as AuthSession;
    if (!parsed?.user?.email || !parsed?.expiresAt) {
      clearAuthSession();
      return null;
    }

    if (parsed.expiresAt <= Date.now()) {
      clearAuthSession();
      return null;
    }

    return parsed;
  } catch {
    clearAuthSession();
    return null;
  }
};

export const saveAuthSession = (session: AuthSession) => {
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  localStorage.setItem(LEGACY_USER_STORAGE_KEY, JSON.stringify(session.user));
};

export const clearAuthSession = () => {
  localStorage.removeItem(SESSION_STORAGE_KEY);
  localStorage.removeItem(LEGACY_USER_STORAGE_KEY);
};

export const apiFetch = (input: string, init: RequestInit = {}) => {
  const headers = new Headers(init.headers);
  const session = readAuthSession();

  if (session?.accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${session.accessToken}`);
  }

  return fetch(input, {
    ...init,
    headers,
    credentials: init.credentials ?? 'include',
  }).then((response) => {
    if (response.status === 401) {
      clearAuthSession();
    }

    return response;
  });
};
