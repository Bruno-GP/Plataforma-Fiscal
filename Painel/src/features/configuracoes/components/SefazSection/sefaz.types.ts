export type SefazDirecaoFiltro = 'todas' | 'emitidas' | 'recebidas';
export type SefazSituacaoFiltro = 'todas' | 'autorizada' | 'cancelada' | 'denegada';
export type SefazManifestacaoFiltro = 'todas' | 'sim' | 'nao';

export type SefazManifestacaoTipo = 'ciencia' | 'confirmada' | 'desconhecida' | 'nao_realizada';

export interface SefazCertificadoStatus {
  ativo: boolean;
  cnpj_titular: string | null;
  data_validade: string | null;
  dias_restantes: number | null;
}

export interface SefazSyncResponse {
  status: string;
  message: string;
  empresa_id: number;
}

export interface SefazDocumento {
  id: number;
  chave_acesso: string;
  tipo_documento: string;
  direcao: 'emitida' | 'recebida' | string;
  cnpj_emitente: string;
  cnpj_destinatario: string | null;
  nsu: string;
  data_emissao: string | null;
  valor_total: string | number | null;
  situacao: 'autorizada' | 'cancelada' | 'denegada' | string | null;
  manifestacao_status: string | null;
  criado_em: string | null;
  atualizado_em: string | null;
}

export interface SefazDocumentoDetalhe extends SefazDocumento {
  xml_armazenado_base64: string | null;
}

export interface SefazDocumentoListResponse {
  total: number;
  limit: number;
  offset: number;
  resultados: SefazDocumento[];
}

export interface SefazManifestacaoRequest {
  tipo_manifestacao: SefazManifestacaoTipo;
}

export interface SefazManifestacaoResponse {
  documento_id: number;
  manifestacao_status: string;
}

export interface SefazSyncLog {
  id: number;
  empresa_id: number;
  iniciado_em: string;
  finalizado_em: string | null;
  documentos_novos: number;
  nsu_inicial: string | null;
  nsu_final: string | null;
  status: string;
  erro_detalhe: string | null;
}

export interface SefazSyncLogListResponse {
  total: number;
  limit: number;
  offset: number;
  resultados: SefazSyncLog[];
}

