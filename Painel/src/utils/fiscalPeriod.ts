export const ALL_MONTHS = 'all';

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
