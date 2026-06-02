export const ALL_MONTHS = 'all';

/**
 * Representa o período fiscal em dois formatos:
 * `params` segue o contrato da API; `yearKey/monthKey` estabilizam as query keys.
 */
export interface FiscalPeriod {
  year?: number;
  month?: number;
  yearKey: string;
  monthKey: string;
  params: {
    periodo_ano?: number;
    periodo_mes?: number;
  };
}

interface FiscalQueryKeyInput {
  scope: string;
  emitenteCnpj?: string;
  sourceKey: string;
  period?: FiscalPeriod;
  extra?: unknown[];
}

/**
 * Normaliza os filtros de ano/mês vindos da UI antes de montar params e cache keys.
 */
export const createFiscalPeriod = (selectedYear: string | number, selectedMonth = ALL_MONTHS): FiscalPeriod => {
  const yearNumber = typeof selectedYear === 'number' ? selectedYear : Number.parseInt(selectedYear, 10);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const year = Number.isNaN(yearNumber) ? undefined : yearNumber;
  const month = selectedMonth === ALL_MONTHS || Number.isNaN(monthNumber) ? undefined : monthNumber;

  return {
    year,
    month,
    yearKey: year === undefined ? String(selectedYear) : String(year),
    monthKey: selectedMonth,
    params: {
      periodo_ano: year,
      periodo_mes: month,
    },
  };
};

/**
 * Mantém todas as queries fiscais com a mesma ordem de chaves para NFe e SPED.
 */
export const createFiscalQueryKey = ({
  scope,
  emitenteCnpj,
  sourceKey,
  period,
  extra = [],
}: FiscalQueryKeyInput) => [
  scope,
  emitenteCnpj,
  sourceKey,
  ...(period ? [period.yearKey, period.monthKey] : []),
  ...extra,
];

export const getFiscalPeriodDescription = (period: FiscalPeriod, monthLabels: string[]) => {
  if (period.month === undefined) {
    return `Ano ${period.yearKey}`;
  }

  return `${monthLabels[period.month - 1]} de ${period.yearKey}`;
};
