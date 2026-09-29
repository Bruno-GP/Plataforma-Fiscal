import { API_BASE_URL, apiFetch } from './api';

const parseError = async (response: Response, fallback: string) => {
  const error = await response.json().catch(() => ({ detail: fallback }));
  return error.detail ?? fallback;
};

export const fetchContaAzulKpis = async (params: Record<string, unknown> = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await apiFetch(`${API_BASE_URL}/conta-azul/analise/kpis?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error(await parseError(response, 'Falha ao consultar KPIs da Conta Azul.'));
  }
  return response.json();
};

export const fetchContaAzulDashboardCompras = async (params: Record<string, unknown> = {}, options: { signal?: AbortSignal } = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await apiFetch(`${API_BASE_URL}/conta-azul/analise/compras/dashboard?${searchParams.toString()}`, {
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(await parseError(response, 'Falha ao consultar dashboard de compras da Conta Azul.'));
  }
  return response.json();
};

export const fetchContaAzulDashboardVendas = async (params: Record<string, unknown> = {}, options: { signal?: AbortSignal } = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await apiFetch(`${API_BASE_URL}/conta-azul/analise/vendas/dashboard?${searchParams.toString()}`, {
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(await parseError(response, 'Falha ao consultar dashboard de vendas da Conta Azul.'));
  }
  return response.json();
};

export const fetchContaAzulAnaliseCompras = async (params: Record<string, unknown> = {}, options: { signal?: AbortSignal } = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await apiFetch(`${API_BASE_URL}/conta-azul/analise/compras?${searchParams.toString()}`, {
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(await parseError(response, 'Falha ao consultar compras da Conta Azul.'));
  }
  return response.json();
};

export const fetchContaAzulAnaliseVendas = async (params: Record<string, unknown> = {}, options: { signal?: AbortSignal } = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await apiFetch(`${API_BASE_URL}/conta-azul/analise/vendas?${searchParams.toString()}`, {
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(await parseError(response, 'Falha ao consultar vendas da Conta Azul.'));
  }
  return response.json();
};

export const fetchContaAzulAnaliseClientes = async (params: Record<string, unknown> = {}, options: { signal?: AbortSignal } = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await apiFetch(`${API_BASE_URL}/conta-azul/analise/clientes?${searchParams.toString()}`, {
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(await parseError(response, 'Falha ao consultar clientes da Conta Azul.'));
  }
  return response.json();
};

export const fetchContaAzulAnaliseFiscalCfop = async (params: Record<string, unknown> = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await apiFetch(`${API_BASE_URL}/conta-azul/analise/fiscal/cfop?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error(await parseError(response, 'Falha ao consultar CFOP da Conta Azul.'));
  }
  return response.json();
};

export const fetchContaAzulAnaliseFiscalHierarquica = async (params: Record<string, unknown> = {}) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await apiFetch(`${API_BASE_URL}/conta-azul/analise/fiscal/hierarquica?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error(await parseError(response, 'Falha ao consultar hierarquia fiscal da Conta Azul.'));
  }
  return response.json();
};
