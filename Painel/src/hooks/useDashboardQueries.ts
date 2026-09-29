import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { SessionUser } from '@/services/api';
import { createFiscalSourceApi } from '@/services/fiscalSource';
import { createFiscalPeriod, createFiscalQueryKey } from '@/utils/fiscalPeriod';
import { normalizeCnpj } from '@/utils/formatters';

interface DashboardQueryParams {
  emitenteCnpj?: string;
  email?: string;
  temSped?: boolean | Pick<SessionUser, 'tem_sped' | 'tem_conta_azul' | 'tem_xml'> | null;
  year: number;
  selectedMonth: string;
  monthNumber: number;
  hasEmitenteCnpj: boolean;
}

const DASHBOARD_YEARS_CACHE_KEY = 'dashboard_fiscal_years';

type DashboardYearsCache = Record<string, number[]>;
type FiscalYearsResponse = {
  resultados?: Array<{ periodo_ano?: number | null }>;
};

const getDashboardYearsCacheKey = (
  emitenteCnpj: string | undefined,
  sourceKey: string,
  scope: 'compras' | 'vendas',
) => [sourceKey, scope, emitenteCnpj ? normalizeCnpj(emitenteCnpj) : undefined].filter(Boolean).join(':');

const readDashboardYearsCache = (
  emitenteCnpj: string | undefined,
  sourceKey: string,
  scope: 'compras' | 'vendas',
) => {
  if (typeof window === 'undefined' || !emitenteCnpj) {
    return undefined;
  }

  try {
    const cache = JSON.parse(localStorage.getItem(DASHBOARD_YEARS_CACHE_KEY) ?? '{}') as DashboardYearsCache;
    return cache[getDashboardYearsCacheKey(emitenteCnpj, sourceKey, scope)];
  } catch {
    return undefined;
  }
};

const saveDashboardYearsCache = (
  emitenteCnpj: string | undefined,
  sourceKey: string,
  scope: 'compras' | 'vendas',
  years: number[] | undefined,
) => {
  if (typeof window === 'undefined' || !emitenteCnpj || !years?.length) {
    return;
  }

  try {
    const cache = JSON.parse(localStorage.getItem(DASHBOARD_YEARS_CACHE_KEY) ?? '{}') as DashboardYearsCache;
    cache[getDashboardYearsCacheKey(emitenteCnpj, sourceKey, scope)] = [...years].sort((a, b) => b - a);
    localStorage.setItem(DASHBOARD_YEARS_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // Cache local e opcional: falhas de storage nao devem bloquear o dashboard.
  }
};

const deriveYearsFromKpis = (data: FiscalYearsResponse | undefined) => {
  const years = new Set<number>();

  data?.resultados?.forEach((item) => {
    if (item.periodo_ano) {
      years.add(item.periodo_ano);
    }
  });

  return [...years].sort((a, b) => b - a);
};

const useCachedFiscalPeriod = (
  emitenteCnpj: string | undefined,
  sourceKey: string,
  scope: 'compras' | 'vendas',
  year: number,
  selectedMonth: string,
  knownYears?: number[],
) => {
  const cachedYears = useMemo(
    () => readDashboardYearsCache(emitenteCnpj, sourceKey, scope),
    [emitenteCnpj, sourceKey, scope],
  );

  const fiscalYears = knownYears?.length ? knownYears : cachedYears;
  const effectiveYear = fiscalYears?.length && !fiscalYears.includes(year) ? fiscalYears[0] : year;

  return {
    cachedYears,
    fiscalPeriod: createFiscalPeriod(effectiveYear, selectedMonth),
  };
};

export function useDashboardComprasQueries({
  emitenteCnpj,
  email,
  temSped,
  year,
  selectedMonth,
  hasEmitenteCnpj
}: DashboardQueryParams) {
  const fiscalApi = createFiscalSourceApi(temSped);
  const cachedYears = readDashboardYearsCache(emitenteCnpj, fiscalApi.sourceKey, 'compras');
  const yearsQuery = useQuery({
    queryKey: ['dashboard-years', emitenteCnpj, fiscalApi.sourceKey, 'compras'],
    queryFn: () => fiscalApi.kpis({
      emitente_cnpj: emitenteCnpj,
      email,
      limite: 120,
    }) as Promise<FiscalYearsResponse>,
    enabled: hasEmitenteCnpj && !cachedYears?.length,
    staleTime: 5 * 60 * 1000,
  });
  const knownYears = deriveYearsFromKpis(yearsQuery.data);
  const { fiscalPeriod } = useCachedFiscalPeriod(
    emitenteCnpj,
    fiscalApi.sourceKey,
    'compras',
    year,
    selectedMonth,
    knownYears,
  );
  const isFiscalPeriodReady = Boolean(cachedYears?.length || knownYears.length || yearsQuery.isError);

  const dashboardQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'dashboard-compras',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
      period: fiscalPeriod,
    }),
    queryFn: ({ signal }) => fiscalApi.dashboardCompras({
      emitente_cnpj: emitenteCnpj,
      email,
      ...fiscalPeriod.params,
      limite: 5,
    }, { signal }),
    enabled: hasEmitenteCnpj && isFiscalPeriodReady,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    saveDashboardYearsCache(emitenteCnpj, fiscalApi.sourceKey, 'compras', dashboardQuery.data?.anos_disponiveis);
  }, [dashboardQuery.data?.anos_disponiveis, emitenteCnpj, fiscalApi.sourceKey]);

  useEffect(() => {
    saveDashboardYearsCache(emitenteCnpj, fiscalApi.sourceKey, 'compras', knownYears);
  }, [emitenteCnpj, fiscalApi.sourceKey, knownYears]);

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
  const cachedYears = readDashboardYearsCache(emitenteCnpj, fiscalApi.sourceKey, 'vendas');
  const yearsQuery = useQuery({
    queryKey: ['dashboard-years', emitenteCnpj, fiscalApi.sourceKey, 'vendas'],
    queryFn: () => fiscalApi.kpis({
      emitente_cnpj: emitenteCnpj,
      email,
      limite: 120,
    }) as Promise<FiscalYearsResponse>,
    enabled: hasEmitenteCnpj && !cachedYears?.length,
    staleTime: 5 * 60 * 1000,
  });
  const knownYears = deriveYearsFromKpis(yearsQuery.data);
  const { fiscalPeriod } = useCachedFiscalPeriod(
    emitenteCnpj,
    fiscalApi.sourceKey,
    'vendas',
    year,
    selectedMonth,
    knownYears,
  );
  const isFiscalPeriodReady = Boolean(cachedYears?.length || knownYears.length || yearsQuery.isError);

  const dashboardQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'dashboard-vendas',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
      period: fiscalPeriod,
    }),
    queryFn: ({ signal }) => fiscalApi.dashboardVendas({
      emitente_cnpj: emitenteCnpj,
      email,
      ...fiscalPeriod.params,
      limite: 5,
    }, { signal }),
    enabled: hasEmitenteCnpj && isFiscalPeriodReady,
    staleTime: 5 * 60 * 1000,
  });

  const mapQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'dashboard-vendas-mapa',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
      period: fiscalPeriod,
    }),
    queryFn: ({ signal }) => fiscalApi.analiseVendas({
      emitente_cnpj: emitenteCnpj,
      email,
      ...fiscalPeriod.params,
      limite: 500,
    }, { signal }),
    enabled: hasEmitenteCnpj && isFiscalPeriodReady,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    saveDashboardYearsCache(emitenteCnpj, fiscalApi.sourceKey, 'vendas', dashboardQuery.data?.anos_disponiveis);
  }, [dashboardQuery.data?.anos_disponiveis, emitenteCnpj, fiscalApi.sourceKey]);

  useEffect(() => {
    saveDashboardYearsCache(emitenteCnpj, fiscalApi.sourceKey, 'vendas', knownYears);
  }, [emitenteCnpj, fiscalApi.sourceKey, knownYears]);

  return { dashboardQuery, mapQuery };
}
