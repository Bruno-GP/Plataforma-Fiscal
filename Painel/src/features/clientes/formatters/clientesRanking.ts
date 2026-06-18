import { formatCurrency } from '@/utils/formatters';

import type { ClienteComRisco, ClienteRankingItem } from '../types';

export const buildTopClientesItems = (
  clientes: ClienteComRisco[],
): ClienteRankingItem[] =>
  clientes.map((cliente, index) => ({
    key: `${cliente.cliente}-${index}`,
    title: cliente.cliente,
    subtitle:
      cliente.percentual !== null
        ? `${cliente.percentual.toFixed(1)}% do faturamento`
        : 'Participacao nao informada',
    value: formatCurrency(cliente.valorTotal),
    rawValue: cliente.valorTotal,
    percent: cliente.percentual,
    badgeLabel: cliente.temRisco ? 'Com risco de perda' : 'Sem risco de perda',
    badgeClassName: cliente.temRisco
      ? 'border-rose-500/40 bg-rose-500/15 text-rose-300'
      : 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300',
  }));
