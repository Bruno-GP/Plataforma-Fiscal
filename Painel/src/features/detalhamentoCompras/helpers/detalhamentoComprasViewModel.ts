import { Box, Package, ShoppingCart, Truck } from 'lucide-react';

import {
  calculateChange,
  formatCurrency,
  formatPercent,
  parseDecimal,
} from '@/utils/formatters';
import {
  buildPurchaseQuantityRankingItems,
  buildPurchaseValueRankingItems,
  sumDecimalField,
  sumNumberField,
} from '@/utils/rankingUtils';

import type { AnaliseComprasResponse } from '@/services/nfe';

import type {
  DetalhamentoComprasRankingPanel,
  DetalhamentoComprasStatConfig,
} from '../types';

export const buildDetalhamentoComprasStats = (params: {
  currentData?: AnaliseComprasResponse;
  previousData?: AnaliseComprasResponse;
}) => {
  const { currentData, previousData } = params;

  const currentTotalComprado = parseDecimal(currentData?.total_comprado ?? 0);
  const previousTotalComprado = parseDecimal(previousData?.total_comprado ?? 0);
  const currentDocCount = sumNumberField(currentData?.top_fornecedores_quantidade ?? [], 'quantidade_documentos');
  const previousDocCount = sumNumberField(previousData?.top_fornecedores_quantidade ?? [], 'quantidade_documentos');
  const currentItemCount = sumDecimalField(currentData?.top_produtos_quantidade ?? [], 'quantidade_total');
  const previousItemCount = sumDecimalField(previousData?.top_produtos_quantidade ?? [], 'quantidade_total');
  const currentTicketMedio = currentDocCount ? currentTotalComprado / currentDocCount : 0;
  const previousTicketMedio = previousDocCount ? previousTotalComprado / previousDocCount : 0;

  const stats: DetalhamentoComprasStatConfig[] = [
    {
      title: 'Total Comprado',
      value: formatCurrency(currentTotalComprado),
      description: formatPercent(calculateChange(currentTotalComprado, previousTotalComprado)),
      icon: ShoppingCart,
      trend: currentTotalComprado >= previousTotalComprado ? 'up' : 'down',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Documentos de Compra (Top 5 fornecedores)',
      value: currentDocCount.toString(),
      description: formatPercent(calculateChange(currentDocCount, previousDocCount)),
      icon: Truck,
      trend: currentDocCount >= previousDocCount ? 'up' : 'down',
      accentClass: 'border-l-emerald-500',
    },
    {
      title: 'Quantidade Comprada',
      value: currentItemCount.toFixed(2),
      description: formatPercent(calculateChange(currentItemCount, previousItemCount)),
      icon: Package,
      trend: currentItemCount >= previousItemCount ? 'up' : 'down',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Ticket MÃ©dio por Compra',
      value: formatCurrency(currentTicketMedio),
      description: formatPercent(calculateChange(currentTicketMedio, previousTicketMedio)),
      icon: Box,
      trend: currentTicketMedio >= previousTicketMedio ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ];

  return {
    stats,
    currentTotalComprado,
    currentItemCount,
    previousTotalComprado,
    previousDocCount,
    previousItemCount,
    previousTicketMedio,
    currentDocCount,
    currentTicketMedio,
  };
};

export const buildDetalhamentoComprasPurchasePanels = (params: {
  currentData?: AnaliseComprasResponse;
  currentTotalComprado: number;
  currentItemCount: number;
}) => {
  const { currentData, currentTotalComprado, currentItemCount } = params;

  const purchasePanels: DetalhamentoComprasRankingPanel[] = [
    {
      title: 'Top Fornecedores',
      description: 'Fornecedores com maior valor de compras no periodo',
      items: buildPurchaseValueRankingItems(currentData?.top_fornecedores_valor ?? [], {
        titleField: 'fornecedor',
        fallbackTitle: 'Fornecedor nao identificado',
        totalValue: currentTotalComprado,
        subtitle: (row) => `${row.quantidade_documentos} documentos`,
        limit: Number.POSITIVE_INFINITY,
      }),
      loadingMessage: 'Carregando ranking de fornecedores...',
      emptyMessage: 'Sem dados para o periodo selecionado.',
    },
    {
      title: 'Top Produtos por Valor',
      description: 'Produtos com maior valor de compra no periodo',
      items: buildPurchaseValueRankingItems(currentData?.top_produtos_valor ?? [], {
        titleField: 'produto',
        fallbackTitle: 'Produto nao identificado',
        totalValue: currentTotalComprado,
        subtitle: (row) => `Qtd. ${parseDecimal(row.quantidade_total).toFixed(2)}`,
        limit: Number.POSITIVE_INFINITY,
      }),
      loadingMessage: 'Carregando ranking de produtos...',
      emptyMessage: 'Sem dados para o periodo selecionado.',
    },
    {
      title: 'Top Produtos por Quantidade',
      description: 'Produtos mais comprados no periodo',
      items: buildPurchaseQuantityRankingItems(
        currentData?.top_produtos_quantidade ?? [],
        currentItemCount,
        Number.POSITIVE_INFINITY,
      ),
      loadingMessage: 'Carregando ranking de produtos por quantidade...',
      emptyMessage: 'Sem dados para o periodo selecionado.',
    },
  ];

  return purchasePanels;
};

export const buildDetalhamentoComprasViewModel = (params: {
  currentData?: AnaliseComprasResponse;
  previousData?: AnaliseComprasResponse;
}) => {
  const { currentData, previousData } = params;
  const statsViewModel = buildDetalhamentoComprasStats({ currentData, previousData });
  const purchasePanels = buildDetalhamentoComprasPurchasePanels({
    currentData,
    currentTotalComprado: statsViewModel.currentTotalComprado,
    currentItemCount: statsViewModel.currentItemCount,
  });

  return {
    stats: statsViewModel.stats,
    purchasePanels,
    currentTotalComprado: statsViewModel.currentTotalComprado,
    currentItemCount: statsViewModel.currentItemCount,
    hasDetalhamentoCompras: purchasePanels.some((panel) => panel.items.length > 0),
    rankingTotalValue: formatCurrency(statsViewModel.currentTotalComprado),
  };
};
