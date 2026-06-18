import { Scale, TrendingDown, TrendingUp, Users, Percent } from 'lucide-react';

import {
  calculateChange,
  formatCurrency,
  formatPercent,
  monthLabels,
  parseDecimal,
} from '@/utils/formatters';
import { buildRankingItems } from '@/utils/rankingUtils';

import type {
  AnaliseVendasEvolutionPoint,
  AnaliseVendasMapQueryData,
  AnaliseVendasMapRegionItem,
  AnaliseVendasRankingItem,
  AnaliseVendasRankingSection,
  AnaliseVendasResumo,
  AnaliseVendasStatConfig,
  AnaliseVendasSerieMensalItem,
} from '../types';

const buildAnaliseVendasStatDescription = (
  selectedMonth: string,
  year: number,
) => (selectedMonth === 'all'
  ? `vs. mesmo período de ${year - 1}`
  : 'vs. período anterior');

export const buildAnaliseVendasStats = (params: {
  currentData?: AnaliseVendasResumo;
  previousData?: AnaliseVendasResumo;
  selectedMonth: string;
  year: number;
  faturamentoPeriodo: string;
}) => {
  const {
    currentData,
    previousData,
    selectedMonth,
    year,
    faturamentoPeriodo,
  } = params;

  const totalFaturamento = parseDecimal(currentData?.total_vendido ?? 0);
  const totalSalesChange = calculateChange(totalFaturamento, previousData?.total_vendido ?? 0);
  const ticketChange = calculateChange(currentData?.ticket_medio ?? 0, previousData?.ticket_medio ?? 0);
  const totalTaxesChange = calculateChange(currentData?.total_impostos ?? 0, previousData?.total_impostos ?? 0);
  const reformaTaxes = parseDecimal(currentData?.total_tributos_reforma ?? 0);
  const previousReformaTaxes = parseDecimal(previousData?.total_tributos_reforma ?? 0);

  const stats: AnaliseVendasStatConfig[] = [
    {
      title: `Faturamento Mensal${faturamentoPeriodo ? ` (Período ${faturamentoPeriodo})` : ''}`,
      value: formatCurrency(totalFaturamento),
      description: formatPercent(totalSalesChange),
      icon: TrendingUp,
      trend: totalSalesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Comparativo anual',
      value: formatPercent(totalSalesChange),
      description: buildAnaliseVendasStatDescription(selectedMonth, year),
      icon: totalSalesChange >= 0 ? TrendingUp : TrendingDown,
      trend: totalSalesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-emerald-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Ticket Médio',
      value: formatCurrency(parseDecimal(currentData?.ticket_medio ?? 0)),
      description: formatPercent(ticketChange),
      icon: Users,
      trend: ticketChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Impostos sobre vendas',
      value: formatCurrency(parseDecimal(currentData?.total_impostos ?? 0)),
      description: formatPercent(totalTaxesChange),
      icon: Percent,
      trend: totalTaxesChange >= 0 ? 'up' : 'down',
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
  ];

  return { stats, totalFaturamento };
};

export const buildAnaliseVendasEvolutionData = (
  serie: AnaliseVendasSerieMensalItem[] = [],
  selectedMonth: string,
  monthNumber: number,
): AnaliseVendasEvolutionPoint[] => {
  const filteredSerie = selectedMonth === 'all'
    ? serie
    : serie.filter((item) => item.periodo_mes === monthNumber);

  return filteredSerie.map((item) => ({
    month: monthLabels[item.periodo_mes - 1] ?? `Mês ${item.periodo_mes}`,
    faturamento: parseDecimal(item.total_vendido ?? 0),
  }));
};

export const buildAnaliseVendasChartMessage = (params: {
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
    return 'Não foi possível carregar o gráfico.';
  }

  return selectedMonthLabel
    ? `Nenhum dado disponível para ${selectedMonthLabel} de ${selectedYear}.`
    : `Nenhum dado disponível para ${selectedYear}.`;
};

export const buildAnaliseVendasRankingViewModel = (params: {
  currentData?: AnaliseVendasResumo;
  mapData?: AnaliseVendasMapQueryData;
  resolvePercentual: (valorTotal?: number | string) => number | null;
}) => {
  const { currentData, mapData, resolvePercentual } = params;

  const topClientesBase = mapData?.top_clientes_valor?.length
    ? mapData.top_clientes_valor
    : currentData?.top_clientes ?? [];

  const topProdutosBase = mapData?.top_produtos_valor?.length
    ? mapData.top_produtos_valor
    : currentData?.top_produtos ?? [];

  const topCidadesBase = mapData?.top_cidades_valor?.length
    ? mapData.top_cidades_valor
    : currentData?.top_cidades ?? [];

  const topClientesItems = buildRankingItems(
    topClientesBase,
    'cliente',
    'Cliente não identificado',
    resolvePercentual,
  );

  const topProdutosItems = buildRankingItems(
    topProdutosBase,
    'produto',
    'Produto não identificado',
    resolvePercentual,
  );

  const topCidadesItems = buildRankingItems(
    topCidadesBase,
    'cidade_uf',
    'Cidade não identificada',
    resolvePercentual,
  );

  const mapTopCidadesItems = buildRankingItems(
    mapData?.top_cidades_valor ?? [],
    'cidade_uf',
    'Cidade não identificada',
    resolvePercentual,
  );

  const mapTopRegioesItems: AnaliseVendasMapRegionItem[] = (mapData?.top_regioes_valor ?? []).map((regiao) => ({
    regiao: regiao.regiao,
    rawValue: parseDecimal(regiao.valor_total ?? 0),
  }));

  const rankings: AnaliseVendasRankingSection[] = [
    {
      title: 'Top Clientes',
      description: 'Clientes com maior faturamento',
      items: topClientesItems as AnaliseVendasRankingItem[],
      emptyMessage: 'Nenhum cliente registrado.',
    },
    {
      title: 'Top Produtos',
      description: 'Itens com maior faturamento',
      items: topProdutosItems as AnaliseVendasRankingItem[],
      emptyMessage: 'Nenhum produto registrado.',
    },
    {
      title: 'Top Cidades',
      description: 'Cidades com maior faturamento',
      items: topCidadesItems as AnaliseVendasRankingItem[],
      emptyMessage: 'Nenhuma cidade registrada.',
    },
  ];

  return {
    rankings,
    topClientesItems: topClientesItems as AnaliseVendasRankingItem[],
    topProdutosItems: topProdutosItems as AnaliseVendasRankingItem[],
    topCidadesItems: topCidadesItems as AnaliseVendasRankingItem[],
    mapTopCidadesItems: mapTopCidadesItems as AnaliseVendasRankingItem[],
    mapTopRegioesItems,
  };
};
