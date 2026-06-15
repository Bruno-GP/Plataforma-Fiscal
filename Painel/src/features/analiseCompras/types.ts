import type { LucideIcon } from 'lucide-react';

export interface AnaliseComprasStatConfig {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend: 'up' | 'down';
  accentClass: string;
  appendPreviousMonthLabel?: boolean;
}

export interface AnaliseComprasEvolutionPoint {
  month: string;
  faturamento: number;
}

export interface AnaliseComprasRankingSection {
  title: string;
  description: string;
  items: any[];
  emptyMessage: string;
}

export interface AnaliseComprasSerieMensalItem {
  periodo_mes: number;
  total_comprado?: number | string;
}

export interface AnaliseComprasResumo {
  total_comprado?: number | string;
  total_tributos_reforma?: number | string;
  top_fornecedores_quantidade?: Array<{ quantidade_documentos?: number | string }>;
  top_produtos_quantidade?: Array<{ quantidade_total?: number | string }>;
  top_fornecedores_valor?: Array<{
    fornecedor?: string;
    quantidade_documentos?: number | string;
    valor_total?: number | string;
  }>;
  top_produtos_valor?: Array<{
    produto?: string;
    quantidade_total?: number | string;
    valor_total?: number | string;
  }>;
}

export interface AnaliseComprasDashboardQueryData {
  resumo_atual?: AnaliseComprasResumo;
  resumo_anterior?: AnaliseComprasResumo;
  serie_mensal?: AnaliseComprasSerieMensalItem[];
  anos_disponiveis?: number[];
}
