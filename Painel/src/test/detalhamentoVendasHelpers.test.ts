import { describe, expect, it } from 'vitest';

import {
  buildSpedFiscalNcmHierarchy,
  filterSpedHierarchyRows,
} from '@/pages/components/detalhamentoVendasHelpers';

describe('detalhamentoVendasHelpers SPED', () => {
  const rows = [
    {
      estado: 'SP',
      cidade: 'Sao Paulo - SP',
      uf: 'SP',
      ncm: '01010101',
      descricao_ncm: 'Produtos alimenticios',
      produto_codigo: 'P1',
      produto: 'Cafe torrado',
      faturamento: '100,00',
      imposto_valor: '10,00',
    },
    {
      estado: 'SP',
      cidade: 'Sao Paulo - SP',
      uf: 'SP',
      ncm: '01010101',
      descricao_ncm: 'Produtos alimenticios',
      produto_codigo: 'P1',
      produto: 'Cafe torrado',
      faturamento: '50,00',
      imposto_valor: '5,00',
    },
    {
      estado: 'RJ',
      cidade: 'Rio de Janeiro - RJ',
      uf: 'RJ',
      ncm: '02020202',
      descricao_ncm: 'Bebidas',
      produto_codigo: 'P2',
      produto: 'Suco natural',
      faturamento: '75,00',
      imposto_valor: '7,50',
    },
  ];

  it('filtra linhas SPED por texto normalizado', () => {
    expect(filterSpedHierarchyRows(rows, 'cafe')).toHaveLength(2);
    expect(filterSpedHierarchyRows(rows, 'RIO')).toHaveLength(1);
    expect(filterSpedHierarchyRows(rows, '01010101')).toHaveLength(2);
  });

  it('retorna todas as linhas quando a busca esta vazia', () => {
    expect(filterSpedHierarchyRows(rows, '')).toHaveLength(3);
  });

  it('agrega hierarquia fiscal por NCM e produto', () => {
    const hierarchy = buildSpedFiscalNcmHierarchy(rows);

    expect(hierarchy).toHaveLength(2);
    expect(hierarchy[0]).toMatchObject({
      ncm: '01010101',
      total: 150,
      taxValue: 15,
      taxPercent: 10,
    });
    expect(hierarchy[0]?.products).toHaveLength(1);
    expect(hierarchy[0]?.products[0]).toMatchObject({
      code: 'P1',
      totalValue: 150,
      taxValue: 15,
      taxPercent: 10,
    });
  });

  it('ignora linhas sem item detalhado na hierarquia por NCM', () => {
    const hierarchy = buildSpedFiscalNcmHierarchy([
      ...rows,
      {
        estado: 'MG',
        cidade: 'Belo Horizonte - MG',
        uf: 'MG',
        faturamento: '200,00',
        imposto_valor: '20,00',
        sem_item_detalhado: true,
      },
    ]);

    expect(hierarchy.some((entry) => entry.ncm === '00000000')).toBe(false);
  });
});
