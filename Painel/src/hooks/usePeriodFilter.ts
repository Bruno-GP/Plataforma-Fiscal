import { useState, useMemo } from 'react';

export function usePeriodFilter(initialYear?: string, initialMonth = 'all') {
  const [selectedMonth, setSelectedMonth] = useState(initialMonth);
  const [selectedYear, setSelectedYear] = useState(initialYear || String(new Date().getFullYear()));

  const monthNumber = Number.parseInt(selectedMonth, 10);
  const year = Number.parseInt(selectedYear, 10);

  const faturamentoPeriodo = useMemo(() => {
    if (selectedMonth === 'all') {
      return selectedYear;
    }
    return `${String(monthNumber).padStart(2, '0')}/${selectedYear}`;
  }, [monthNumber, selectedMonth, selectedYear]);

  return {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    monthNumber,
    year,
    faturamentoPeriodo,
  };
}
