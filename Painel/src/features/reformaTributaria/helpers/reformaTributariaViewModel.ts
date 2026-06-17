import { Calculator, FileText, Landmark, ReceiptText } from 'lucide-react';

import { parseDecimal } from '@/services/fiscal';
import { formatCurrency } from '@/utils/formatters';

import type { ApuracaoTributariaItem, MemoriaCalculoTributariaItem } from '@/services/reformaTributaria';

import type { ReformaTributariaStatConfig, ReformaTributariaTotals } from '../types';

export const formatPercent = (value: number | string | null | undefined) => {
  const parsed = parseDecimal(value);
  return `${parsed.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}%`;
};

export const statusVariant = (status: string) => {
  const normalized = status.toLowerCase();
  if (['fechada', 'ativo', 'apurado'].includes(normalized)) return 'default';
  if (['retificada', 'parcial'].includes(normalized)) return 'secondary';
  return 'outline';
};

export const filterMemoriaCalculoItems = (
  items: MemoriaCalculoTributariaItem[],
  searchTerm: string,
) => {
  const termo = searchTerm.trim().toLowerCase();

  if (!termo) {
    return items;
  }

  return items.filter((item) =>
    [
      item.tributo_codigo,
      item.tributo_nome,
      item.etapa_calculo,
      item.fonte_dados,
      item.formula_calculo ?? '',
      item.hash_calculo ?? '',
    ].some((value) => value.toLowerCase().includes(termo)),
  );
};

export const buildReformaTributariaStats = (params: {
  totais: ReformaTributariaTotals;
  memoriaTotal: number;
}) => {
  const { totais, memoriaTotal } = params;

  const stats: ReformaTributariaStatConfig[] = [
    {
      title: 'Debitos',
      value: formatCurrency(totais.debitos),
      description: 'Total apurado no periodo',
      icon: ReceiptText,
      trend: 'neutral',
      accentClass: 'border-l-sky-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Creditos',
      value: formatCurrency(totais.creditos),
      description: 'Creditos vinculados a apuracao',
      icon: Landmark,
      trend: 'neutral',
      accentClass: 'border-l-emerald-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Saldo',
      value: formatCurrency(totais.saldo),
      description: 'Saldo apurado por tributo',
      icon: Calculator,
      trend: 'neutral',
      accentClass: 'border-l-amber-400',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Memorias',
      value: String(memoriaTotal),
      description: 'Registros de rastreabilidade',
      icon: FileText,
      trend: 'neutral',
      accentClass: 'border-l-violet-500',
      appendPreviousMonthLabel: false,
    },
  ] as const;

  return stats;
};

export const totalizarSaldoApurado = (item: ApuracaoTributariaItem) =>
  parseDecimal(item.ajustes_debito) - parseDecimal(item.ajustes_credito);
