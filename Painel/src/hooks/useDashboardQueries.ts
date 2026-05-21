import { useQuery } from '@tanstack/react-query';
import { createFiscalSourceApi } from '@/services/fiscalSource';
import { createFiscalPeriod, createFiscalQueryKey } from '@/utils/fiscalPeriod';

interface DashboardQueryParams {
  emitenteCnpj?: string;
  email?: string;
  temSped?: boolean;
  year: number;
  selectedMonth: string;
  monthNumber: number;
  hasEmitenteCnpj: boolean;
}

export function useDashboardComprasQueries({
  emitenteCnpj,
  email,
  temSped,
  year,
  selectedMonth,
  hasEmitenteCnpj
}: DashboardQueryParams) {
  const fiscalApi = createFiscalSourceApi(temSped);
  const fiscalPeriod = createFiscalPeriod(year, selectedMonth);

  const dashboardQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'dashboard-compras',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
      period: fiscalPeriod,
    }),
    queryFn: () => fiscalApi.dashboardCompras({
      emitente_cnpj: emitenteCnpj,
      email,
      ...fiscalPeriod.params,
      limite: 5,
    }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  return { dashboardQuery };
}

export function useDashboardVendasQueries({
  emitenteCnpj,
  email,
  temSped,
  year,
  selectedMonth,
  hasEmitenteCnpj
}: DashboardQueryParams) {
  const fiscalApi = createFiscalSourceApi(temSped);
  const fiscalPeriod = createFiscalPeriod(year, selectedMonth);

  const dashboardQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'dashboard-vendas',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
      period: fiscalPeriod,
    }),
    queryFn: () => fiscalApi.dashboardVendas({
      emitente_cnpj: emitenteCnpj,
      email,
      ...fiscalPeriod.params,
      limite: 5,
    }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const mapQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'dashboard-vendas-mapa',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
      period: fiscalPeriod,
    }),
    queryFn: () => fiscalApi.analiseVendas({
      emitente_cnpj: emitenteCnpj,
      email,
      ...fiscalPeriod.params,
      limite: 500,
    }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  return { dashboardQuery, mapQuery };
}
