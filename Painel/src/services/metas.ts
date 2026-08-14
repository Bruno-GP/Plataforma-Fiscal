import { API_BASE_URL, apiFetch } from './api';
import { parseDecimal } from '@/utils/formatters';

export type TipoMeta = 'crescimento' | 'reducao' | 'manutencao';
export type PeriodoTipo = 'mensal' | 'trimestral' | 'anual' | 'custom';
export type StatusMeta = 'ativa' | 'atingida' | 'nao_atingida' | 'cancelada';
export type UnidadeIndicador = 'moeda' | 'percentual' | 'numero' | 'dias';
export type DirecaoBoa = 'maior_melhor' | 'menor_melhor';
export type IndicadorPerfil = 'xml' | 'sped';
export type StatusRitmo = 'no_caminho' | 'em_risco' | 'fora_da_rota';
export type Tendencia = 'crescimento_forte' | 'crescimento_leve' | 'estavel' | 'queda_leve' | 'queda_forte';

export interface IndicadorResponse {
  id: number;
  chave: string;
  nome: string;
  unidade: UnidadeIndicador;
  direcao_boa: DirecaoBoa;
  perfil: IndicadorPerfil;
}

export interface IndicadorHistoricoPontoResponse {
  periodo: string;
  valor: number;
}

export interface IndicadorHistoricoResponse {
  indicador_id: number;
  resultados: IndicadorHistoricoPontoResponse[];
}

export interface MetaResponse {
  id: number;
  empresa_id: number;
  indicador_id: number;
  titulo: string;
  descricao: string | null;
  valor_alvo: number;
  tipo_meta: TipoMeta;
  periodo_tipo: PeriodoTipo;
  periodo_inicio: string;
  periodo_fim: string;
  status: StatusMeta;
  criado_em: string;
  atualizado_em: string;
}

export interface MetaListResponse {
  total: number;
  resultados: MetaResponse[];
}

export interface AnaliseMetaResponse {
  meta_id: number;
  valor_alvo: number;
  valor_realizado_atual: number;
  percentual_atingido: number;
  tempo_decorrido_pct: number;
  status_ritmo: StatusRitmo;
  tendencia: Tendencia;
  media_periodos_anteriores: number;
  mediana_periodos_anteriores: number;
  desvio_padrao_periodos_anteriores: number;
  variacao_vs_media_pct: number | null;
  diagnostico: string;
  serie_historica: IndicadorHistoricoPontoResponse[];
  projecao_fim_periodo: number;
  comparativo_ano_anterior_pct: number | null;
}

export interface MetaCreatePayload {
  indicador_id: number;
  titulo: string;
  descricao?: string | null;
  valor_alvo: number;
  tipo_meta: TipoMeta;
  periodo_tipo: PeriodoTipo;
  periodo_inicio: string;
  periodo_fim: string;
}

export interface MetaUpdatePayload {
  titulo?: string;
  descricao?: string | null;
  valor_alvo?: number;
  status?: StatusMeta;
}

const parseApiError = async (response: Response, fallback: string) => {
  const error = await response.json().catch(() => null);
  if (typeof error?.detail === 'string' && error.detail.trim()) {
    return error.detail;
  }

  return fallback;
};

const buildSearchParams = (params: Record<string, string | number | undefined | null>) => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value));
    }
  });

  return searchParams;
};

const normalizeIndicador = (item: IndicadorResponse): IndicadorResponse => item;

const normalizeMeta = (item: MetaResponse): MetaResponse => ({
  ...item,
  valor_alvo: parseDecimal(item.valor_alvo),
});

const normalizeMetaList = (payload: MetaListResponse): MetaListResponse => ({
  total: payload.total,
  resultados: payload.resultados.map(normalizeMeta),
});

const normalizeAnalise = (payload: AnaliseMetaResponse): AnaliseMetaResponse => ({
  ...payload,
  valor_alvo: parseDecimal(payload.valor_alvo),
  valor_realizado_atual: parseDecimal(payload.valor_realizado_atual),
  percentual_atingido: parseDecimal(payload.percentual_atingido),
  tempo_decorrido_pct: parseDecimal(payload.tempo_decorrido_pct),
  media_periodos_anteriores: parseDecimal(payload.media_periodos_anteriores),
  mediana_periodos_anteriores: parseDecimal(payload.mediana_periodos_anteriores),
  desvio_padrao_periodos_anteriores: parseDecimal(payload.desvio_padrao_periodos_anteriores),
  variacao_vs_media_pct: payload.variacao_vs_media_pct === null ? null : parseDecimal(payload.variacao_vs_media_pct),
  serie_historica: payload.serie_historica.map((item) => ({
    periodo: item.periodo,
    valor: parseDecimal(item.valor),
  })),
  projecao_fim_periodo: parseDecimal(payload.projecao_fim_periodo),
  comparativo_ano_anterior_pct:
    payload.comparativo_ano_anterior_pct === null ? null : parseDecimal(payload.comparativo_ano_anterior_pct),
});

export const fetchIndicadores = async (perfil: IndicadorPerfil = 'xml'): Promise<IndicadorResponse[]> => {
  const params = buildSearchParams({ perfil });
  const response = await apiFetch(`${API_BASE_URL}/indicadores${params.toString() ? `?${params.toString()}` : ''}`);

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao carregar o catalogo de indicadores.'));
  }

  const payload = (await response.json()) as { resultados: IndicadorResponse[] };
  return payload.resultados.map(normalizeIndicador);
};

export const fetchIndicadorHistorico = async (
  indicadorId: number,
  meses = 12,
): Promise<IndicadorHistoricoResponse> => {
  const params = buildSearchParams({ meses });
  const response = await apiFetch(
    `${API_BASE_URL}/indicadores/${indicadorId}/historico${params.toString() ? `?${params.toString()}` : ''}`,
  );

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao carregar o historico do indicador.'));
  }

  const payload = (await response.json()) as IndicadorHistoricoResponse;
  return {
    indicador_id: payload.indicador_id,
    resultados: payload.resultados.map((item) => ({
      periodo: item.periodo,
      valor: parseDecimal(item.valor),
    })),
  };
};

export const fetchMetas = async (params: { status?: StatusMeta; indicador_id?: number } = {}): Promise<MetaListResponse> => {
  const searchParams = buildSearchParams({
    status: params.status,
    indicador_id: params.indicador_id,
  });
  const response = await apiFetch(`${API_BASE_URL}/metas${searchParams.toString() ? `?${searchParams.toString()}` : ''}`);

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao carregar as metas.'));
  }

  const payload = (await response.json()) as MetaListResponse;
  return normalizeMetaList(payload);
};

export const fetchMeta = async (metaId: number): Promise<MetaResponse> => {
  const response = await apiFetch(`${API_BASE_URL}/metas/${metaId}`);

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao carregar a meta.'));
  }

  return normalizeMeta((await response.json()) as MetaResponse);
};

export const fetchMetaAnalise = async (metaId: number): Promise<AnaliseMetaResponse> => {
  const response = await apiFetch(`${API_BASE_URL}/metas/${metaId}/analise`);

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao carregar a analise da meta.'));
  }

  return normalizeAnalise((await response.json()) as AnaliseMetaResponse);
};

export const createMeta = async (payload: MetaCreatePayload): Promise<MetaResponse> => {
  const response = await apiFetch(`${API_BASE_URL}/metas`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao criar a meta.'));
  }

  return normalizeMeta((await response.json()) as MetaResponse);
};

export const updateMeta = async (metaId: number, payload: MetaUpdatePayload): Promise<MetaResponse> => {
  const response = await apiFetch(`${API_BASE_URL}/metas/${metaId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao atualizar a meta.'));
  }

  return normalizeMeta((await response.json()) as MetaResponse);
};

export const cancelMeta = async (metaId: number): Promise<void> => {
  const response = await apiFetch(`${API_BASE_URL}/metas/${metaId}`, {
    method: 'DELETE',
  });

  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Falha ao cancelar a meta.'));
  }
};
