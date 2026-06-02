import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  apiFetch,
  clearAuthSession,
  readAuthSession,
  resolveRawApiBaseUrl,
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
  accessToken: 'token-teste',
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

  it('envia Bearer token salvo como fallback de autenticacao', async () => {
    saveAuthSession(makeSession(Date.now() + 60_000));
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('https://api.example.com/api/auth/sessao');

    const [, requestInit] = fetchMock.mock.calls[0]!;
    expect((requestInit?.headers as Headers).get('Authorization')).toBe('Bearer token-teste');
    expect(requestInit?.credentials).toBe('include');
  });
});

describe('api base url configuration', () => {
  it('usa localhost como fallback apenas em desenvolvimento', () => {
    expect(resolveRawApiBaseUrl({ PROD: false })).toBe('http://localhost:8000');
  });

  it('exige VITE_API_URL em producao', () => {
    expect(() => resolveRawApiBaseUrl({ PROD: true })).toThrow(
      'VITE_API_URL deve apontar para a API publica',
    );
  });

  it('rejeita localhost em producao', () => {
    expect(() =>
      resolveRawApiBaseUrl({
        PROD: true,
        VITE_API_URL: 'http://localhost:8000',
      }),
    ).toThrow('VITE_API_URL nao pode apontar para localhost');
  });

  it('rejeita URL sem protocolo', () => {
    expect(() =>
      resolveRawApiBaseUrl({
        PROD: true,
        VITE_API_URL: 'plataforma-fiscal.vercel.app',
      }),
    ).toThrow('VITE_API_URL deve ser uma URL absoluta');
  });

  it('aceita URL publica em producao', () => {
    expect(
      resolveRawApiBaseUrl({
        PROD: true,
        VITE_API_URL: 'https://api.plataforma-fiscal.com.br',
      }),
    ).toBe('https://api.plataforma-fiscal.com.br');
  });
});
