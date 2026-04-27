import { API_BASE_URL, apiFetch } from './api';
import { buildFiscalSearchParams, parseDecimal, type FiscalQueryParams } from './fiscal';

interface RequestOptions {
  signal?: AbortSignal;
}

export interface Tributo {
  id: number;
  codigo: string;
  nome: string;
  esfera: string;
  tipo: string;
  descricao?: string | null;
  ativo: boolean;
}

export interface ConsultaTributosResponse {
  status: string;
  total: number;
  resultados: Tributo[];
}

export interface ApuracaoTributariaItem {
  id: number;
  empresa_cnpj: string;
  periodo_ano: number;
  periodo_mes: number;
  tributo_codigo: string;
  tributo_nome: string;
  total_debitos: number | string;
  total_creditos: number | string;
  ajustes_debito: number | string;
  ajustes_credito: number | string;
  estornos_debito: number | string;
  estornos_credito: number | string;
  compensacoes: number | string;
  saldo_apurado: number | string;
  saldo_periodo_anterior: number | string;
  saldo_a_recolher: number | string;
  status: string;
  data_fechamento?: string | null;
}

export interface ConsultaApuracaoTributariaResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  total: number;
  resultados: ApuracaoTributariaItem[];
}

export interface MemoriaCalculoTributariaItem {
  id: number;
  documento_tributo_id?: number | null;
  item_tributo_id?: number | null;
  credito_tributario_id?: number | null;
  debito_tributario_id?: number | null;
  tributo_codigo: string;
  tributo_nome: string;
  empresa_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  etapa_calculo: string;
  base_origem?: number | string | null;
  base_calculo?: number | string | null;
  aliquota_aplicada?: number | string | null;
  percentual_reducao_base?: number | string | null;
  percentual_diferimento?: number | string | null;
  valor_calculado?: number | string | null;
  formula_calculo?: string | null;
  parametros_calculo: Record<string, unknown>;
  resultado_calculo: Record<string, unknown>;
  fonte_dados: string;
  hash_calculo?: string | null;
  criado_em: string;
}

export interface ConsultaMemoriaCalculoTributariaResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  total: number;
  limite: number;
  offset: number;
  resultados: MemoriaCalculoTributariaItem[];
}

export interface ReformaQueryParams extends FiscalQueryParams {
  tributo_codigo?: string;
  documento_tributo_id?: number;
  item_tributo_id?: number;
}

const appendReformaParams = (searchParams: URLSearchParams, params: ReformaQueryParams) => {
  if (params.tributo_codigo?.trim()) searchParams.set('tributo_codigo', params.tributo_codigo.trim());
  if (params.documento_tributo_id) searchParams.set('documento_tributo_id', String(params.documento_tributo_id));
  if (params.item_tributo_id) searchParams.set('item_tributo_id', String(params.item_tributo_id));
};

const readApiError = async (response: Response, fallback: string) => {
  const error = await response.json().catch(() => ({ detail: fallback }));
  return new Error(error.detail ?? fallback);
};

export const fetchReformaTributos = async (
  params: { incluir_inativos?: boolean } = {},
  options: RequestOptions = {},
): Promise<ConsultaTributosResponse> => {
  const searchParams = new URLSearchParams();
  if (params.incluir_inativos) searchParams.set('incluir_inativos', 'true');

  const response = await apiFetch(`${API_BASE_URL}/reforma-tributaria/tributos?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw await readApiError(response, 'Falha ao consultar tributos da Reforma Tributaria.');
  }

  return response.json() as Promise<ConsultaTributosResponse>;
};

export const fetchReformaApuracao = async (
  params: ReformaQueryParams,
  options: RequestOptions = {},
): Promise<ConsultaApuracaoTributariaResponse> => {
  const searchParams = buildFiscalSearchParams(params);
  appendReformaParams(searchParams, params);

  const response = await apiFetch(`${API_BASE_URL}/reforma-tributaria/apuracao?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw await readApiError(response, 'Falha ao consultar apuracao tributaria.');
  }

  return response.json() as Promise<ConsultaApuracaoTributariaResponse>;
};

export const fetchReformaMemoriaCalculo = async (
  params: ReformaQueryParams,
  options: RequestOptions = {},
): Promise<ConsultaMemoriaCalculoTributariaResponse> => {
  const searchParams = buildFiscalSearchParams(params);
  appendReformaParams(searchParams, params);

  const response = await apiFetch(`${API_BASE_URL}/reforma-tributaria/memoria-calculo?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw await readApiError(response, 'Falha ao consultar memoria de calculo tributaria.');
  }

  return response.json() as Promise<ConsultaMemoriaCalculoTributariaResponse>;
};

export const totalizarApuracao = (itens: ApuracaoTributariaItem[]) => {
  return itens.reduce(
    (acc, item) => {
      acc.debitos += parseDecimal(item.total_debitos);
      acc.creditos += parseDecimal(item.total_creditos);
      acc.saldo += parseDecimal(item.saldo_apurado);
      acc.recolher += parseDecimal(item.saldo_a_recolher);
      return acc;
    },
    { debitos: 0, creditos: 0, saldo: 0, recolher: 0 },
  );
};
