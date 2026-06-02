export interface FiscalQueryParams {
  emitente_cnpj?: string;
  email?: string;
  periodo_ano?: number;
  periodo_mes?: number;
  nivel_atual?: string;
  estado?: string;
  cidade?: string;
  ncm?: string;
  produto_codigo?: string;
  limite?: number;
  offset?: number;
  gerar_relatorio_ia?: boolean;
  formato_relatorio?: 'executivo' | 'analitico';
  layout?: string;
}

export const MAX_FISCAL_LIMIT = 5000;

export { parseDecimal } from '@/utils/formatters';

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
  if (params.nivel_atual?.trim()) searchParams.set('nivel_atual', params.nivel_atual.trim());
  if (params.estado?.trim()) searchParams.set('estado', params.estado.trim());
  if (params.cidade?.trim()) searchParams.set('cidade', params.cidade.trim());
  if (params.ncm?.trim()) searchParams.set('ncm', params.ncm.trim());
  if (params.produto_codigo?.trim()) searchParams.set('produto_codigo', params.produto_codigo.trim());
  if (params.limite) searchParams.set('limite', String(Math.min(params.limite, MAX_FISCAL_LIMIT)));
  if (params.offset) searchParams.set('offset', String(params.offset));
  if (params.gerar_relatorio_ia) searchParams.set('gerar_relatorio_ia', 'true');
  if (params.formato_relatorio) searchParams.set('formato_relatorio', params.formato_relatorio);
  if (params.layout?.trim()) searchParams.set('layout', params.layout.trim());

  return searchParams;
};
