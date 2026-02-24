import React, { createContext, useContext, useState, ReactNode } from 'react';

interface User {
  id: string;
  name: string;
  email: string;
  emitente_cnpj: string;
  avatar?: string;
}

interface AuthResult {
  ok: boolean;
  message?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<AuthResult>;
  register: (empresaNome: string, email: string, password: string, cnpj: string, autoLogin?: boolean) => Promise<AuthResult>;
  logout: () => void;
}

interface LoginResponse {
  status: string;
  login_id: number | string;
  empresa_id: number | string;
  cnpj: string;
  email: string;
  empresa_nome: string;
}

const RAW_API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_BASE_URL = RAW_API_BASE_URL.endsWith('/api')
  ? RAW_API_BASE_URL
  : `${RAW_API_BASE_URL.replace(/\/$/, '')}/api`;

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
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
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
      const firstWord = normalizedName.split(/\s+/)[0];
      return firstWord;
    };

  const login = async (email: string, password: string): Promise<AuthResult> => {
    if (!email || !password) {
      return { ok: false, message: 'Informe email e senha.' };
    }

    const response = await fetch(`${API_BASE_URL}/auth/entrar`, {
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
      const errorData = await response.json().catch(() => null);
      return {
        ok: false,
        message: errorData?.detail ?? 'Email ou senha inválidos.',
      };
    }

    const data = (await response.json()) as LoginResponse;
    const resolvedId = data.login_id ?? data.empresa_id ?? email;
    const displayName = resolveDisplayName(data.empresa_nome, data.email);
    const nextUser: User = {
      id: String(resolvedId),
      name: displayName,
      email: data.email,
      emitente_cnpj: data.cnpj,
      avatar: undefined,
    };

    setUser(nextUser);
    localStorage.setItem('user', JSON.stringify(nextUser));
    return { ok: true };
  };

  const register = async (
    empresaNome: string,
    email: string,
    password: string,
    cnpj: string,
    autoLogin = true,
  ): Promise<AuthResult> => {
    if (!empresaNome || !email || !password || !cnpj) {
      return { ok: false, message: 'Informe empresa, email, senha e CNPJ.' };
    }

    const response = await fetch(`${API_BASE_URL}/auth/registrar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        empresa_nome: empresaNome,
        email,
        senha: password,
        cnpj,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      return {
        ok: false,
        message: errorData?.detail ?? 'Não foi possível cadastrar.',
      };
    }

    const data = (await response.json()) as LoginResponse;
    
    if (autoLogin) {
      const resolvedId = data.login_id ?? data.empresa_id ?? email;
      const displayName = resolveDisplayName(data.empresa_nome, data.email);
      const nextUser: User = {
        id: String(resolvedId),
        name: displayName,
        email: data.email,
        emitente_cnpj: data.cnpj,
        avatar: undefined,
      };

      setUser(nextUser);
      localStorage.setItem('user', JSON.stringify(nextUser));
    }

    return { ok: true };
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
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
