import { describe, expect, it } from 'vitest';

import { buildFiscalSearchParams, normalizeCnpjParam, parseDecimal } from '@/services/fiscal';

describe('fiscal helpers', () => {
  it('normaliza CNPJ valido e rejeita entradas inválidas', () => {
    expect(normalizeCnpjParam('12.345.678/0001-99')).toBe('12345678000199');
    expect(normalizeCnpjParam('00000000000000')).toBeNull();
    expect(normalizeCnpjParam('123')).toBeNull();
  });

  it('monta query params fiscais reaproveitáveis', () => {
    const searchParams = buildFiscalSearchParams({
      emitente_cnpj: '12.345.678/0001-99',
      periodo_ano: 2026,
      periodo_mes: 3,
      limite: 5,
      gerar_relatorio_ia: true,
      formato_relatorio: 'executivo',
    });

    expect(searchParams.get('emitente_cnpj')).toBe('12345678000199');
    expect(searchParams.get('periodo_ano')).toBe('2026');
    expect(searchParams.get('periodo_mes')).toBe('3');
    expect(searchParams.get('limite')).toBe('5');
    expect(searchParams.get('gerar_relatorio_ia')).toBe('true');
    expect(searchParams.get('formato_relatorio')).toBe('executivo');
  });

  it('converte decimais textuais para número', () => {
    expect(parseDecimal('1.234,56')).toBeCloseTo(1234.56);
    expect(parseDecimal('1234.56')).toBeCloseTo(1234.56);
    expect(parseDecimal(null)).toBe(0);
  });
});
