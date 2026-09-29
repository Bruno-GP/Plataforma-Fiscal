export type IntegracaoStatus = 'ATIVA' | 'EXPIRADA' | 'REVOGADA' | 'ERRO' | 'DESCONECTADA';

export type SyncStatus = 'SUCESSO' | 'SUCESSO_PARCIAL' | 'ERRO' | 'EM_PROCESSAMENTO';

export type EntidadeNome = 'pessoas' | 'produtos' | 'categorias' | 'vendas' | 'financeiro';

export interface SyncEntidade {
  entidade: EntidadeNome;
  registros_processados: number;
  status: SyncStatus;
  fim_em: string;
  erro?: string;
}

export interface ContaAzulIntegracao {
  status: IntegracaoStatus;
  ultima_sync_em: string | null;
  token_expira_em: string | null;
  entidades: SyncEntidade[];
}

export interface AuthUrlResponse {
  auth_url: string;
}
