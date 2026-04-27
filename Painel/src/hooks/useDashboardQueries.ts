import { useQuery } from '@tanstack/react-query';
import { 
  fetchNfeDashboardCompras,
  fetchNfeDashboardVendas,
  fetchNfeAnaliseVendas
} from '@/services/nfe';
import { 
  fetchSpedDashboardCompras,
  fetchSpedDashboardVendas,
  fetchSpedAnaliseVendas
} from '@/services/sped';

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
  monthNumber,
  hasEmitenteCnpj
}: DashboardQueryParams) {
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

  return { dashboardQuery };
}

export function useDashboardVendasQueries({
  emitenteCnpj,
  email,
  temSped,
  year,
  selectedMonth,
  monthNumber,
  hasEmitenteCnpj
}: DashboardQueryParams) {
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
