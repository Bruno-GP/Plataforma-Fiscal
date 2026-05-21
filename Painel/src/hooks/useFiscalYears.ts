import { useEffect, useMemo } from 'react';

type FiscalYearEntry = {
  periodo_ano?: number | null;
  periodo_mes?: number | null;
};

interface UseFiscalYearsParams<T extends FiscalYearEntry> {
  entries?: T[];
  selectedYear: string;
  setSelectedYear: (year: string) => void;
  includeCurrentYear?: boolean;
  fallbackYear?: number;
}

interface UseFiscalYearListParams {
  years?: number[];
  selectedYear: string;
  setSelectedYear: (year: string) => void;
  fallbackYear?: number;
}

export const getLatestFiscalEntry = <T extends FiscalYearEntry>(entries: T[] = []) =>
  [...entries].sort((a, b) => {
    const anoA = a.periodo_ano ?? 0;
    const anoB = b.periodo_ano ?? 0;
    if (anoA !== anoB) {
      return anoB - anoA;
    }
    return (b.periodo_mes ?? 0) - (a.periodo_mes ?? 0);
  })[0];

export const deriveFiscalYears = (
  entries: FiscalYearEntry[] = [],
  { includeCurrentYear = false, fallbackYear }: { includeCurrentYear?: boolean; fallbackYear?: number } = {},
) => {
  const years = new Set<number>();

  entries.forEach((item) => {
    if (item.periodo_ano) {
      years.add(item.periodo_ano);
    }
  });

  if (includeCurrentYear) {
    years.add(new Date().getFullYear());
  }

  const sortedYears = [...years].sort((a, b) => b - a);
  return sortedYears.length ? sortedYears : [fallbackYear ?? new Date().getFullYear()];
};

export const normalizeFiscalYears = (years?: number[], fallbackYear = new Date().getFullYear()) =>
  years?.length ? [...years].sort((a, b) => b - a) : [fallbackYear];

export function useFiscalYears<T extends FiscalYearEntry>({
  entries = [],
  selectedYear,
  setSelectedYear,
  includeCurrentYear = false,
  fallbackYear,
}: UseFiscalYearsParams<T>) {
  const availableYears = useMemo(
    () => deriveFiscalYears(entries, { includeCurrentYear, fallbackYear }),
    [entries, fallbackYear, includeCurrentYear],
  );

  useEffect(() => {
    if (!availableYears.length) {
      return;
    }

    if (!availableYears.includes(Number.parseInt(selectedYear, 10))) {
      setSelectedYear(String(availableYears[0]));
    }
  }, [availableYears, selectedYear, setSelectedYear]);

  return {
    availableYears,
    selectedYearNumber: availableYears.includes(Number.parseInt(selectedYear, 10))
      ? Number.parseInt(selectedYear, 10)
      : availableYears[0],
  };
}

export function useFiscalYearList({
  years,
  selectedYear,
  setSelectedYear,
  fallbackYear,
}: UseFiscalYearListParams) {
  const availableYears = useMemo(
    () => normalizeFiscalYears(years, fallbackYear),
    [fallbackYear, years],
  );

  useEffect(() => {
    if (!years?.length) {
      return;
    }

    if (!availableYears.includes(Number.parseInt(selectedYear, 10))) {
      setSelectedYear(String(availableYears[0]));
    }
  }, [availableYears, selectedYear, setSelectedYear, years?.length]);

  return { availableYears };
}
