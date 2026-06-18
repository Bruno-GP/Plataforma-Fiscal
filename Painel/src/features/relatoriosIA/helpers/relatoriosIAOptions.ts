import { formatCurrency, monthLabels } from '@/utils/formatters';

import type { ReportFormat, ReportOption, ReportType } from '../types';

export const monthOptions = [
  { value: 'all', label: 'Ano completo' },
  ...monthLabels.map((label, index) => ({ value: String(index + 1), label })),
] as const satisfies readonly ReportOption<string>[];

export const reportTypeOptions = [
  { value: 'compras', label: 'Compras' },
  { value: 'vendas', label: 'Vendas' },
  { value: 'clientes', label: 'Clientes' },
] as const satisfies readonly ReportOption<ReportType>[];

export const reportFormatOptions = [
  {
    value: 'executivo',
    label: 'Executivo',
    description: 'Resumo objetivo com os principais indicadores e conclusões.',
  },
  {
    value: 'analitico',
    label: 'Analítico',
    description: 'Visão mais detalhada para aprofundar a leitura dos dados.',
  },
] as const satisfies readonly ReportOption<ReportFormat>[];

export const getTotalPeriodoLabel = (reportType: ReportType) => {
  if (reportType === 'compras') {
    return 'comprado';
  }

  if (reportType === 'clientes') {
    return 'faturado';
  }

  return 'vendido';
};

export const buildRelatoriosIATitle = (formatLabel: string, periodoDescricao: string) =>
  `Relatório ${formatLabel.toLowerCase()} (${periodoDescricao})`;

export const buildRelatoriosIASubtitle = (
  formatLabel: string,
  totalPeriodoLabel: string,
  totalPeriodo: number,
) => `Formato solicitado: ${formatLabel}. Total ${totalPeriodoLabel} no período: ${formatCurrency(totalPeriodo)}`;
