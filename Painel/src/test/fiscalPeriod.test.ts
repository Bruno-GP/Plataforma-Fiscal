import { describe, expect, it } from 'vitest';

import {
  createFiscalPeriod,
  createFiscalQueryKey,
  getFiscalPeriodDescription,
} from '@/utils/fiscalPeriod';

describe('fiscalPeriod helpers', () => {
  it('normaliza periodo anual sem mes', () => {
    const period = createFiscalPeriod('2026', 'all');

    expect(period.year).toBe(2026);
    expect(period.month).toBeUndefined();
    expect(period.params).toEqual({
      periodo_ano: 2026,
      periodo_mes: undefined,
    });
    expect(period.yearKey).toBe('2026');
    expect(period.monthKey).toBe('all');
  });

  it('normaliza periodo mensal valido', () => {
    const period = createFiscalPeriod('2026', '3');

    expect(period.params).toEqual({
      periodo_ano: 2026,
      periodo_mes: 3,
    });
  });

  it('monta query key fiscal com periodo e extras', () => {
    const period = createFiscalPeriod('2026', '3');

    expect(createFiscalQueryKey({
      scope: 'dashboard-vendas',
      emitenteCnpj: '12345678000199',
      sourceKey: 'nfe',
      period,
      extra: ['abc'],
    })).toEqual([
      'dashboard-vendas',
      '12345678000199',
      'nfe',
      '2026',
      '3',
      'abc',
    ]);
  });

  it('descreve periodo anual e mensal', () => {
    const labels = ['Janeiro', 'Fevereiro', 'Marco'];

    expect(getFiscalPeriodDescription(createFiscalPeriod('2026', 'all'), labels)).toBe('Ano 2026');
    expect(getFiscalPeriodDescription(createFiscalPeriod('2026', '3'), labels)).toBe('Marco de 2026');
  });
});
