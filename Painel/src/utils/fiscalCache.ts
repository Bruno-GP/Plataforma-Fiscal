import type { QueryClient } from '@tanstack/react-query';

type FiscalCacheSource = 'nfe' | 'sped';

// Consultas que dependem dos dados consolidados após importação/processamento fiscal.
const DASHBOARD_QUERY_KEYS = [
  ['dashboard-vendas'],
  ['dashboard-vendas-mapa'],
  ['dashboard-compras'],
] as const;

const REFORMA_TRIBUTARIA_QUERY_KEYS = [
  ['reforma-tributaria-apuracao'],
  ['reforma-tributaria-memoria'],
] as const;

const FISCAL_KPI_QUERY_KEYS: Record<FiscalCacheSource, readonly (readonly string[])[]> = {
  nfe: [
    ['nfe-kpis'],
    ['nfe-kpis-years'],
    ['nfe-kpis-clientes'],
    ['kpis-years'],
    ['kpis-clientes'],
  ],
  sped: [
    ['kpis'],
    ['kpis-years'],
    ['kpis-clientes'],
  ],
};

const invalidateQueryKeys = (queryClient: QueryClient, queryKeys: readonly (readonly string[])[]) =>
  Promise.all(queryKeys.map((queryKey) => queryClient.invalidateQueries({ queryKey })));

export const invalidateFiscalDashboardCache = (queryClient: QueryClient) =>
  invalidateQueryKeys(queryClient, DASHBOARD_QUERY_KEYS);

export const invalidateReformaTributariaCache = (queryClient: QueryClient) =>
  invalidateQueryKeys(queryClient, REFORMA_TRIBUTARIA_QUERY_KEYS);

export const invalidateFiscalKpiCache = (queryClient: QueryClient, source: FiscalCacheSource) =>
  invalidateQueryKeys(queryClient, FISCAL_KPI_QUERY_KEYS[source]);

/**
 * Deve ser chamado após jobs fiscais concluídos para atualizar visões derivadas do mesmo dado base.
 */
export const invalidateFiscalProcessingCache = (queryClient: QueryClient, source: FiscalCacheSource) =>
  Promise.all([
    invalidateFiscalDashboardCache(queryClient),
    invalidateReformaTributariaCache(queryClient),
    invalidateFiscalKpiCache(queryClient, source),
  ]);
