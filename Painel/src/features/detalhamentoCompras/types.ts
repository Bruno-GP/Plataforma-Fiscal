import type { LucideIcon } from 'lucide-react';

export interface DetalhamentoComprasStatConfig {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend: 'up' | 'down';
  accentClass: string;
}

export interface DetalhamentoComprasRankingPanel {
  title: string;
  description: string;
  items: any[];
  emptyMessage: string;
  loadingMessage?: string;
}

