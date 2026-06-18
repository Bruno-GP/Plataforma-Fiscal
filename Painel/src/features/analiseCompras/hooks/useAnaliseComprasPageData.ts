import { useMemo } from 'react';

import { useAuth } from '@/contexts/AuthContext';
import { useDashboardComprasQueries } from '@/hooks/useDashboardQueries';
import { useFiscalYearList } from '@/hooks/useFiscalYears';
import { usePeriodFilter } from '@/hooks/usePeriodFilter';
import { hasValidEmitenteCnpj } from '@/utils/formatters';

import { buildAnaliseComprasViewModel } from '../helpers/analiseComprasViewModel';
import type { AnaliseComprasDashboardQueryData } from '../types';

export function useAnaliseComprasPageData() {
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
  } = usePeriodFilter();

  const { dashboardQuery } = useDashboardComprasQueries({
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

  const dashboardData = dashboardQuery.data as AnaliseComprasDashboardQueryData | undefined;

  const viewModel = useMemo(
    () => buildAnaliseComprasViewModel({
      currentData: dashboardData?.resumo_atual,
      previousData: dashboardData?.resumo_anterior,
      serie_mensal: dashboardData?.serie_mensal,
      selectedMonth,
      selectedYear,
      year,
      monthNumber,
      isLoading: dashboardQuery.isLoading,
      isError: dashboardQuery.isError,
    }),
    [
      dashboardData?.resumo_atual,
      dashboardData?.resumo_anterior,
      dashboardData?.serie_mensal,
      dashboardQuery.isError,
      dashboardQuery.isLoading,
      monthNumber,
      selectedMonth,
      selectedYear,
      year,
    ],
  );

  return {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    availableYears,
    dashboardQuery,
    ...viewModel,
  };
}
