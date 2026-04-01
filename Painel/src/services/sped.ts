import type { ConsultaKpiResponse } from './nfe';
import { API_BASE_URL, apiFetch } from './api';
import { buildFiscalSearchParams } from './fiscal';

interface RequestOptions {
  signal?: AbortSignal;
}

export interface ImportacaoSpedArquivoResultado {
  arquivo: string;
  cnpj_emitente?: string | null;
  status: 'importado' | 'duplicado' | 'erro';
  mensagem: string;
}

export interface ImportacaoSpedResponse {
  status: string;
  total_arquivos: number;
  importados: number;
  duplicados: number;
  erros: number;
  resultados: ImportacaoSpedArquivoResultado[];
}

export interface ImportacaoSpedPendenciasResponse {
  status: string;
  cnpj_emitente: string;
  total_pendentes: number;
  possui_pendentes: boolean;
}

export interface ProcessamentoSpedResponse {
  status: string;
  cnpj_emitente: string;
  total_linhas: number;
  total_registros_identificados: number;
  total_arquivos_processados: number;
  banco_sped: string;
  resumo_registros: Array<{ registro: string; quantidade: number }>;
}

export const importarSpedArquivo = async (file: File, cnpjEmpresaOrigem: string): Promise<ImportacaoSpedResponse> => {
  const formData = new FormData();
  formData.append('arquivos', file);

  const cnpjDigits = cnpjEmpresaOrigem.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_empresa_origem: cnpjDigits });

  const response = await apiFetch(`${API_BASE_URL}/sped/importar?${searchParams.toString()}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao importar SPED.' }));
    throw new Error(error.detail ?? 'Falha ao importar SPED.');
  }

  return response.json() as Promise<ImportacaoSpedResponse>;
};

export const consultarPendenciasSped = async (cnpjEmitente: string): Promise<ImportacaoSpedPendenciasResponse> => {
  const digits = cnpjEmitente.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_emitente: digits });

  const response = await apiFetch(`${API_BASE_URL}/sped/pendencias?${searchParams.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar pendências do SPED.' }));
    throw new Error(error.detail ?? 'Falha ao consultar pendências do SPED.');
  }

  return response.json() as Promise<ImportacaoSpedPendenciasResponse>;
};

export const processarSpedsImportados = async (cnpjEmitente: string): Promise<ProcessamentoSpedResponse> => {
  const digits = cnpjEmitente.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_emitente: digits });

  const response = await apiFetch(`${API_BASE_URL}/sped/processar-importados?${searchParams.toString()}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao processar arquivos SPED.' }));
    throw new Error(error.detail ?? 'Falha ao processar arquivos SPED.');
  }

  return response.json() as Promise<ProcessamentoSpedResponse>;
};

export type ConsultaSpedKpiResponse = ConsultaKpiResponse;

export const fetchSpedKpis = async (params: { emitente_cnpj?: string; periodo_ano?: number; periodo_mes?: number; limite?: number; offset?: number } = {}): Promise<ConsultaSpedKpiResponse> => {
  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/sped/kpis?${searchParams.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar KPIs do SPED.' }));
    throw new Error(error.detail ?? 'Falha ao consultar KPIs do SPED.');
  }

  return response.json() as Promise<ConsultaSpedKpiResponse>;
};

export interface RankingFornecedorCompra {
  fornecedor: string;
  valor_total: number | string;
  quantidade_documentos: number;
}

export interface RankingProdutoCompra {
  produto: string;
  valor_total: number | string;
  quantidade_total: number | string;
}

export interface AnaliseComprasResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  total_comprado: number | string;
  top_fornecedores_valor: RankingFornecedorCompra[];
  top_fornecedores_quantidade: RankingFornecedorCompra[];
  top_produtos_valor: RankingProdutoCompra[];
  top_produtos_quantidade: RankingProdutoCompra[];
  relatorio_ia?: string | null;
}

export interface SerieMensalComprasItem {
  periodo_ano: number;
  periodo_mes: number;
  total_comprado: number | string;
}

export interface DashboardComprasResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  anos_disponiveis: number[];
  resumo_atual: AnaliseComprasResponse;
  resumo_anterior: AnaliseComprasResponse;
  serie_mensal: SerieMensalComprasItem[];
}

export const fetchSpedAnaliseCompras = async (params: { 
    emitente_cnpj?: string; 
    periodo_ano?: number; 
    periodo_mes?: number; 
    limite?: number; 
    gerar_relatorio_ia?: boolean;
    formato_relatorio?: 'executivo' | 'analitico';
    layout?: string;
  } = {}, options: RequestOptions = {}): Promise<AnaliseComprasResponse> => {

  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/sped/analise/compras?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar análise de compras.' }));
    throw new Error(error.detail ?? 'Falha ao consultar análise de compras.');
  }

  return response.json() as Promise<AnaliseComprasResponse>;
};

export const fetchSpedDashboardCompras = async (
  params: {
    emitente_cnpj?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
  } = {},
  options: RequestOptions = {},
): Promise<DashboardComprasResponse> => {
  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/sped/analise/compras/dashboard?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar dashboard de compras.' }));
    throw new Error(error.detail ?? 'Falha ao consultar dashboard de compras.');
  }

  return response.json() as Promise<DashboardComprasResponse>;
};

export interface AnaliseVendasResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  total_vendido: number | string;
  top_cfops_valor: Array<{
    cfop: string;
    descricao: string;
    valor_total: number | string;
    participacao_percentual: number | string;
  }>;
  top_regioes_valor: Array<{ regiao: string; valor_total: number | string; quantidade_documentos: number }>;
  top_cidades_valor: Array<{ cidade: string; uf?: string; valor_total: number | string; quantidade_documentos: number }>;
  top_clientes_valor: Array<{ cliente: string; valor_total: number | string; quantidade_documentos: number }>;
  top_clientes_quantidade: Array<{ cliente: string; valor_total: number | string; quantidade_documentos: number }>;
  top_produtos_valor: RankingProdutoCompra[];
  top_produtos_quantidade: RankingProdutoCompra[];
  relatorio_ia?: string | null;
}

export interface SerieMensalVendasItem {
  periodo_ano: number;
  periodo_mes: number;
  total_vendido: number | string;
  quantidade_notas: number;
  total_impostos: number | string;
}

export interface DashboardVendasResumo {
  total_vendido: number | string;
  quantidade_notas: number;
  total_impostos: number | string;
  ticket_medio: number | string;
  top_clientes: Array<{ cliente?: string; valor_total?: number | string }>;
  top_produtos: Array<{ produto?: string; valor_total?: number | string }>;
  top_cidades: Array<{ cidade?: string; valor_total?: number | string }>;
}

export interface DashboardVendasResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  anos_disponiveis: number[];
  resumo_atual: DashboardVendasResumo;
  resumo_anterior: DashboardVendasResumo;
  serie_mensal: SerieMensalVendasItem[];
}

export const fetchSpedAnaliseVendas = async (params: {
    emitente_cnpj?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
    gerar_relatorio_ia?: boolean;
    formato_relatorio?: 'executivo' | 'analitico';
    layout?: string;
  } = {}, options: RequestOptions = {}): Promise<AnaliseVendasResponse> => {

  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/sped/analise/vendas?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar análise de vendas.' }));
    throw new Error(error.detail ?? 'Falha ao consultar análise de vendas.');
  }

  return response.json() as Promise<AnaliseVendasResponse>;
};

export const fetchSpedDashboardVendas = async (
  params: {
    emitente_cnpj?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
  } = {},
  options: RequestOptions = {},
): Promise<DashboardVendasResponse> => {
  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/sped/analise/vendas/dashboard?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar dashboard de vendas.' }));
    throw new Error(error.detail ?? 'Falha ao consultar dashboard de vendas.');
  }

  return response.json() as Promise<DashboardVendasResponse>;
};

export interface AnaliseClientesResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  total_vendido: number | string;
  total_clientes: number;
  top_clientes_valor: Array<{
    cliente: string;
    valor_total: number | string;
    quantidade_documentos: number;
    ticket_medio: number | string;
    percentual_participacao: number | string;
  }>;
  top_clientes_quantidade: Array<{
    cliente: string;
    valor_total: number | string;
    quantidade_documentos: number;
    ticket_medio: number | string;
    percentual_participacao: number | string;
  }>;
  relatorio_ia?: string | null;
}

export const fetchSpedAnaliseClientes = async (params: {
    emitente_cnpj?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
    gerar_relatorio_ia?: boolean;
    formato_relatorio?: 'executivo' | 'analitico';
  } = {}, options: RequestOptions = {}): Promise<AnaliseClientesResponse> => {

  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/sped/analise/clientes?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar anÃ¡lise de clientes.' }));
    throw new Error(error.detail ?? 'Falha ao consultar anÃ¡lise de clientes.');
  }

  return response.json() as Promise<AnaliseClientesResponse>;
};
