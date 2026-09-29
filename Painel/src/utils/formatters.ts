export const monthLabels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

export const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);

export const formatPercent = (value: number) => 
  `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

export const normalizeCnpj = (value: string | null | undefined): string =>
  (value ?? '').toUpperCase().replace(/[^0-9A-Z]/g, '');

export const isPlaceholderCnpj = (normalized: string): boolean =>
  [...normalized].every((char) => char === '0');

export const hasValidEmitenteCnpj = (value: string | undefined) => {
  const normalized = normalizeCnpj(value);
  return normalized.length === 14 && !isPlaceholderCnpj(normalized);
};

export const resolvePeriodDescription = (year: number, month: string) => {
  if (month === 'all') {
    return `Acumulado em ${year}`;
  }

  const monthNumber = Number.parseInt(month, 10);
  return `${monthLabels[monthNumber - 1]} de ${year}`;
};

export const parseDecimal = (value: unknown): number => {
  if (typeof value === 'number') {
    return value;
  }

  if (typeof value !== 'string') {
    return 0;
  }

  const cleaned = value.replace(/[^\d,.-]/g, '');
  if (!cleaned) {
    return 0;
  }

  const hasComma = cleaned.includes(',');
  const hasDot = cleaned.includes('.');

  if (hasComma && hasDot) {
    const lastComma = cleaned.lastIndexOf(',');
    const lastDot = cleaned.lastIndexOf('.');

    if (lastComma > lastDot) {
      return Number(cleaned.replace(/\./g, '').replace(',', '.')) || 0;
    }

    return Number(cleaned.replace(/,/g, '')) || 0;
  }

  if (hasComma) {
    return Number(cleaned.replace(',', '.')) || 0;
  }

  return Number(cleaned) || 0;
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
