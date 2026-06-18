import type { LucideIcon } from 'lucide-react';

export interface ReformaTributariaTotals {
  debitos: number;
  creditos: number;
  saldo: number;
  recolher: number;
}

export interface ReformaTributariaStatConfig {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend: string;
  accentClass: string;
  appendPreviousMonthLabel: boolean;
}
