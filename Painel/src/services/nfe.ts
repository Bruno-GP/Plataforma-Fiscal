const RAW_API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const API_BASE_URL = RAW_API_BASE_URL.endsWith("/api")
  ? RAW_API_BASE_URL
  : `${RAW_API_BASE_URL.replace(/\/$/, "")}/api`;

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

export const parseDecimal = (value: unknown): number => {
  if (typeof value === "number") {
    return value;
  }

  if (typeof value !== "string") {
    return 0;
  }

  const cleaned = value.replace(/[^\d,.-]/g, "");
  if (!cleaned) {
    return 0;
  }

  if (cleaned.includes(",") && !cleaned.includes(".")) {
    return Number(cleaned.replace(",", ".")) || 0;
  }

  return Number(cleaned.replace(/,/g, "")) || 0;
};

const normalizeCnpjParam = (value?: string): string | null => {
  if (!value) {
    return null;
  }

  const digits = value.replace(/\D/g, "");
  if (!digits || digits.length < 14) {
    return null;
  }

  if ([...digits].every((digit) => digit === "0")) {
    return null;
  }

  return digits;
};


export const fetchNfeKpis = async (params: FetchKpiParams = {}): Promise<ConsultaKpiResponse> => {
  const searchParams = new URLSearchParams();

  const cnpjParam = normalizeCnpjParam(params.emitente_cnpj);
  if (cnpjParam) {
    searchParams.set("emitente_cnpj", cnpjParam);
  }

  if (params.periodo_ano) {
    searchParams.set("periodo_ano", String(params.periodo_ano));
  }

  if (params.periodo_mes) {
    searchParams.set("periodo_mes", String(params.periodo_mes));
  }

  if (params.limite) {
    searchParams.set("limite", String(params.limite));
  }

  if (params.offset) {
    searchParams.set("offset", String(params.offset));
  }

  const queryString = searchParams.toString();
  const response = await fetch(`${API_BASE_URL}/nfe/kpis${queryString ? `?${queryString}` : ""}`);

  if (!response.ok) {
    throw new Error("Não foi possível carregar os KPIs da NFe.");
  }

  return response.json() as Promise<ConsultaKpiResponse>;
};

export const fetchNfeKpisComparativoAtual = async (
  emitenteCnpj?: string,
  email?: string
): Promise<KpiComparativoResponse> => {
  const searchParams = new URLSearchParams();

  const cnpjParam = normalizeCnpjParam(emitenteCnpj);
  if (cnpjParam) {
    searchParams.set("emitente_cnpj", cnpjParam);
  } else if (email) {
    searchParams.set("email", email);
  }

  const queryString = searchParams.toString();
  const response = await fetch(
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
): Promise<ImportacaoXmlResponse> => {
  const formData = new FormData();
  formData.append('arquivos', file);

  const cnpjDigits = cnpjEmpresaOrigem.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_empresa_origem: cnpjDigits });

  const response = await fetch(`${API_BASE_URL}/nfe/xml/importar?${searchParams.toString()}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao importar XML.' }));
    throw new Error(error.detail ?? 'Falha ao importar XML.');
  }

  return response.json() as Promise<ImportacaoXmlResponse>;
}

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

  const response = await fetch(`${API_BASE_URL}/nfe/xml/pendencias?${searchParams.toString()}`);

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

export const processarXmlsImportados = async (cnpjEmitente: string): Promise<ProcessamentoNfeResponse> => {
  const digits = cnpjEmitente.replace(/\D/g, '');
  const searchParams = new URLSearchParams({ cnpj_emitente: digits });

  const response = await fetch(`${API_BASE_URL}/nfe/xml/processar-importados?${searchParams.toString()}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao processar XMLs importados.' }));
    throw new Error(error.detail ?? 'Falha ao processar XMLs importados.');
  }

  return response.json() as Promise<ProcessamentoNfeResponse>;
};

export const fetchNfeAnaliseCompras = async (
  params: { emitente_cnpj?: string; email?: string; periodo_ano?: number; periodo_mes?: number; limite?: number; gerar_relatorio_ia?: boolean } = {}
): Promise<AnaliseComprasResponse> => {
  const searchParams = new URLSearchParams();
  const cnpjParam = normalizeCnpjParam(params.emitente_cnpj);

  if (cnpjParam) {
    searchParams.set('emitente_cnpj', cnpjParam);
  } else if (params.email) {
    searchParams.set('email', params.email);
  }

  if (params.periodo_ano) searchParams.set('periodo_ano', String(params.periodo_ano));
  if (params.periodo_mes) searchParams.set('periodo_mes', String(params.periodo_mes));
  if (params.limite) searchParams.set('limite', String(params.limite));
  if (params.gerar_relatorio_ia) searchParams.set('gerar_relatorio_ia', 'true');

  const response = await fetch(`${API_BASE_URL}/nfe/analise/compras?${searchParams.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Falha ao consultar análise de compras da NFe.' }));
    throw new Error(error.detail ?? 'Falha ao consultar análise de compras da NFe.');
  }

  return response.json() as Promise<AnaliseComprasResponse>;
};