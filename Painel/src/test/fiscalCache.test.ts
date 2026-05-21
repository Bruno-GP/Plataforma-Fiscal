import { describe, expect, it, vi } from 'vitest';

import {
  invalidateFiscalDashboardCache,
  invalidateFiscalKpiCache,
  invalidateFiscalProcessingCache,
  invalidateReformaTributariaCache,
} from '@/utils/fiscalCache';

const createQueryClientMock = () => ({
  invalidateQueries: vi.fn(() => Promise.resolve()),
});

describe('fiscalCache helpers', () => {
  it('invalida dashboards fiscais por prefixo', async () => {
    const queryClient = createQueryClientMock();

    await invalidateFiscalDashboardCache(queryClient as never);

    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['dashboard-vendas'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['dashboard-vendas-mapa'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['dashboard-compras'] });
  });

  it('invalida cache da reforma tributaria', async () => {
    const queryClient = createQueryClientMock();

    await invalidateReformaTributariaCache(queryClient as never);

    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['reforma-tributaria-apuracao'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['reforma-tributaria-memoria'] });
  });

  it('invalida KPIs por fonte fiscal', async () => {
    const queryClient = createQueryClientMock();

    await invalidateFiscalKpiCache(queryClient as never, 'nfe');

    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['nfe-kpis'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['nfe-kpis-years'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['nfe-kpis-clientes'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['kpis-years'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['kpis-clientes'] });
  });

  it('invalida cache fiscal completo apos processamento', async () => {
    const queryClient = createQueryClientMock();

    await invalidateFiscalProcessingCache(queryClient as never, 'sped');

    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['dashboard-vendas'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['reforma-tributaria-apuracao'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['kpis'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['kpis-years'] });
    expect(queryClient.invalidateQueries).toHaveBeenCalledTimes(8);
  });
});
