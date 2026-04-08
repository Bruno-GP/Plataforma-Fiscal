import { useQuery } from '@tanstack/react-query';
import { fetchNfeDashboardVendas, fetchNfeAnaliseVendas, fetchNfeDashboardCompras, fetchNfeAnaliseCompras } from '@/services/nfe';
import { fetchSpedDashboardVendas, fetchSpedAnaliseVendas, fetchSpedDashboardCompras, fetchSpedAnaliseCompras } from '@/services/sped';

interface BaseDashboardQueryParams {
  emitenteCnpj?: string;
  email?: string;
  temSped?: boolean;
  year: number;
  selectedMonth: string;
  monthNumber: number;
  hasEmitenteCnpj: boolean;
}

export function useDashboardVendasQueries({
  emitenteCnpj,
  email,
  temSped,
  year,
  selectedMonth,
  monthNumber,
  hasEmitenteCnpj,
}: BaseDashboardQueryParams) {
  const dashboardQuery = useQuery({
    queryKey: ['dashboard-vendas', emitenteCnpj, temSped, year, selectedMonth],
    queryFn: () =>
      temSped
        ? fetchSpedDashboardVendas({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          })
        : fetchNfeDashboardVendas({
            emitente_cnpj: emitenteCnpj,
            email: email,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const mapQuery = useQuery({
    queryKey: ['dashboard-vendas-mapa', emitenteCnpj, temSped, year, selectedMonth],
    queryFn: () =>
      temSped
        ? fetchSpedAnaliseVendas({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 500,
          })
        : fetchNfeAnaliseVendas({
            emitente_cnpj: emitenteCnpj,
            email: email,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 500,
          }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  return { dashboardQuery, mapQuery };
}

export function useDashboardComprasQueries({
  emitenteCnpj,
  email,
  temSped,
  year,
  selectedMonth,
  monthNumber,
  hasEmitenteCnpj,
}: BaseDashboardQueryParams) {
  const dashboardQuery = useQuery({
    queryKey: ['dashboard-compras', emitenteCnpj, temSped, year, selectedMonth],
    queryFn: () =>
      temSped
        ? fetchSpedDashboardCompras({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          })
        : fetchNfeDashboardCompras({
            emitente_cnpj: emitenteCnpj,
            email: email,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const mapQuery = useQuery({
    queryKey: ['dashboard-compras-mapa', emitenteCnpj, temSped, year, selectedMonth],
    queryFn: () =>
      temSped
        ? fetchSpedAnaliseCompras({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 500,
          })
        : fetchNfeAnaliseCompras({
            emitente_cnpj: emitenteCnpj,
            email: email,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 500,
          }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  return { dashboardQuery, mapQuery };
}
