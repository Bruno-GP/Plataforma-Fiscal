const RAW_API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

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
}

export interface AuthSession {
  user: SessionUser;
  expiresAt: number;
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
