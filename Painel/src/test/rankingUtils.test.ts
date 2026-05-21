import { describe, expect, it } from 'vitest';

import {
  aggregateClientKpis,
  buildClientRiskItems,
  buildPurchaseQuantityRankingItems,
  buildPurchaseValueRankingItems,
  sumDecimalField,
  sumNumberField,
} from '@/utils/rankingUtils';

describe('rankingUtils helpers', () => {
  it('soma campos numericos e decimais', () => {
    expect(sumNumberField([{ quantidade: 2 }, { quantidade: 3 }], 'quantidade')).toBe(5);
    expect(sumDecimalField([{ valor: '1.234,50' }, { valor: '10,25' }], 'valor')).toBeCloseTo(1244.75);
  });

  it('monta ranking de compras por valor', () => {
    const items = buildPurchaseValueRankingItems(
      [
        { fornecedor: 'Fornecedor A', valor_total: '75,00', quantidade_documentos: 3 },
        { fornecedor: 'Fornecedor B', valor_total: '25,00', quantidade_documentos: 1 },
      ],
      {
        titleField: 'fornecedor',
        fallbackTitle: 'Fornecedor nao identificado',
        totalValue: 100,
        subtitle: (row) => `${row.quantidade_documentos} documentos`,
      },
    );

    expect(items[0]).toMatchObject({
      title: 'Fornecedor A',
      rawValue: 75,
      percent: 75,
      subtitle: '3 documentos',
    });
  });

  it('monta ranking de compras por quantidade', () => {
    const items = buildPurchaseQuantityRankingItems(
      [{ produto: 'Produto A', quantidade_total: '8,5', valor_total: '120,00' }],
      10,
    );

    expect(items[0]).toMatchObject({
      title: 'Produto A',
      rawValue: 120,
      percent: 85,
      subtitle: '8.50 itens comprados',
    });
  });

  it('agrega KPIs de clientes por periodo anual', () => {
    const kpis = aggregateClientKpis([
      {
        kpis: {
          total_vendas: '100,00',
          total_icms: '10,00',
          total_ipi: '5,00',
          total_pis: '2,00',
          total_cofins: '3,00',
          top_clientes: [{ cliente: 'Cliente A', valor_total: '60,00' }],
        },
      },
      {
        kpis: {
          total_vendas: '50,00',
          total_icms: '5,00',
          total_ipi: '1,00',
          total_pis: '1,00',
          total_cofins: '1,00',
          top_clientes: [{ cliente: 'Cliente A', valor_total: '15,00' }],
        },
      },
    ]);

    expect(kpis.total_vendas).toBe(150);
    expect(kpis.total_icms).toBe(15);
    expect(kpis.top_clientes[0]).toMatchObject({
      cliente: 'Cliente A',
      valor_total: 75,
    });
  });

  it('identifica cliente com risco por queda forte', () => {
    const riskItems = buildClientRiskItems({
      resultados: [
        {
          periodo_ano: 2026,
          periodo_mes: 1,
          kpis: {
            top_clientes: [{ cliente: 'Cliente A', valor_total: '100,00' }],
          },
        },
        {
          periodo_ano: 2026,
          periodo_mes: 2,
          kpis: {
            top_clientes: [{ cliente: 'Cliente A', valor_total: '50,00' }],
          },
        },
      ],
      topClientes: [{ cliente: 'Cliente A', valor_total: '50,00' }],
      totalReceita: 100,
    });

    expect(riskItems[0]).toMatchObject({
      cliente: 'Cliente A',
      valorTotal: 50,
      percentual: 50,
      temRisco: true,
    });
  });
});
