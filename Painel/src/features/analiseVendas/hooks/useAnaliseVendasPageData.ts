import { useMemo } from 'react';

import { useAuth } from '@/contexts/AuthContext';
import { useDashboardVendasQueries } from '@/hooks/useDashboardQueries';
import { useFiscalYearList } from '@/hooks/useFiscalYears';
import { usePeriodFilter } from '@/hooks/usePeriodFilter';
import { formatCurrency, hasValidEmitenteCnpj, monthLabels, safePercentage } from '@/utils/formatters';

import { 
  buildAnaliseVendasChartMessage, 
  buildAnaliseVendasEvolutionData, 
  buildAnaliseVendasRankingViewModel, 
  buildAnaliseVendasStats 
} from '../helpers/analiseVendasViewModel';
import type {
  AnaliseVendasDashboardQueryData,
  AnaliseVendasMapQueryData,
} from '../types';

export function useAnaliseVendasPageData() {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

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
    temSped: user?.tem_sped,
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

  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const chartMessage = buildAnaliseVendasChartMessage({
    isLoading: dashboardQuery.isLoading,
    isError: dashboardQuery.isError,
    selectedMonthLabel,
    selectedYear,
  });
  const hasChartData = salesEvolutionData.length > 0;

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
    salesEvolutionData,
    hasChartData,
    chartMessage,
    selectedMonthLabel,
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
