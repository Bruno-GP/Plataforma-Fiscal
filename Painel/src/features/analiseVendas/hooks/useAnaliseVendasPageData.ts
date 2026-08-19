import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/contexts/AuthContext';
import { useDashboardVendasQueries } from '@/hooks/useDashboardQueries';
import { useFiscalYearList } from '@/hooks/useFiscalYears';
import { usePeriodFilter } from '@/hooks/usePeriodFilter';
import { getFiscalSource } from '@/services/fiscalSource';
import { fetchIndicadores, fetchMetas, type MetaResponse } from '@/services/metas';
import { formatCurrency, hasValidEmitenteCnpj, monthLabels, safePercentage } from '@/utils/formatters';

import { 
  buildAnaliseVendasChartMessage, 
  buildAnaliseVendasEvolutionData, 
  buildAnaliseVendasRankingViewModel, 
  buildAnaliseVendasStats 
} from '../helpers/analiseVendasViewModel';
import type {
  AnaliseVendasDashboardQueryData,
  AnaliseVendasEvolutionPoint,
  AnaliseVendasMapQueryData,
} from '../types';

const parseDateOnly = (value: string) => {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
};

const getMonthStart = (year: number, month: number) => new Date(year, month - 1, 1);

const getMonthEnd = (year: number, month: number) => new Date(year, month, 0);

const metaOverlapsMonth = (meta: MetaResponse, year: number, month: number) => {
  const inicio = parseDateOnly(meta.periodo_inicio);
  const fim = parseDateOnly(meta.periodo_fim);

  return inicio <= getMonthEnd(year, month) && fim >= getMonthStart(year, month);
};

const countCoveredMonths = (meta: MetaResponse) => {
  const inicio = parseDateOnly(meta.periodo_inicio);
  const fim = parseDateOnly(meta.periodo_fim);
  let total = 0;

  for (
    let cursor = new Date(inicio.getFullYear(), inicio.getMonth(), 1);
    cursor <= fim;
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1)
  ) {
    total += 1;
  }

  return Math.max(total, 1);
};

const getMonthlyTarget = (meta: MetaResponse) => (
  meta.periodo_tipo === 'mensal' ? meta.valor_alvo : meta.valor_alvo / countCoveredMonths(meta)
);

const buildSalesVsMetaData = (
  salesData: AnaliseVendasEvolutionPoint[],
  meta: MetaResponse | null,
  selectedMonth: string,
  monthNumber: number,
  year: number,
) => {
  if (!meta) {
    return salesData;
  }

  const salesByMonth = new Map(salesData.map((item) => [item.month, item.faturamento]));
  const months = selectedMonth === 'all' ? Array.from({ length: 12 }, (_, index) => index + 1) : [monthNumber];
  const monthlyTarget = getMonthlyTarget(meta);

  return months.reduce<AnaliseVendasEvolutionPoint[]>((acc, month) => {
    const label = monthLabels[month - 1] ?? `Mês ${month}`;
    const hasSales = salesByMonth.has(label);
    const hasMeta = metaOverlapsMonth(meta, year, month);

    if (hasSales || hasMeta) {
      acc.push({
        month: label,
        faturamento: salesByMonth.get(label) ?? 0,
        meta: hasMeta ? monthlyTarget : null,
      });
    }

    return acc;
  }, []);
};

const buildMetaSummary = (data: AnaliseVendasEvolutionPoint[]) => {
  const totalMeta = data.reduce((total, point) => total + (point.meta ?? 0), 0);

  if (!totalMeta) {
    return null;
  }

  const totalRealizado = data.reduce((total, point) => total + point.faturamento, 0);
  const percentual = (totalRealizado / totalMeta) * 100;
  const diferenca = totalRealizado - totalMeta;
  const diferencaFormatada = formatCurrency(Math.abs(diferenca));
  const status = diferenca >= 0 ? `acima da meta em ${diferencaFormatada}` : `faltam ${diferencaFormatada}`;

  return `${percentual.toFixed(1)}% da meta, ${status}`;
};

export function useAnaliseVendasPageData() {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const fiscalSource = getFiscalSource(user);
  const indicatorProfile = fiscalSource === 'sped' ? 'sped' : 'xml';

  const {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    monthNumber,
    year,
    faturamentoPeriodo,
  } = usePeriodFilter();

  const { dashboardQuery, mapQuery } = useDashboardVendasQueries({
    emitenteCnpj,
    email: user?.email,
    temSped: user,
    year,
    selectedMonth,
    monthNumber,
    hasEmitenteCnpj,
  });

  const { availableYears } = useFiscalYearList({
    years: dashboardQuery.data?.anos_disponiveis,
    selectedYear,
    setSelectedYear,
    fallbackYear: year,
  });

  const dashboardData = dashboardQuery.data as AnaliseVendasDashboardQueryData | undefined;
  const mapData = mapQuery.data as AnaliseVendasMapQueryData | undefined;

  const indicatorsQuery = useQuery({
    queryKey: ['dashboard-vendas', 'metas', 'indicadores', indicatorProfile, emitenteCnpj],
    queryFn: () => fetchIndicadores(indicatorProfile),
    enabled: hasEmitenteCnpj && fiscalSource !== 'conta_azul',
    staleTime: 5 * 60 * 1000,
  });

  const faturamentoIndicator = useMemo(
    () => indicatorsQuery.data?.find((indicador) => indicador.chave === 'faturamento') ?? null,
    [indicatorsQuery.data],
  );

  const metasQuery = useQuery({
    queryKey: ['dashboard-vendas', 'metas', 'ativas', faturamentoIndicator?.id, emitenteCnpj],
    queryFn: () => fetchMetas({ status: 'ativa', indicador_id: faturamentoIndicator?.id }),
    enabled: hasEmitenteCnpj && Boolean(faturamentoIndicator?.id),
    staleTime: 90 * 1000,
  });

  const currentData = dashboardData?.resumo_atual;
  const previousData = dashboardData?.resumo_anterior;

  const { stats, totalFaturamento } = useMemo(
    () => buildAnaliseVendasStats({
      currentData,
      previousData,
      selectedMonth,
      year,
      faturamentoPeriodo,
    }),
    [currentData, faturamentoPeriodo, previousData, selectedMonth, year],
  );

  const salesEvolutionData = useMemo(
    () => buildAnaliseVendasEvolutionData(dashboardData?.serie_mensal, selectedMonth, monthNumber),
    [dashboardData?.serie_mensal, monthNumber, selectedMonth],
  );

  const activeRevenueMeta = useMemo(() => {
    const metas = (metasQuery.data?.resultados ?? []).filter((meta) => meta.status === 'ativa');
    return metas.find((meta) => {
      if (selectedMonth === 'all') {
        return Array.from({ length: 12 }, (_, index) => index + 1).some((month) => metaOverlapsMonth(meta, year, month));
      }

      return metaOverlapsMonth(meta, year, monthNumber);
    }) ?? null;
  }, [metasQuery.data, monthNumber, selectedMonth, year]);

  const salesVsMetaData = useMemo(
    () => buildSalesVsMetaData(salesEvolutionData, activeRevenueMeta, selectedMonth, monthNumber, year),
    [activeRevenueMeta, monthNumber, salesEvolutionData, selectedMonth, year],
  );

  const metaComparisonSummary = useMemo(
    () => buildMetaSummary(salesVsMetaData),
    [salesVsMetaData],
  );

  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const chartMessage = buildAnaliseVendasChartMessage({
    isLoading: dashboardQuery.isLoading,
    isError: dashboardQuery.isError,
    selectedMonthLabel,
    selectedYear,
  });
  const hasChartData = salesVsMetaData.length > 0;

  const rankingViewModel = useMemo(
    () => {
      const resolvePercentual = (valorTotal?: number | string) => safePercentage(valorTotal || 0, totalFaturamento);

      return buildAnaliseVendasRankingViewModel({
        currentData,
        mapData,
        resolvePercentual,
      });
    },
    [currentData, mapData, totalFaturamento],
  );

  return {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    availableYears,
    stats,
    salesEvolutionData: salesVsMetaData,
    hasChartData,
    chartMessage,
    selectedMonthLabel,
    hasMetaComparison: Boolean(activeRevenueMeta),
    metaComparisonSummary,
    metaComparisonLabel: activeRevenueMeta?.titulo ?? null,
    dashboardQuery,
    totalFaturamento,
    rankings: rankingViewModel.rankings,
    mapTopCidadesItems: rankingViewModel.mapTopCidadesItems.length
      ? rankingViewModel.mapTopCidadesItems
      : rankingViewModel.topCidadesItems,
    mapTopRegioesItems: rankingViewModel.mapTopRegioesItems,
    formatCurrency,
  };
}
