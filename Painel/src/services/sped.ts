import type { ConsultaKpiResponse } from './nfe';

const RAW_API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_BASE_URL = RAW_API_BASE_URL.endsWith('/api')
  ? RAW_API_BASE_URL
  : `${RAW_API_BASE_URL.replace(/\/$/, '')}/api`;

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

  const response = await fetch(`${API_BASE_URL}/sped/importar?${searchParams.toString()}`, {
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

  const response = await fetch(`${API_BASE_URL}/sped/pendencias?${searchParams.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar pendências do SPED.' }));
    throw new Error(error.detail ?? 'Falha ao consultar pendências do SPED.');
  }

  return response.json() as Promise<ImportacaoSpedPendenciasResponse>;
};

export const processarSpedsImportados = async (cnpjEmitente: string): Promise<ProcessamentoSpedResponse> => {
  const digits = cnpjEmitente.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_emitente: digits });

  const response = await fetch(`${API_BASE_URL}/sped/processar-importados?${searchParams.toString()}`, {
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
  const searchParams = new URLSearchParams();
  const digits = params.emitente_cnpj?.replace(/\D/g, '') ?? '';

  if (digits.length === 14) {
    searchParams.set('emitente_cnpj', digits);
  }

  if (params.periodo_ano) searchParams.set('periodo_ano', String(params.periodo_ano));
  if (params.periodo_mes) searchParams.set('periodo_mes', String(params.periodo_mes));
  if (params.limite) searchParams.set('limite', String(params.limite));
  if (params.offset) searchParams.set('offset', String(params.offset));

  const response = await fetch(`${API_BASE_URL}/sped/kpis?${searchParams.toString()}`);

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

export const fetchSpedAnaliseCompras = async (params: { 
    emitente_cnpj?: string; 
    periodo_ano?: number; 
    periodo_mes?: number; 
    limite?: number; 
    gerar_relatorio_ia?: boolean;
    formato_relatorio?: 'executivo' | 'analitico';
    layout?: string;
  } = {}): Promise<AnaliseComprasResponse> => {

  const searchParams = new URLSearchParams();
  const digits = params.emitente_cnpj?.replace(/\D/g, '') ?? '';

  if (digits.length === 14) {
    searchParams.set('emitente_cnpj', digits);
  }

  if (params.periodo_ano) searchParams.set('periodo_ano', String(params.periodo_ano));
  if (params.periodo_mes) searchParams.set('periodo_mes', String(params.periodo_mes));
  if (params.limite) searchParams.set('limite', String(params.limite));
  if (params.gerar_relatorio_ia) searchParams.set('gerar_relatorio_ia', 'true');
  if (params.formato_relatorio) searchParams.set('formato_relatorio', params.formato_relatorio);
  if (params.layout?.trim()) searchParams.set('layout', params.layout.trim());

  const response = await fetch(`${API_BASE_URL}/sped/analise/compras?${searchParams.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar análise de compras.' }));
    throw new Error(error.detail ?? 'Falha ao consultar análise de compras.');
  }

  return response.json() as Promise<AnaliseComprasResponse>;
};

export interface AnaliseVendasResponse {
  status: string;
  emitente_cnpj: string;
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  total_vendido: number | string;
  top_clientes_valor: Array<{ cliente: string; valor_total: number | string; quantidade_documentos: number }>;
  top_clientes_quantidade: Array<{ cliente: string; valor_total: number | string; quantidade_documentos: number }>;
  top_produtos_valor: RankingProdutoCompra[];
  top_produtos_quantidade: RankingProdutoCompra[];
  relatorio_ia?: string | null;
}

export const fetchSpedAnaliseVendas = async (params: {
    emitente_cnpj?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    limite?: number;
    gerar_relatorio_ia?: boolean;
    formato_relatorio?: 'executivo' | 'analitico';
  } = {}): Promise<AnaliseVendasResponse> => {

  const searchParams = new URLSearchParams();
  const digits = params.emitente_cnpj?.replace(/\D/g, '') ?? '';

  if (digits.length === 14) {
    searchParams.set('emitente_cnpj', digits);
  }

  if (params.periodo_ano) searchParams.set('periodo_ano', String(params.periodo_ano));
  if (params.periodo_mes) searchParams.set('periodo_mes', String(params.periodo_mes));
  if (params.limite) searchParams.set('limite', String(params.limite));
  if (params.gerar_relatorio_ia) searchParams.set('gerar_relatorio_ia', 'true');
  if (params.formato_relatorio) searchParams.set('formato_relatorio', params.formato_relatorio);

  const response = await fetch(`${API_BASE_URL}/sped/analise/vendas?${searchParams.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar análise de vendas.' }));
    throw new Error(error.detail ?? 'Falha ao consultar análise de vendas.');
  }

  return response.json() as Promise<AnaliseVendasResponse>;
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
  } = {}): Promise<AnaliseClientesResponse> => {

  const searchParams = new URLSearchParams();
  const digits = params.emitente_cnpj?.replace(/\D/g, '') ?? '';

  if (digits.length === 14) {
    searchParams.set('emitente_cnpj', digits);
  }

  if (params.periodo_ano) searchParams.set('periodo_ano', String(params.periodo_ano));
  if (params.periodo_mes) searchParams.set('periodo_mes', String(params.periodo_mes));
  if (params.limite) searchParams.set('limite', String(params.limite));
  if (params.gerar_relatorio_ia) searchParams.set('gerar_relatorio_ia', 'true');
  if (params.formato_relatorio) searchParams.set('formato_relatorio', params.formato_relatorio);

  const response = await fetch(`${API_BASE_URL}/sped/analise/clientes?${searchParams.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar anÃ¡lise de clientes.' }));
    throw new Error(error.detail ?? 'Falha ao consultar anÃ¡lise de clientes.');
  }

  return response.json() as Promise<AnaliseClientesResponse>;
};
