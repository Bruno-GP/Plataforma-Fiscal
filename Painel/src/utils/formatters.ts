import { monthLabels } from '@/services/utils';

export const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);

export const formatPercent = (value: number) => 
  `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

export const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

export const resolvePeriodDescription = (year: number, month: string) => {
  if (month === 'all') {
    return `Acumulado em ${year}`;
  }

  const monthNumber = Number.parseInt(month, 10);
  return `${monthLabels[monthNumber - 1]} de ${year}`;
};

export const parseDecimal = (val: any): number => {
  if (typeof val === 'number') return val;
  if (typeof val === 'string') {
    return parseFloat(val) || 0;
  }
  return 0;
};

export const calculateChange = (current: number | string, previous: number | string) => {
  const cur = parseDecimal(current);
  const prev = parseDecimal(previous);
  return prev ? ((cur - prev) / prev) * 100 : 0;
};

export const safePercentage = (part: number | string, total: number | string) => {
  const p = parseDecimal(part);
  const t = parseDecimal(total);
  if (!t || !p) return null;
  return (p / t) * 100;
};
