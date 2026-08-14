import type { PeriodoTipo, StatusMeta, StatusRitmo, Tendencia, TipoMeta } from '@/services/metas';

export const STATUS_RITMO_CONFIG: Record<StatusRitmo, { label: string; variant: 'default' | 'warning' | 'destructive' }> = {
  no_caminho: { label: 'No caminho', variant: 'default' },
  em_risco: { label: 'Em risco', variant: 'warning' },
  fora_da_rota: { label: 'Fora da rota', variant: 'destructive' },
};

export const TIPO_META_LABELS: Record<TipoMeta, string> = {
  crescimento: 'Crescimento',
  reducao: 'Redução',
  manutencao: 'Manutenção',
};

export const PERIODO_LABELS: Record<PeriodoTipo, string> = {
  mensal: 'Mensal',
  trimestral: 'Trimestral',
  anual: 'Anual',
  custom: 'Personalizado',
};

export const TENDENCIA_LABELS: Record<Tendencia, string> = {
  crescimento_forte: 'Crescimento forte',
  crescimento_leve: 'Crescimento leve',
  estavel: 'Estável',
  queda_leve: 'Queda leve',
  queda_forte: 'Queda forte',
};

export const STATUS_META_LABELS: Record<StatusMeta, string> = {
  ativa: 'Ativa',
  atingida: 'Atingida',
  nao_atingida: 'Não atingida',
  cancelada: 'Cancelada',
};
