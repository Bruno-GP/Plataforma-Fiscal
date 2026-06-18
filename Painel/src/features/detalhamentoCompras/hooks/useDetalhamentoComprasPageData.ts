import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/contexts/AuthContext';
import { useDashboardComprasQueries } from '@/hooks/useDashboardQueries';
import { useFiscalYearList } from '@/hooks/useFiscalYears';
import { usePeriodFilter } from '@/hooks/usePeriodFilter';
import { fetchNfeNotasDetalhadas } from '@/services/nfe';
import { hasValidEmitenteCnpj } from '@/utils/formatters';
import { createFiscalPeriod, createFiscalQueryKey } from '@/utils/fiscalPeriod';

import { buildDetalhamentoComprasViewModel } from '../helpers/detalhamentoComprasViewModel';

export function useDetalhamentoComprasPageData() {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const isSped = Boolean(user?.tem_sped);
  const [openPurchaseSupplierValues, setOpenPurchaseSupplierValues] = useState<string[]>([]);
  const [openPurchaseNcmValues, setOpenPurchaseNcmValues] = useState<string[]>([]);
  const [openPurchaseProductValues, setOpenPurchaseProductValues] = useState<string[]>([]);

  const {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    monthNumber,
    year,
  } = usePeriodFilter();

  const fiscalPeriod = useMemo(
    () => createFiscalPeriod(selectedYear, selectedMonth),
    [selectedMonth, selectedYear],
  );

  const { dashboardQuery } = useDashboardComprasQueries({
    emitenteCnpj,
    email: user?.email,
    temSped: user?.tem_sped,
    year,
    selectedMonth,
    monthNumber,
    hasEmitenteCnpj,
  });

  const notasComprasQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'detalhamento-compras-notas',
      emitenteCnpj,
      sourceKey: 'nfe',
      period: fiscalPeriod,
      extra: [user?.email],
    }),
    queryFn: () => fetchNfeNotasDetalhadas({
      emitente_cnpj: emitenteCnpj,
      email: user?.email,
      ...fiscalPeriod.params,
      tipo_operacao: 'compras',
      limite: 500,
      offset: 0,
    }),
    enabled: hasEmitenteCnpj && !isSped,
    staleTime: 5 * 60 * 1000,
  });

  const { availableYears } = useFiscalYearList({
    years: dashboardQuery.data?.anos_disponiveis,
    selectedYear,
    setSelectedYear,
    fallbackYear: year,
  });

  const currentData = dashboardQuery.data?.resumo_atual;
  const previousData = dashboardQuery.data?.resumo_anterior;

  const viewModel = useMemo(
    () => buildDetalhamentoComprasViewModel({
      currentData,
      previousData,
    }),
    [currentData, previousData],
  );

  return {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    availableYears,
    dashboardQuery,
    notasComprasQuery,
    notasCompras: notasComprasQuery.data?.notas ?? [],
    isSped,
    openPurchaseSupplierValues,
    setOpenPurchaseSupplierValues,
    openPurchaseNcmValues,
    setOpenPurchaseNcmValues,
    openPurchaseProductValues,
    setOpenPurchaseProductValues,
    ...viewModel,
  };
}
