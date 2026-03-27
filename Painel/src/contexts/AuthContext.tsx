import React, { createContext, useContext, useState, ReactNode } from 'react';
import {
  API_BASE_URL,
  apiFetch,
  clearAuthSession,
  readAuthSession,
  saveAuthSession,
  type SessionUser,
} from '@/services/api';

interface User {
  id: string;
  name: string;
  email: string;
  emitente_cnpj: string;
  avatar?: string;
  tem_sped?: boolean;
}

interface StoredUserLegacy {
  id?: string;
  name?: string;
  email?: string;
  emitente_cnpj?: string;
  cnpj?: string;
  avatar?: string;
  tem_sped?: boolean;
}

interface AuthResult {
  ok: boolean;
  message?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<AuthResult>;
  register: (empresaNome: string, email: string, password: string, cnpj: string, temSped: boolean, autoLogin?: boolean) => Promise<AuthResult>;
  logout: () => void;
}

interface LoginResponse {
  status: string;
  login_id: number | string;
  empresa_id: number | string;
  cnpj: string;
  email: string;
  empresa_nome: string;
  tem_sped?: boolean;
  access_token: string;
  token_type: string;
  expires_in: number;
}

interface ApiErrorDetail {
  detail?: string | { msg?: string }[];
}

const extractApiErrorMessage = (errorData: ApiErrorDetail | null, fallback: string) => {
  if (!errorData?.detail) {
    return fallback;
  }

  if (typeof errorData.detail === 'string') {
    return errorData.detail;
  }

  const firstDetail = errorData.detail[0];
  if (firstDetail?.msg) {
    return firstDetail.msg;
  }

  return fallback;
};

const normalizeSessionCnpj = (value: string | null | undefined): string => {
  const digits = (value ?? '').replace(/\D/g, '');

  if (digits.length !== 14) {
    return '';
  }

  if ([...digits].every((digit) => digit === '0')) {
    return '';
  }

  return digits;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(() => {
    const session = readAuthSession();
    if (!session) {
      return null;
    }

    const parsed = session.user as StoredUserLegacy;
    const emitenteCnpj = (parsed.emitente_cnpj ?? parsed.cnpj ?? '').replace(/\D/g, '');

    if (!parsed.id || !parsed.email || !emitenteCnpj) {
      return null;
    }

    return {
      id: String(parsed.id),
      name: parsed.name ?? '',
      email: parsed.email,
      emitente_cnpj: emitenteCnpj,
      avatar: parsed.avatar,
      tem_sped: Boolean(parsed.tem_sped),
    };
  });

  const resolveDisplayName = (empresaNome: string | null | undefined, email: string) => {
    const trimmed = empresaNome?.trim() ?? '';
    if (!trimmed) {
      return '';
    }

    const emailNormalizado = email.trim().toLowerCase();
    if (emailNormalizado && trimmed.toLowerCase() === emailNormalizado) {
      return '';
    }

    const normalizedName = trimmed.split('/').pop()?.trim() ?? trimmed;

    return normalizedName;
  };

  const persistAuthenticatedUser = (data: LoginResponse, fallbackId: string) => {
    const resolvedId = data.login_id ?? data.empresa_id ?? fallbackId;
    const displayName = resolveDisplayName(data.empresa_nome, data.email);
    const nextUser: SessionUser = {
      id: String(resolvedId),
      name: displayName,
      email: data.email,
      emitente_cnpj: normalizeSessionCnpj(data.cnpj),
      avatar: undefined,
      tem_sped: Boolean(data.tem_sped),
    };

    setUser(nextUser);
    saveAuthSession({
      user: nextUser,
      accessToken: data.access_token,
      tokenType: data.token_type,
      expiresAt: Date.now() + data.expires_in * 1000,
    });
  };

  const login = async (email: string, password: string): Promise<AuthResult> => {
    if (!email || !password) {
      return { ok: false, message: 'Informe email e senha.' };
    }

    const response = await apiFetch(`${API_BASE_URL}/auth/entrar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        senha: password,
      }),
    });

    if (!response.ok) {
      const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
      return {
        ok: false,
        message: extractApiErrorMessage(errorData, 'Email ou senha inválidos.'),
      };
    }

    const data = (await response.json()) as LoginResponse;
    persistAuthenticatedUser(data, email);
    return { ok: true };
  };

  const register = async (
    empresaNome: string,
    email: string,
    password: string,
    cnpj: string,
    temSped: boolean,
    autoLogin = true,
  ): Promise<AuthResult> => {
    const empresaNomeNormalizado = empresaNome.trim();
    const emailNormalizado = email.trim();
    const senhaInformada = password;
    const senhaParaValidacao = password.trim();
    const cnpjNormalizado = cnpj.replace(/\D/g, '');

    if (!empresaNomeNormalizado || !emailNormalizado || !senhaParaValidacao || !cnpjNormalizado) {
      return { ok: false, message: 'Informe empresa, email, senha e CNPJ.' };
    }

    if (senhaParaValidacao.length < 8) {
      return { ok: false, message: 'A senha deve ter no mínimo 8 caracteres.' };
    }

    if (cnpjNormalizado.length !== 14) {
      return { ok: false, message: 'Informe um CNPJ válido com 14 dígitos.' };
    }

    const response = await apiFetch(`${API_BASE_URL}/auth/registrar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        empresa_nome: empresaNomeNormalizado,
        email: emailNormalizado,
        senha: senhaInformada,
        cnpj: cnpjNormalizado,
        tem_sped: temSped,
      }),
    });

    if (!response.ok) {
      const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
      return {
        ok: false,
        message: extractApiErrorMessage(errorData, 'Não foi possível cadastrar.'),
      };
    }

    const data = (await response.json()) as LoginResponse;
    
    if (autoLogin) {
      persistAuthenticatedUser(data, emailNormalizado);
    }

    return { ok: true };
  };

  const logout = () => {
    setUser(null);
    clearAuthSession();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
