import { API_BASE_URL, apiFetch } from './api';

export interface CnpjEnriquecimento {
  status: string;
  cnpj: string;
  razao_social: string | null;
  cnae_fiscal: string | null;
  cnae_fiscal_descricao: string | null;
  estado: string | null;
  cidade: string | null;
  municipio_id: string | null;
  codigo_ibge: string | null;
}

export const fetchCnpjEnriquecimento = async (cnpj: string): Promise<CnpjEnriquecimento> => {
  const cnpjNormalizado = cnpj.replace(/[^0-9A-Za-z]/g, '');

  const response = await apiFetch(`${API_BASE_URL}/cnpj/${cnpjNormalizado}/enriquecer`);

  if (!response.ok) {
    const errorData = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(errorData?.detail ?? 'Nao foi possivel buscar os dados do CNPJ.');
  }

  return response.json() as Promise<CnpjEnriquecimento>;
};
