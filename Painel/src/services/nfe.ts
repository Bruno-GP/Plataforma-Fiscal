import { API_BASE_URL, apiFetch } from './api';
import { buildFiscalSearchParams } from './fiscal';

export { parseDecimal } from './fiscal';

export interface NfeKpi {
  total_vendas: number | string;
  quantidade_notas: number;
  ticket_medio: number | string;
  maior_nota: number | string;
  menor_nota: number | string;
  total_icms: number | string;
  total_ipi: number | string;
  total_pis: number | string;
  total_cofins: number | string;
  top_clientes?: NfeRankingItem[];
  top_produtos?: NfeRankingItem[];
  top_cidades?: NfeRankingItem[];
}

export interface NfeRankingItem {
  cliente?: string;
  produto?: string;
  cidade?: string;
  valor_total?: number | string;
  percentual?: number | string;
}

export interface NfeKpiConsulta {
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  kpis: NfeKpi;
}

export interface ConsultaKpiResponse {
  status: string;
  total: number;
  resultados: NfeKpiConsulta[];
}

export interface FetchKpiParams {
  emitente_cnpj?: string;
  periodo_ano?: number;
  periodo_mes?: number;
  limite?: number;
  offset?: number;
}

interface RequestOptions {
  signal?: AbortSignal;
}

export interface KpiComparativoValor {
  atual: number | string;
  anterior: number | string;
  variacao_percentual?: number | string | null;
}

export interface KpiComparativoQuantidade {
  atual: number;
  anterior: number;
  variacao_percentual?: number | string | null;
}

export interface KpiComparativoResponse {
  status: string;
  periodo_atual_ano: number;
  periodo_atual_mes: number;
  periodo_anterior_ano: number;
  periodo_anterior_mes: number;
  emitente_cnpj?: string | null;
  kpis: {
    total_vendas: KpiComparativoValor;
    quantidade_notas: KpiComparativoQuantidade;
    ticket_medio: KpiComparativoValor;
    maior_nota: KpiComparativoValor;
    menor_nota: KpiComparativoValor;
    total_icms: KpiComparativoValor;
    total_ipi: KpiComparativoValor;
    total_pis: KpiComparativoValor;
    total_cofins: KpiComparativoValor;
  };
}

export const fetchNfeKpis = async (params: FetchKpiParams = {}): Promise<ConsultaKpiResponse> => {
  const searchParams = buildFiscalSearchParams(params);
  const queryString = searchParams.toString();
  const response = await apiFetch(`${API_BASE_URL}/nfe/kpis${queryString ? `?${queryString}` : ""}`);

  if (!response.ok) {
    throw new Error("Não foi possível carregar os KPIs da NFe.");
  }

  return response.json() as Promise<ConsultaKpiResponse>;
};

export const fetchNfeKpisComparativoAtual = async (
  emitenteCnpj?: string,
  email?: string
): Promise<KpiComparativoResponse> => {
  const searchParams = buildFiscalSearchParams({ emitente_cnpj: emitenteCnpj, email });

  const queryString = searchParams.toString();
  const response = await apiFetch(
    `${API_BASE_URL}/nfe/kpis/comparativo/atual${queryString ? `?${queryString}` : ""}`
  );

  if (!response.ok) {
    throw new Error("Não foi possível carregar o comparativo de KPIs.");
  }

  return response.json() as Promise<KpiComparativoResponse>;
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

export interface ImportacaoXmlArquivoResultado {
  arquivo: string;
  cnpj_emitente?: string | null;
  status: 'importado' | 'duplicado' | 'erro';
  mensagem: string;
}

export interface ImportacaoXmlResponse {
  status: string;
  total_arquivos: number;
  importados: number;
  duplicados: number;
  erros: number;
  resultados: ImportacaoXmlArquivoResultado[];
}

export const importarXmlArquivo = async (
  file: File,
  cnpjEmpresaOrigem: string,
  options: RequestOptions = {},
): Promise<ImportacaoXmlResponse> => {
  return importarXmlArquivos([file], cnpjEmpresaOrigem, options);
}

export const importarXmlArquivos = async (
  files: File[],
  cnpjEmpresaOrigem: string,
  options: RequestOptions = {},
): Promise<ImportacaoXmlResponse> => {
  const formData = new FormData();
  files.forEach((file) => formData.append('arquivos', file));

  const cnpjDigits = cnpjEmpresaOrigem.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_empresa_origem: cnpjDigits });

  const response = await apiFetch(`${API_BASE_URL}/nfe/xml/importar?${searchParams.toString()}`, {
    method: 'POST',
    body: formData,
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao importar XML.' }));
    throw new Error(error.detail ?? 'Falha ao importar XML.');
  }

  return response.json() as Promise<ImportacaoXmlResponse>;
};

export interface ImportacaoXmlPendenciasResponse {
  status: string;
  cnpj_emitente: string;
  total_pendentes: number;
  possui_pendentes: boolean;
}

export const consultarPendenciasXmlImportados = async (
  cnpjEmitente: string
): Promise<ImportacaoXmlPendenciasResponse> => {
  const digits = cnpjEmitente.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_emitente: digits });

  const response = await apiFetch(`${API_BASE_URL}/nfe/xml/pendencias?${searchParams.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar pendências de XML.' }));
    throw new Error(error.detail ?? 'Falha ao consultar pendências de XML.');
  }

  return response.json() as Promise<ImportacaoXmlPendenciasResponse>;
};

export interface ProcessamentoNfePeriodoKpi {
  ano: number;
  mes: number;
  kpis: NfeKpi;
}

export interface ProcessamentoNfeResponse {
  status: string;
  cnpj_emitente: string;
  periodo_ano: number;
  periodo_mes: number;
  periodos_encontrados: Array<{ ano: number; mes: number }>;
  notas_processadas: number;
  itens_processados: number;
  kpis: ProcessamentoNfePeriodoKpi[];
  erros: Array<{ codigo: string; mensagem: string; detalhe?: string }>;
  data_processamento?: string;
}

export const processarXmlsImportados = async (
  cnpjEmitente: string,
  options: RequestOptions = {},
): Promise<ProcessamentoNfeResponse> => {
  const digits = cnpjEmitente.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_emitente: digits });

  const response = await apiFetch(`${API_BASE_URL}/nfe/xml/processar-importados?${searchParams.toString()}`, {
    method: 'POST',
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao processar XMLs importados.' }));
    throw new Error(error.detail ?? 'Falha ao processar XMLs importados.');
  }

  return response.json() as Promise<ProcessamentoNfeResponse>;
};

export const fetchNfeAnaliseCompras = async (
  params: {
    emitente_cnpj?: string;
    email?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
    gerar_relatorio_ia?: boolean;
    formato_relatorio?: 'executivo' | 'analitico';
    layout?: string;
  } = {},
  options: RequestOptions = {},
): Promise<AnaliseComprasResponse> => {
  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/nfe/analise/compras?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar análise de compras da NFe.' }));
    throw new Error(error.detail ?? 'Falha ao consultar análise de compras da NFe.');
  }

  return response.json() as Promise<AnaliseComprasResponse>;
};

export const fetchNfeDashboardCompras = async (
  params: {
    emitente_cnpj?: string;
    email?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
  } = {},
  options: RequestOptions = {},
): Promise<DashboardComprasResponse> => {
  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/nfe/analise/compras/dashboard?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar dashboard de compras da NFe.' }));
    throw new Error(error.detail ?? 'Falha ao consultar dashboard de compras da NFe.');
  }

  return response.json() as Promise<DashboardComprasResponse>;
};

export interface AnaliseVendasResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  total_vendido: number | string;
  top_regioes_valor: Array<{ regiao: string; valor_total: number | string; quantidade_documentos: number }>;
  top_cidades_valor: Array<{ cidade: string; uf?: string; valor_total: number | string; quantidade_documentos: number }>;
  top_clientes_valor: Array<{ cliente: string; valor_total: number | string; quantidade_documentos: number }>;
  top_clientes_quantidade: Array<{ cliente: string; valor_total: number | string; quantidade_documentos: number }>;
  top_produtos_valor: RankingProdutoCompra[];
  top_produtos_quantidade: RankingProdutoCompra[];
  relatorio_ia?: string | null;
}

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

export const fetchNfeAnaliseVendas = async (
  params: {
    emitente_cnpj?: string;
    email?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
    gerar_relatorio_ia?: boolean;
    formato_relatorio?: 'executivo' | 'analitico';
    layout?: string;
  } = {},
  options: RequestOptions = {},
): Promise<AnaliseVendasResponse> => {
  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/nfe/analise/vendas?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar análise de vendas da NFe.' }));
    throw new Error(error.detail ?? 'Falha ao consultar análise de vendas da NFe.');
  }

  return response.json() as Promise<AnaliseVendasResponse>;
};

export const fetchNfeDashboardVendas = async (
  params: {
    emitente_cnpj?: string;
    email?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
  } = {},
  options: RequestOptions = {},
): Promise<DashboardVendasResponse> => {
  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/nfe/analise/vendas/dashboard?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar dashboard de vendas da NFe.' }));
    throw new Error(error.detail ?? 'Falha ao consultar dashboard de vendas da NFe.');
  }

  return response.json() as Promise<DashboardVendasResponse>;
};

export const fetchNfeAnaliseClientes = async (
  params: { emitente_cnpj?: string; email?: string; periodo_ano?: number; periodo_mes?: number; limite?: number; gerar_relatorio_ia?: boolean; formato_relatorio?: 'executivo' | 'analitico' } = {},
  options: RequestOptions = {},
): Promise<AnaliseClientesResponse> => {
  const searchParams = buildFiscalSearchParams(params);

  const response = await apiFetch(`${API_BASE_URL}/nfe/analise/clientes?${searchParams.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar análise de clientes da NFe.' }));
    throw new Error(error.detail ?? 'Falha ao consultar análise de clientes da NFe.');
  }

  return response.json() as Promise<AnaliseClientesResponse>;
};
