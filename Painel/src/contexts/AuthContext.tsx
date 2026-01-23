import React, { createContext, useContext, useState, ReactNode } from 'react';

interface User {
  id: string;
  name: string;
  email: string;
  emitente_cnpj: string;
  avatar?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
}

interface LoginResponse {
  status: string;
  login_id: number | string;
  empresa_id: number | string;
  cnpj: string;
  email: string;
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

  const login = async (email: string, password: string): Promise<boolean> => {
    // Simulated login - in production, this would call an API
      if (!email || !password) {
      return false;
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
      return false;
    }

    const data = (await response.json()) as LoginResponse;
    const resolvedId = data.login_id ?? data.empresa_id ?? email;
    const nextUser: User = {
      id: String(resolvedId),
      name: data.email,
      email: data.email,
      emitente_cnpj: data.cnpj,
      avatar: undefined,
    };

    setUser(nextUser);
    localStorage.setItem('user', JSON.stringify(nextUser));
    return true;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
