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

export interface SpedKpiItem {
  periodo_ano?: number | null;
  periodo_mes?: number | null;
  emitente_cnpj?: string | null;
  kpis: {
    total_vendas?: number | string | null;
    quantidade_notas?: number | null;
    ticket_medio?: number | string | null;
    maior_nota?: number | string | null;
    menor_nota?: number | string | null;
    total_icms?: number | string | null;
    total_ipi?: number | string | null;
    total_pis?: number | string | null;
    total_cofins?: number | string | null;
    top_clientes?: Array<Record<string, unknown>> | null;
    top_produtos?: Array<Record<string, unknown>> | null;
    top_cidades?: Array<Record<string, unknown>> | null;
  };
}

export interface ConsultaSpedKpiResponse {
  status: string;
  total: number;
  resultados: SpedKpiItem[];
}

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