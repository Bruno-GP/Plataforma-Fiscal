import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearAuthSession,
  readAuthSession,
  saveAuthSession,
  type AuthSession,
} from '@/services/api';

const makeSession = (expiresAt: number): AuthSession => ({
  user: {
    id: '1',
    name: 'Empresa Teste',
    email: 'teste@empresa.com',
    emitente_cnpj: '12345678000199',
    tem_sped: false,
  },
  expiresAt,
});

describe('auth session helpers', () => {
  beforeEach(() => {
    const storage = new Map<string, string>();

    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => {
          storage.set(key, value);
        },
        removeItem: (key: string) => {
          storage.delete(key);
        },
      },
    });

    clearAuthSession();
  });

  it('persiste e recupera uma sessão válida', () => {
    const session = makeSession(Date.now() + 60_000);
    saveAuthSession(session);

    expect(readAuthSession()).toEqual(session);
  });

  it('limpa sessão expirada automaticamente', () => {
    saveAuthSession(makeSession(Date.now() - 1_000));

    expect(readAuthSession()).toBeNull();
  });
});
