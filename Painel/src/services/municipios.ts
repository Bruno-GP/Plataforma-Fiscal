import { API_BASE_URL, apiFetch } from './api';

export interface MunicipioCatalogoItem {
  municipio_id: string;
  codigo_ibge: string;
  nome: string;
  uf: string;
}

export interface UFCatalogoItem {
  uf: string;
  label: string;
  quantidade_municipios: number;
}

export const fetchUfsCatalogo = async (busca = ''): Promise<UFCatalogoItem[]> => {
  const searchParams = new URLSearchParams();
  if (busca.trim()) {
    searchParams.set('busca', busca.trim());
  }

  const response = await apiFetch(`${API_BASE_URL}/municipios/ufs${searchParams.toString() ? `?${searchParams.toString()}` : ''}`);
  if (!response.ok) {
    throw new Error('Não foi possível carregar as UFs do catálogo.');
  }

  return response.json() as Promise<UFCatalogoItem[]>;
};

export const fetchMunicipiosPorUf = async (uf: string, busca = ''): Promise<MunicipioCatalogoItem[]> => {
  const searchParams = new URLSearchParams();
  searchParams.set('uf', uf.trim().toUpperCase());
  if (busca.trim()) {
    searchParams.set('busca', busca.trim());
  }

  const response = await apiFetch(`${API_BASE_URL}/municipios/cidades?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error('Não foi possível carregar as cidades do catálogo.');
  }

  return response.json() as Promise<MunicipioCatalogoItem[]>;
};
