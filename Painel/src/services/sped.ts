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