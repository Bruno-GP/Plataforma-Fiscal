import { useState, useMemo, useEffect } from 'react';

/**
 * Gerencia os estados de controle de período (ano, mês) e garante
 * que o ano atual não sairá da lista de anos disponíveis no servidor.
 */
export function usePeriodFilter(initialYear?: string, initialMonth = 'all') {
  const [selectedYear, setSelectedYear] = useState(initialYear ?? String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState(initialMonth);

  const yearNumber = Number.parseInt(selectedYear, 10);
  const monthNumber = Number.parseInt(selectedMonth, 10);

  // Garante que o ano selecionado existe na lista, senão fallback pro item mais recente
  const ensureValidYear = (availableYears: number[] | undefined) => {
    if (!availableYears?.length) return;

    if (!availableYears.includes(yearNumber)) {
      setSelectedYear(String(availableYears[0]));
    }
  };

  const faturamentoPeriodo = useMemo(() => {
    if (selectedMonth === 'all') {
      return selectedYear;
    }
    return `${String(monthNumber).padStart(2, '0')}/${selectedYear}`;
  }, [monthNumber, selectedMonth, selectedYear]);

  return {
    selectedYear,
    setSelectedYear,
    selectedMonth,
    setSelectedMonth,
    year: yearNumber,
    monthNumber,
    ensureValidYear,
    faturamentoPeriodo,
  };
}
