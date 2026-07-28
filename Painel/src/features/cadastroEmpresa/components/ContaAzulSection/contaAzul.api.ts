import { API_BASE_URL, apiFetch } from '@/services/api';

import type { AuthUrlResponse, ContaAzulIntegracao } from './contaAzul.types';

/**
 * GET /api/empresas/:id/integracoes/conta-azul
 * Retorna a integracao atual da Conta Azul ou null quando inexistente.
 */
export const getContaAzulIntegracao = async (empresaId: number) => {
  const response = await apiFetch(`${API_BASE_URL}/empresas/${empresaId}/integracoes/conta-azul`);

  if (response.status === 404 || response.status === 204) {
    return null;
  }

  if (!response.ok) {
    throw new Error('Nao foi possivel carregar a integracao da Conta Azul.');
  }

  return (await response.json()) as ContaAzulIntegracao | null;
};

/**
 * GET /api/empresas/:id/integracoes/conta-azul/auth-url
 * Retorna a URL de autorizacao OAuth2.
 */
export const getContaAzulAuthUrl = async (empresaId: number) => {
  const response = await apiFetch(`${API_BASE_URL}/empresas/${empresaId}/integracoes/conta-azul/auth-url`);

  if (!response.ok) {
    throw new Error('Nao foi possivel gerar a URL de autorizacao.');
  }

  return (await response.json()) as AuthUrlResponse;
};

/**
 * GET /api/empresas/:id/integracoes/conta-azul/sincronizacoes
 * Retorna o estado atualizado das sincronizacoes da Conta Azul.
 */
export const getContaAzulSincronizacoes = async (empresaId: number) => {
  const response = await apiFetch(`${API_BASE_URL}/empresas/${empresaId}/integracoes/conta-azul/sincronizacoes`);

  if (!response.ok) {
    throw new Error('Nao foi possivel consultar as sincronizacoes da Conta Azul.');
  }

  return (await response.json()) as ContaAzulIntegracao;
};

/**
 * POST /api/empresas/:id/integracoes/conta-azul/sync
 * Dispara uma sincronizacao manual.
 */
export const syncContaAzul = async (empresaId: number) => {
  const response = await apiFetch(`${API_BASE_URL}/empresas/${empresaId}/integracoes/conta-azul/sync`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Nao foi possivel iniciar a sincronizacao.');
  }

  return (await response.json()) as { iniciado: true };
};

/**
 * DELETE /api/empresas/:id/integracoes/conta-azul
 * Remove a integracao ativa.
 */
export const deleteContaAzulIntegracao = async (empresaId: number) => {
  const response = await apiFetch(`${API_BASE_URL}/empresas/${empresaId}/integracoes/conta-azul`, {
    method: 'DELETE',
  });

  if (response.status === 404 || response.status === 204) {
    return;
  }

  if (!response.ok) {
    throw new Error('Nao foi possivel desconectar a Conta Azul.');
  }
};
