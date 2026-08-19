import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
  API_BASE_URL,
  apiFetch,
  clearAuthSession,
  readAuthSession,
  saveAuthSession,
  type SessionUser,
} from '@/services/api';
import { getDefaultWorkspaceRoute } from '@/utils/workspaceAccess';
import { normalizeCnpj, isPlaceholderCnpj } from '@/utils/formatters';

interface User {
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

interface StoredUserLegacy {
  id?: string;
  name?: string;
  email?: string;
  emitente_cnpj?: string;
  cnpj?: string;
  avatar?: string;
  tem_sped?: boolean;
  tem_conta_azul?: boolean;
  tem_xml?: boolean;
  tem_xml_importado_valido?: boolean;
}

interface AuthResult {
  ok: boolean;
  message?: string;
  redirectTo?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isReady: boolean;
  login: (email: string, password: string) => Promise<AuthResult>;
  refreshSession: () => Promise<void>;
  register: (
    empresaNome: string,
    email: string,
    password: string,
    cnpj: string,
    origemFiscal: 'xml' | 'sped' | 'conta_azul',
    autoLogin?: boolean,
    estado?: string,
    cidade?: string,
    municipioId?: string,
    codigoIbge?: string,
    cnaeFiscal?: string,
    cnaeFiscalDescricao?: string,
  ) => Promise<AuthResult>;
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
  tem_conta_azul?: boolean;
  tem_xml?: boolean;
  tem_xml_importado_valido?: boolean;
  expires_in: number;
  access_token?: string;
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
  const digits = normalizeCnpj(value);

  if (digits.length !== 14) {
    return '';
  }

  if (isPlaceholderCnpj(digits)) {
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
  const [isReady, setIsReady] = useState(false);
  const [user, setUser] = useState<User | null>(() => {
    const session = readAuthSession();
    if (!session) {
      return null;
    }

    const parsed = session.user as StoredUserLegacy;
    const emitenteCnpj = normalizeCnpj(parsed.emitente_cnpj ?? parsed.cnpj);

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
      tem_conta_azul: Boolean(parsed.tem_conta_azul),
      tem_xml: Boolean(parsed.tem_xml),
      tem_xml_importado_valido: Boolean(parsed.tem_xml_importado_valido),
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

    return trimmed.split('/').pop()?.trim() ?? trimmed;
  };

  const persistAuthenticatedUser = (data: LoginResponse, fallbackId: string) => {
    const resolvedId = data.login_id ?? data.empresa_id ?? fallbackId;
    const nextUser: SessionUser = {
      id: String(resolvedId),
      name: resolveDisplayName(data.empresa_nome, data.email),
      email: data.email,
      emitente_cnpj: normalizeSessionCnpj(data.cnpj),
      avatar: undefined,
      tem_sped: Boolean(data.tem_sped),
      tem_conta_azul: Boolean(data.tem_conta_azul),
      tem_xml: Boolean(data.tem_xml),
      tem_xml_importado_valido: Boolean(data.tem_xml_importado_valido),
    };

    setUser(nextUser);
    saveAuthSession({
      user: nextUser,
      expiresAt: Date.now() + data.expires_in * 1000,
      accessToken: data.access_token ?? readAuthSession()?.accessToken,
    });
  };

  const syncSessionFromServer = async (clearOnFailure: boolean) => {
    try {
      const response = await apiFetch(`${API_BASE_URL}/auth/sessao`);
      if (!response.ok) {
        if (clearOnFailure) {
          setUser(null);
        }
        return;
      }

      const data = (await response.json()) as LoginResponse;
      persistAuthenticatedUser(data, data.email);
    } catch {
      if (clearOnFailure) {
        setUser(null);
      }
    }
  };

  useEffect(() => {
    const hydrateSession = async () => {
      await syncSessionFromServer(true);
      setIsReady(true);
    };

    void hydrateSession();
  }, []);

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
    return {
      ok: true,
      redirectTo: getDefaultWorkspaceRoute({
        tem_sped: Boolean(data.tem_sped),
        tem_conta_azul: Boolean(data.tem_conta_azul),
        tem_xml: Boolean(data.tem_xml),
        tem_xml_importado_valido: Boolean(data.tem_xml_importado_valido),
      }),
    };
  };

  const refreshSession = async () => {
    await syncSessionFromServer(false);
  };

  const register = async (
    empresaNome: string,
    email: string,
    password: string,
    cnpj: string,
    origemFiscal: 'xml' | 'sped' | 'conta_azul',
    autoLogin = true,
    estado?: string,
    cidade?: string,
    municipioId?: string,
    codigoIbge?: string,
    cnaeFiscal?: string,
    cnaeFiscalDescricao?: string,
  ): Promise<AuthResult> => {
    const empresaNomeNormalizado = empresaNome.trim();
    const emailNormalizado = email.trim();
    const senhaInformada = password;
    const senhaParaValidacao = password.trim();
    const cnpjNormalizado = normalizeCnpj(cnpj);

    if (!empresaNomeNormalizado || !emailNormalizado || !senhaParaValidacao || !cnpjNormalizado) {
      return { ok: false, message: 'Informe empresa, email, senha e CNPJ.' };
    }

    if (senhaParaValidacao.length < 12) {
      return { ok: false, message: 'A senha deve ter no mínimo 12 caracteres, com maiúscula, minúscula, número e símbolo.' };
    }

    if (cnpjNormalizado.length !== 14) {
      return { ok: false, message: 'Informe um CNPJ válido com 14 dígitos.' };
    }

    const ufNormalizada = estado?.trim().toUpperCase() ?? '';
    const cidadeNormalizada = cidade?.trim() ?? '';
    const municipioIdNormalizado = municipioId?.trim() ?? '';
    const codigoIbgeNormalizado = codigoIbge?.trim() ?? '';

    if (!ufNormalizada) {
      return { ok: false, message: 'Selecione uma UF válida para a empresa.' };
    }

    if (!cidadeNormalizada) {
      return { ok: false, message: 'Selecione uma cidade válida para a empresa.' };
    }

    if (!municipioIdNormalizado) {
      return { ok: false, message: 'Selecione uma cidade vinculada ao catálogo de municípios.' };
    }

    if (!codigoIbgeNormalizado) {
      return { ok: false, message: 'Selecione uma cidade vinculada ao código IBGE do catálogo.' };
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
          tem_sped: origemFiscal === 'sped',
          tem_conta_azul: origemFiscal === 'conta_azul',
          tem_xml: origemFiscal === 'xml',
          estado: ufNormalizada,
          cidade: cidadeNormalizada,
          municipio_id: municipioIdNormalizado,
          codigo_ibge: codigoIbgeNormalizado,
          cnae_fiscal: cnaeFiscal?.trim() || undefined,
          cnae_fiscal_descricao: cnaeFiscalDescricao?.trim() || undefined,
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
    void apiFetch(`${API_BASE_URL}/auth/sair`, { method: 'POST' });
    setUser(null);
    clearAuthSession();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isReady,
        login,
        refreshSession,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
