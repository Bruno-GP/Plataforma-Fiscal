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
import {
  fetchContaAzulAnaliseClientes,
  fetchContaAzulAnaliseCompras,
  fetchContaAzulDashboardVendas,
  fetchContaAzulKpis,
} from '@/services/contaAzul';

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

vi.mock('@/services/contaAzul', () => ({
  fetchContaAzulAnaliseClientes: vi.fn(() => Promise.resolve({ source: 'conta-azul-clientes' })),
  fetchContaAzulAnaliseCompras: vi.fn(() => Promise.resolve({ source: 'conta-azul-compras' })),
  fetchContaAzulAnaliseFiscalCfop: vi.fn(() => Promise.resolve({ source: 'conta-azul-cfop' })),
  fetchContaAzulAnaliseFiscalHierarquica: vi.fn(() => Promise.resolve({ source: 'conta-azul-hierarquia' })),
  fetchContaAzulAnaliseVendas: vi.fn(() => Promise.resolve({ source: 'conta-azul-vendas' })),
  fetchContaAzulDashboardCompras: vi.fn(() => Promise.resolve({ source: 'conta-azul-dashboard-compras' })),
  fetchContaAzulDashboardVendas: vi.fn(() => Promise.resolve({ source: 'conta-azul-dashboard-vendas' })),
  fetchContaAzulKpis: vi.fn(() => Promise.resolve({ source: 'conta-azul-kpis' })),
}));

describe('fiscalSource helpers', () => {
  it('resolve metadados da fonte fiscal', () => {
    expect(getFiscalSource(false)).toBe('nfe');
    expect(getFiscalSource(true)).toBe('sped');
    expect(getFiscalSource({ tem_sped: false, tem_conta_azul: true, tem_xml: false })).toBe('conta_azul');
    expect(getFiscalSourceKey(true)).toBe('sped');
    expect(getFiscalSourceLabel(false)).toBe('XML / NFe');
    expect(getFiscalSourceLabel(true)).toBe('SPED Fiscal');
    expect(getFiscalSourceLabel({ tem_sped: false, tem_conta_azul: true, tem_xml: false })).toBe('Conta Azul');
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

  it('roteia chamadas para APIs Conta Azul quando a empresa usa Conta Azul', async () => {
    const fiscalApi = createFiscalSourceApi({ tem_sped: false, tem_conta_azul: true, tem_xml: false });
    const params = { emitente_cnpj: '12345678000199' };
    const options = { signal: new AbortController().signal };

    await fiscalApi.kpis(params);
    await fiscalApi.dashboardVendas(params, options);
    await fiscalApi.analiseCompras(params, options);
    await fiscalApi.analiseClientes(params, options);

    expect(fetchContaAzulKpis).toHaveBeenCalledWith(params);
    expect(fetchContaAzulDashboardVendas).toHaveBeenCalledWith(params, options);
    expect(fetchContaAzulAnaliseCompras).toHaveBeenCalledWith(params, options);
    expect(fetchContaAzulAnaliseClientes).toHaveBeenCalledWith(params, options);
    expect(fiscalApi).toMatchObject({
      source: 'conta_azul',
      sourceKey: 'conta_azul',
      sourceLabel: 'Conta Azul',
      isSped: false,
    });
  });
});
