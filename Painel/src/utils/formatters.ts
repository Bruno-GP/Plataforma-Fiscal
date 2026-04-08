export const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);

export const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

export const hasValidEmitenteCnpj = (value: string | undefined) => {
  if (!value) return false;
  const digits = value.replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

export const parseDecimal = (value: string | number | undefined | null): number => {
  if (value === undefined || value === null) return 0;
  if (typeof value === 'number') return value;
  const parsed = Number.parseFloat(value);
  return Number.isNaN(parsed) ? 0 : parsed;
};

export const safePercentage = (valorTotal: number | string, total: number | string) => {
  const valorNum = parseDecimal(valorTotal);
  const totalNum = parseDecimal(total);
  if (!totalNum || !valorNum) return null;
  return (valorNum / totalNum) * 100;
};

export const calculateChange = (current: number | string, previous: number | string) => {
  const cur = parseDecimal(current);
  const prev = parseDecimal(previous);
  return prev ? ((cur - prev) / prev) * 100 : 0;
};
