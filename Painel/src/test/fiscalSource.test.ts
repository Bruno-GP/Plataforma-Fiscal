import { describe, expect, it, vi } from 'vitest';

import {
  createFiscalSourceApi,
  getFiscalSource,
  getFiscalSourceKey,
  getFiscalSourceLabel,
} from '@/services/fiscalSource';
import {
  fetchNfeAnaliseClientes,
  fetchNfeAnaliseCompras,
  fetchNfeDashboardVendas,
  fetchNfeKpis,
} from '@/services/nfe';
import {
  fetchSpedAnaliseClientes,
  fetchSpedAnaliseCompras,
  fetchSpedDashboardVendas,
  fetchSpedKpis,
} from '@/services/sped';

vi.mock('@/services/nfe', () => ({
  fetchNfeAnaliseClientes: vi.fn(() => Promise.resolve({ source: 'nfe-clientes' })),
  fetchNfeAnaliseCompras: vi.fn(() => Promise.resolve({ source: 'nfe-compras' })),
  fetchNfeAnaliseFiscalCfop: vi.fn(() => Promise.resolve({ source: 'nfe-cfop' })),
  fetchNfeAnaliseFiscalHierarquica: vi.fn(() => Promise.resolve({ source: 'nfe-hierarquia' })),
  fetchNfeAnaliseVendas: vi.fn(() => Promise.resolve({ source: 'nfe-vendas' })),
  fetchNfeDashboardCompras: vi.fn(() => Promise.resolve({ source: 'nfe-dashboard-compras' })),
  fetchNfeDashboardVendas: vi.fn(() => Promise.resolve({ source: 'nfe-dashboard-vendas' })),
  fetchNfeKpis: vi.fn(() => Promise.resolve({ source: 'nfe-kpis' })),
}));

vi.mock('@/services/sped', () => ({
  fetchSpedAnaliseClientes: vi.fn(() => Promise.resolve({ source: 'sped-clientes' })),
  fetchSpedAnaliseCompras: vi.fn(() => Promise.resolve({ source: 'sped-compras' })),
  fetchSpedAnaliseFiscalCfop: vi.fn(() => Promise.resolve({ source: 'sped-cfop' })),
  fetchSpedAnaliseFiscalHierarquica: vi.fn(() => Promise.resolve({ source: 'sped-hierarquia' })),
  fetchSpedAnaliseVendas: vi.fn(() => Promise.resolve({ source: 'sped-vendas' })),
  fetchSpedDashboardCompras: vi.fn(() => Promise.resolve({ source: 'sped-dashboard-compras' })),
  fetchSpedDashboardVendas: vi.fn(() => Promise.resolve({ source: 'sped-dashboard-vendas' })),
  fetchSpedKpis: vi.fn(() => Promise.resolve({ source: 'sped-kpis' })),
}));

describe('fiscalSource helpers', () => {
  it('resolve metadados da fonte fiscal', () => {
    expect(getFiscalSource(false)).toBe('nfe');
    expect(getFiscalSource(true)).toBe('sped');
    expect(getFiscalSourceKey(true)).toBe('sped');
    expect(getFiscalSourceLabel(false)).toBe('XML / NFe');
    expect(getFiscalSourceLabel(true)).toBe('SPED Fiscal');
  });

  it('roteia chamadas para APIs NFe quando temSped e falso', async () => {
    const fiscalApi = createFiscalSourceApi(false);
    const params = { emitente_cnpj: '12345678000199' };
    const options = { signal: new AbortController().signal };

    await fiscalApi.kpis(params);
    await fiscalApi.dashboardVendas(params, options);
    await fiscalApi.analiseCompras(params, options);
    await fiscalApi.analiseClientes(params, options);

    expect(fetchNfeKpis).toHaveBeenCalledWith(params);
    expect(fetchNfeDashboardVendas).toHaveBeenCalledWith(params, options);
    expect(fetchNfeAnaliseCompras).toHaveBeenCalledWith(params, options);
    expect(fetchNfeAnaliseClientes).toHaveBeenCalledWith(params, options);
    expect(fetchSpedKpis).not.toHaveBeenCalled();
    expect(fiscalApi).toMatchObject({
      source: 'nfe',
      sourceKey: 'nfe',
      sourceLabel: 'XML / NFe',
      isSped: false,
    });
  });

  it('roteia chamadas para APIs SPED quando temSped e verdadeiro', async () => {
    const fiscalApi = createFiscalSourceApi(true);
    const params = { emitente_cnpj: '12345678000199' };
    const options = { signal: new AbortController().signal };

    await fiscalApi.kpis(params);
    await fiscalApi.dashboardVendas(params, options);
    await fiscalApi.analiseCompras(params, options);
    await fiscalApi.analiseClientes(params, options);

    expect(fetchSpedKpis).toHaveBeenCalledWith(params);
    expect(fetchSpedDashboardVendas).toHaveBeenCalledWith(params, options);
    expect(fetchSpedAnaliseCompras).toHaveBeenCalledWith(params, options);
    expect(fetchSpedAnaliseClientes).toHaveBeenCalledWith(params, options);
    expect(fiscalApi).toMatchObject({
      source: 'sped',
      sourceKey: 'sped',
      sourceLabel: 'SPED Fiscal',
      isSped: true,
    });
  });
});
