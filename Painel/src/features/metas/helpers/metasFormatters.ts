import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';

import type { UnidadeIndicador } from '@/services/metas';

export const formatMetaPeriod = (period: string) => {
  try {
    return format(parseISO(period), 'MMM/yyyy', { locale: ptBR });
  } catch {
    return period;
  }
};

export const formatLongPeriod = (start: string, end: string) => {
  try {
    return `${format(parseISO(start), 'MMM/yyyy', { locale: ptBR })} até ${format(parseISO(end), 'MMM/yyyy', {
      locale: ptBR,
    })}`;
  } catch {
    return `${start} até ${end}`;
  }
};

export const formatIndicatorUnit = (value: number, unidade?: UnidadeIndicador | null) => {
  if (unidade === 'moeda') {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
  }

  if (unidade === 'percentual') {
    return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value)}%`;
  }

  if (unidade === 'dias') {
    return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value)} dias`;
  }

  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value);
};

export const formatCompact = (value: number) =>
  new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value);
