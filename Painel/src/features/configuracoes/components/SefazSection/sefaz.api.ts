import { API_BASE_URL, apiFetch } from '@/services/api';

import type {
  SefazCertificadoStatus,
  SefazDocumento,
  SefazDocumentoDetalhe,
  SefazDocumentoListResponse,
  SefazManifestacaoRequest,
  SefazManifestacaoResponse,
  SefazSyncLogListResponse,
  SefazSyncResponse,
  SefazSyncStatus,
} from './sefaz.types';

interface ApiErrorDetail {
  detail?: string | { msg?: string }[];
}

const extractApiErrorMessage = (errorData: ApiErrorDetail | null, fallback: string) => {
  if (!errorData?.detail) {
    return fallback;
  }

  if (typeof errorData.detail === 'string') {
    return errorData.detail;
  }

  const firstDetail = errorData.detail[0];
  if (firstDetail?.msg) {
    return firstDetail.msg;
  }

  return fallback;
};

const readErrorMessage = async (response: Response, fallback: string) => {
  const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
  return extractApiErrorMessage(errorData, fallback);
};

export interface SefazDocumentosParams {
  direcao?: 'emitidas' | 'recebidas';
  situacao?: 'autorizada' | 'cancelada' | 'denegada';
  manifestacao_pendente?: boolean;
  data_inicio?: string;
  data_fim?: string;
  limit?: number;
  offset?: number;
}

export interface SefazSyncLogParams {
  limit?: number;
  offset?: number;
}

export const fetchSefazCertificadoStatus = async () => {
  const response = await apiFetch(`${API_BASE_URL}/sefaz/certificados/status`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, 'Nao foi possivel carregar o status do certificado SEFAZ.'));
  }

  return response.json() as Promise<SefazCertificadoStatus>;
};

export const uploadSefazCertificado = async (arquivo: File, senha: string) => {
  const formData = new FormData();
  formData.append('arquivo', arquivo);
  formData.append('senha', senha);

  const response = await apiFetch(`${API_BASE_URL}/sefaz/certificados`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, 'Nao foi possivel salvar o certificado SEFAZ.'));
  }

  return response.json() as Promise<SefazCertificadoStatus>;
};

export const syncSefazAgora = async () => {
  const response = await apiFetch(`${API_BASE_URL}/sefaz/sync`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, 'Nao foi possivel iniciar a sincronizacao SEFAZ.'));
  }

  return response.json() as Promise<SefazSyncResponse>;
};

export const fetchSefazSyncStatus = async () => {
  const response = await apiFetch(`${API_BASE_URL}/sefaz/sync-status`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, 'Nao foi possivel carregar o status de sincronizacao SEFAZ.'));
  }

  return response.json() as Promise<SefazSyncStatus>;
};

export const fetchSefazDocumentos = async (params: SefazDocumentosParams = {}) => {
  const searchParams = new URLSearchParams();

  if (params.direcao && params.direcao !== 'emitidas' && params.direcao !== 'recebidas') {
    throw new Error('Filtro de direcao invalido.');
  }

  if (params.direcao) {
    searchParams.set('direcao', params.direcao === 'emitidas' ? 'emitida' : 'recebida');
  }

  if (params.situacao) {
    searchParams.set('situacao', params.situacao);
  }

  if (typeof params.manifestacao_pendente === 'boolean') {
    searchParams.set('manifestacao_pendente', params.manifestacao_pendente ? 'true' : 'false');
  }

  if (params.data_inicio) {
    searchParams.set('data_inicio', params.data_inicio);
  }

  if (params.data_fim) {
    searchParams.set('data_fim', params.data_fim);
  }

  searchParams.set('limit', String(params.limit ?? 10));
  searchParams.set('offset', String(params.offset ?? 0));

  const response = await apiFetch(`${API_BASE_URL}/sefaz/documentos?${searchParams.toString()}`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, 'Nao foi possivel carregar os documentos SEFAZ.'));
  }

  return response.json() as Promise<SefazDocumentoListResponse>;
};

export const fetchSefazDocumentoDetalhe = async (documentoId: number) => {
  const response = await apiFetch(`${API_BASE_URL}/sefaz/documentos/${documentoId}`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, 'Nao foi possivel carregar o detalhe do documento.'));
  }

  return response.json() as Promise<SefazDocumentoDetalhe>;
};

export const manifestarSefazDocumento = async (documentoId: number, payload: SefazManifestacaoRequest) => {
  const response = await apiFetch(`${API_BASE_URL}/sefaz/documentos/${documentoId}/manifestacao`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, 'Nao foi possivel enviar a manifestacao do documento.'));
  }

  return response.json() as Promise<SefazManifestacaoResponse>;
};

export const fetchSefazSyncLog = async (params: SefazSyncLogParams = {}) => {
  const searchParams = new URLSearchParams();
  searchParams.set('limit', String(params.limit ?? 10));
  searchParams.set('offset', String(params.offset ?? 0));

  const response = await apiFetch(`${API_BASE_URL}/sefaz/sync-log?${searchParams.toString()}`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, 'Nao foi possivel carregar o historico de sincronizacao.'));
  }

  return response.json() as Promise<SefazSyncLogListResponse>;
};
