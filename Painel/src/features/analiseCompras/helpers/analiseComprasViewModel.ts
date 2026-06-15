import { Box, Package, Scale, ShoppingCart, Truck } from 'lucide-react';

import {
  calculateChange,
  formatCurrency,
  formatPercent,
  monthLabels,
  parseDecimal,
  resolvePeriodDescription,
} from '@/utils/formatters';
import {
  buildPurchaseQuantityRankingItems,
  buildPurchaseValueRankingItems,
  sumDecimalField,
  sumNumberField,
} from '@/utils/rankingUtils';

import type {
  AnaliseComprasDashboardQueryData,
  AnaliseComprasEvolutionPoint,
  AnaliseComprasRankingSection,
  AnaliseComprasResumo,
  AnaliseComprasStatConfig,
} from '../types';

export const buildAnaliseComprasStats = (params: {
  currentData?: AnaliseComprasResumo;
  previousData?: AnaliseComprasResumo;
  selectedMonth: string;
  year: number;
}) => {
  const { currentData, previousData, selectedMonth, year } = params;

  const currentTotalComprado = parseDecimal(currentData?.total_comprado ?? 0);
  const previousTotalComprado = parseDecimal(previousData?.total_comprado ?? 0);
  const currentDocCount = sumNumberField(currentData?.top_fornecedores_quantidade ?? [], 'quantidade_documentos');
  const previousDocCount = sumNumberField(previousData?.top_fornecedores_quantidade ?? [], 'quantidade_documentos');
  const currentItemCount = sumDecimalField(currentData?.top_produtos_quantidade ?? [], 'quantidade_total');
  const previousItemCount = sumDecimalField(previousData?.top_produtos_quantidade ?? [], 'quantidade_total');
  const currentTicketMedio = currentDocCount ? currentTotalComprado / currentDocCount : 0;
  const previousTicketMedio = previousDocCount ? previousTotalComprado / previousDocCount : 0;
  const reformaTaxes = parseDecimal(currentData?.total_tributos_reforma ?? 0);
  const previousReformaTaxes = parseDecimal(previousData?.total_tributos_reforma ?? 0);

  const stats: AnaliseComprasStatConfig[] = [
    {
      title: `Total Comprado (${resolvePeriodDescription(year, selectedMonth)})`,
      value: formatCurrency(currentTotalComprado),
      description: formatPercent(calculateChange(currentTotalComprado, previousTotalComprado)),
      icon: ShoppingCart,
      trend: currentTotalComprado >= previousTotalComprado ? 'up' : 'down',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Documentos de Compra (Top 5 fornecedores)',
      value: currentDocCount.toString(),
      description: formatPercent(calculateChange(currentDocCount, previousDocCount)),
      icon: Truck,
      trend: currentDocCount >= previousDocCount ? 'up' : 'down',
      accentClass: 'border-l-emerald-500',
    },
    {
      title: 'Quantidade Comprada',
      value: currentItemCount.toFixed(2),
      description: formatPercent(calculateChange(currentItemCount, previousItemCount)),
      icon: Package,
      trend: currentItemCount >= previousItemCount ? 'up' : 'down',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Ticket Médio por Compra',
      value: formatCurrency(currentTicketMedio),
      description: formatPercent(calculateChange(currentTicketMedio, previousTicketMedio)),
      icon: Box,
      trend: currentTicketMedio >= previousTicketMedio ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
    {
      title: 'Reforma Tributaria',
      value: formatCurrency(reformaTaxes),
      description: reformaTaxes > 0 ? 'IBS, CBS e IS no periodo' : 'Sem IBS/CBS/IS apurados',
      icon: Scale,
      trend: reformaTaxes >= previousReformaTaxes ? 'up' : 'down',
      accentClass: 'border-l-cyan-500',
    },
  ] as const;

  return {
    stats,
    currentTotalComprado,
    currentItemCount,
    rankingTotalValue: formatCurrency(currentTotalComprado),
  };
};

export const buildAnaliseComprasRankings = (params: {
  currentData?: AnaliseComprasResumo;
  currentTotalComprado: number;
  currentItemCount: number;
}) => {
  const { currentData, currentTotalComprado, currentItemCount } = params;

  const rankings: AnaliseComprasRankingSection[] = [
    {
      title: 'Top Fornecedores',
      description: 'Fornecedores com maior valor de compras no periodo',
      emptyMessage: 'Sem dados para o periodo selecionado.',
      items: buildPurchaseValueRankingItems(currentData?.top_fornecedores_valor ?? [], {
        titleField: 'fornecedor',
        fallbackTitle: 'Fornecedor nao identificado',
        totalValue: currentTotalComprado,
        subtitle: (row) => `${row.quantidade_documentos} documentos`,
      }),
    },
    {
      title: 'Top Produtos por Valor',
      description: 'Produtos com maior valor de compra no periodo',
      emptyMessage: 'Sem dados para o periodo selecionado.',
      items: buildPurchaseValueRankingItems(currentData?.top_produtos_valor ?? [], {
        titleField: 'produto',
        fallbackTitle: 'Produto nao identificado',
        totalValue: currentTotalComprado,
        subtitle: (row) => `Qtd. ${parseDecimal(row.quantidade_total).toFixed(2)}`,
      }),
    },
    {
      title: 'Top Produtos por Quantidade',
      description: 'Produtos mais comprados no periodo',
      emptyMessage: 'Sem dados para o periodo selecionado.',
      items: buildPurchaseQuantityRankingItems(currentData?.top_produtos_quantidade ?? [], currentItemCount),
    },
  ];

  return rankings;
};

export const buildAnaliseComprasEvolutionData = (
  serie: AnaliseComprasDashboardQueryData['serie_mensal'] = [],
  selectedMonth: string,
  monthNumber: number,
): AnaliseComprasEvolutionPoint[] => {
  const filteredSerie = selectedMonth === 'all'
    ? serie
    : serie.filter((item) => item.periodo_mes === monthNumber);

  return filteredSerie.map((item) => ({
    month: monthLabels[item.periodo_mes - 1] ?? `MÃªs ${item.periodo_mes}`,
    faturamento: parseDecimal(item.total_comprado ?? 0),
  }));
};

export const buildAnaliseComprasChartMessage = (params: {
  isLoading: boolean;
  isError: boolean;
  selectedMonthLabel: string | null;
  selectedYear: string;
}) => {
  const { isLoading, isError, selectedMonthLabel, selectedYear } = params;

  if (isLoading) {
    return 'Carregando dados...';
  }

  if (isError) {
    return 'NÃ£o foi possÃ­vel carregar o grÃ¡fico.';
  }

  return selectedMonthLabel
    ? `Nenhum dado disponÃ­vel para ${selectedMonthLabel} de ${selectedYear}.`
    : `Nenhum dado disponÃ­vel para ${selectedYear}.`;
};

export const buildAnaliseComprasViewModel = (params: {
  currentData?: AnaliseComprasResumo;
  previousData?: AnaliseComprasResumo;
  serie_mensal?: AnaliseComprasDashboardQueryData['serie_mensal'];
  selectedMonth: string;
  selectedYear: string;
  year: number;
  monthNumber: number;
  isLoading: boolean;
  isError: boolean;
}) => {
  const {
    currentData,
    previousData,
    serie_mensal,
    selectedMonth,
    selectedYear,
    year,
    monthNumber,
    isLoading,
    isError,
  } = params;

  const { stats, currentTotalComprado, currentItemCount, rankingTotalValue } = buildAnaliseComprasStats({
    currentData,
    previousData,
    selectedMonth,
    year,
  });

  const rankings = buildAnaliseComprasRankings({
    currentData,
    currentTotalComprado,
    currentItemCount,
  });

  const comprasEvolutionData = buildAnaliseComprasEvolutionData(serie_mensal, selectedMonth, monthNumber);
  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const chartMessage = buildAnaliseComprasChartMessage({
    isLoading,
    isError,
    selectedMonthLabel,
    selectedYear,
  });

  return {
    stats,
    rankings,
    rankingTotalValue,
    comprasEvolutionData,
    selectedMonthLabel,
    chartMessage,
    hasChartData: comprasEvolutionData.some((item) => item.faturamento > 0),
  };
};
