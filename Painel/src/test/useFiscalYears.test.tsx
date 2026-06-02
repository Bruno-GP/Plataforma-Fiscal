import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import {
  deriveFiscalYears,
  getLatestFiscalEntry,
  normalizeFiscalYears,
  useFiscalYearList,
  useFiscalYears,
} from '@/hooks/useFiscalYears';

describe('useFiscalYears helpers', () => {
  it('deriva anos fiscais ordenados e sem duplicidade', () => {
    expect(deriveFiscalYears([
      { periodo_ano: 2024 },
      { periodo_ano: 2026 },
      { periodo_ano: 2024 },
      { periodo_ano: null },
    ])).toEqual([2026, 2024]);
  });

  it('usa fallback quando nao ha anos validos', () => {
    expect(deriveFiscalYears([], { fallbackYear: 2025 })).toEqual([2025]);
    expect(normalizeFiscalYears(undefined, 2026)).toEqual([2026]);
  });

  it('retorna o lancamento fiscal mais recente por ano e mes', () => {
    expect(getLatestFiscalEntry([
      { periodo_ano: 2025, periodo_mes: 12, id: 'a' },
      { periodo_ano: 2026, periodo_mes: 1, id: 'b' },
      { periodo_ano: 2026, periodo_mes: 3, id: 'c' },
    ])).toMatchObject({ id: 'c' });
  });

  it('ajusta selectedYear quando o ano selecionado nao existe nas entradas', () => {
    const setSelectedYear = vi.fn();

    const { result } = renderHook(() =>
      useFiscalYears({
        entries: [{ periodo_ano: 2026 }, { periodo_ano: 2024 }],
        selectedYear: '2023',
        setSelectedYear,
      }),
    );

    expect(result.current.availableYears).toEqual([2026, 2024]);
    expect(result.current.selectedYearNumber).toBe(2026);
    expect(setSelectedYear).toHaveBeenCalledWith('2026');
  });

  it('mantem selectedYear quando ele existe nas entradas', () => {
    const setSelectedYear = vi.fn();

    const { result } = renderHook(() =>
      useFiscalYears({
        entries: [{ periodo_ano: 2026 }, { periodo_ano: 2024 }],
        selectedYear: '2024',
        setSelectedYear,
      }),
    );

    expect(result.current.availableYears).toEqual([2026, 2024]);
    expect(result.current.selectedYearNumber).toBe(2024);
    expect(setSelectedYear).not.toHaveBeenCalled();
  });

  it('normaliza lista externa de anos e ajusta ano selecionado invalido', () => {
    const setSelectedYear = vi.fn();

    const { result } = renderHook(() =>
      useFiscalYearList({
        years: [2024, 2026, 2025],
        selectedYear: '2023',
        setSelectedYear,
      }),
    );

    expect(result.current.availableYears).toEqual([2026, 2025, 2024]);
    expect(setSelectedYear).toHaveBeenCalledWith('2026');
  });

  it('nao chama setSelectedYear quando lista externa usa fallback', () => {
    const setSelectedYear = vi.fn();

    const { result } = renderHook(() =>
      useFiscalYearList({
        years: undefined,
        selectedYear: '2023',
        setSelectedYear,
        fallbackYear: 2026,
      }),
    );

    expect(result.current.availableYears).toEqual([2026]);
    expect(setSelectedYear).not.toHaveBeenCalled();
  });
});
