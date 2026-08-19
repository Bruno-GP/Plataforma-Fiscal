import type { LucideIcon } from 'lucide-react';

export interface AnaliseVendasPageProps {
  title?: string;
  subtitle?: string;
}

export interface AnaliseVendasStatConfig {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend: 'up' | 'down';
  accentClass: string;
  appendPreviousMonthLabel?: boolean;
}

export interface AnaliseVendasRankingItem {
  key: string;
  title: string;
  subtitle: string;
  value: string;
  rawValue: number;
  percent: number | null;
  cidade?: string;
  uf?: string;
}

export interface AnaliseVendasRankingSection {
  title: string;
  description: string;
  items: AnaliseVendasRankingItem[];
  emptyMessage: string;
}

export interface AnaliseVendasEvolutionPoint {
  month: string;
  faturamento: number;
  meta?: number | null;
}

export interface AnaliseVendasSerieMensalItem {
  periodo_mes: number;
  total_vendido?: number | string;
}

export interface AnaliseVendasResumo {
  total_vendido?: number | string;
  ticket_medio?: number | string;
  total_impostos?: number | string;
  total_tributos_reforma?: number | string;
  top_clientes?: Array<{ cliente?: string; valor_total?: number | string }>;
  top_produtos?: Array<{ produto?: string; valor_total?: number | string }>;
  top_cidades?: Array<{ cidade?: string; uf?: string; valor_total?: number | string }>;
}

export interface AnaliseVendasMapRegionItem {
  regiao: string;
  rawValue: number;
}

export interface AnaliseVendasMapQueryData {
  top_clientes_valor?: Array<{ cliente?: string; valor_total?: number | string }>;
  top_produtos_valor?: Array<{ produto?: string; valor_total?: number | string }>;
  top_cidades_valor?: Array<{ cidade?: string; uf?: string; valor_total?: number | string }>;
  top_regioes_valor?: Array<{ regiao: string; valor_total?: number | string }>;
}

export interface AnaliseVendasDashboardQueryData {
  resumo_atual?: AnaliseVendasResumo;
  resumo_anterior?: AnaliseVendasResumo;
  serie_mensal?: AnaliseVendasSerieMensalItem[];
  anos_disponiveis?: number[];
}
