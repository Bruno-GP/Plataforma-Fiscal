export interface FiscalQueryParams {
  emitente_cnpj?: string;
  email?: string;
  periodo_ano?: number;
  periodo_mes?: number;
  limite?: number;
  offset?: number;
  gerar_relatorio_ia?: boolean;
  formato_relatorio?: 'executivo' | 'analitico';
  layout?: string;
}

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

export const normalizeCnpjParam = (value?: string): string | null => {
  if (!value) {
    return null;
  }

  const digits = value.replace(/\D/g, '');
  if (!digits || digits.length < 14) {
    return null;
  }

  if ([...digits].every((digit) => digit === '0')) {
    return null;
  }

  return digits;
};

export const buildFiscalSearchParams = (params: FiscalQueryParams = {}) => {
  const searchParams = new URLSearchParams();
  const cnpjParam = normalizeCnpjParam(params.emitente_cnpj);

  if (cnpjParam) {
    searchParams.set('emitente_cnpj', cnpjParam);
  } else if (params.email) {
    searchParams.set('email', params.email);
  }

  if (params.periodo_ano) searchParams.set('periodo_ano', String(params.periodo_ano));
  if (params.periodo_mes) searchParams.set('periodo_mes', String(params.periodo_mes));
  if (params.limite) searchParams.set('limite', String(params.limite));
  if (params.offset) searchParams.set('offset', String(params.offset));
  if (params.gerar_relatorio_ia) searchParams.set('gerar_relatorio_ia', 'true');
  if (params.formato_relatorio) searchParams.set('formato_relatorio', params.formato_relatorio);
  if (params.layout?.trim()) searchParams.set('layout', params.layout.trim());

  return searchParams;
};
