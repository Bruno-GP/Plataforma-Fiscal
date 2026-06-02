import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Box, Package, ShoppingCart, Truck } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Header } from '@/pages/components/Header';
import { DetalhamentoComprasNotaMode } from '@/pages/components/DetalhamentoComprasNotaMode';
import { RankingPanelGroup } from '@/pages/components/RankingPanelGroup';
import { StatCard } from '@/pages/components/StatCard';
import { useAuth } from '@/contexts/AuthContext';
import { fetchNfeNotasDetalhadas } from '@/services/nfe';

import { usePeriodFilter } from '@/hooks/usePeriodFilter';
import { useDashboardComprasQueries } from '@/hooks/useDashboardQueries';
import { useFiscalYearList } from '@/hooks/useFiscalYears';
import {
  formatCurrency,
  formatPercent,
  hasValidEmitenteCnpj,
  monthLabels,
  parseDecimal,
  calculateChange,
} from '@/utils/formatters';
import { createFiscalPeriod, createFiscalQueryKey } from '@/utils/fiscalPeriod';
import {
  buildPurchaseQuantityRankingItems,
  buildPurchaseValueRankingItems,
  sumDecimalField,
  sumNumberField,
} from '@/utils/rankingUtils';

export default function DetalhamentoCompras() {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const isSped = Boolean(user?.tem_sped);
  const [openPurchaseSupplierValues, setOpenPurchaseSupplierValues] = useState<string[]>([]);
  const [openPurchaseNcmValues, setOpenPurchaseNcmValues] = useState<string[]>([]);
  const [openPurchaseProductValues, setOpenPurchaseProductValues] = useState<string[]>([]);

  const {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    monthNumber,
    year,
    faturamentoPeriodo,
  } = usePeriodFilter();
  const fiscalPeriod = useMemo(
    () => createFiscalPeriod(selectedYear, selectedMonth),
    [selectedMonth, selectedYear],
  );

  const { dashboardQuery } = useDashboardComprasQueries({
    emitenteCnpj,
    email: user?.email,
    temSped: user?.tem_sped,
    year,
    selectedMonth,
    monthNumber,
    hasEmitenteCnpj,
  });

  const notasComprasQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'detalhamento-compras-notas',
      emitenteCnpj,
      sourceKey: 'nfe',
      period: fiscalPeriod,
      extra: [user?.email],
    }),
    queryFn: () => fetchNfeNotasDetalhadas({
      emitente_cnpj: emitenteCnpj,
      email: user?.email,
      ...fiscalPeriod.params,
      tipo_operacao: 'compras',
      limite: 500,
      offset: 0,
    }),
    enabled: hasEmitenteCnpj && !isSped,
    staleTime: 5 * 60 * 1000,
  });

  const { availableYears } = useFiscalYearList({
    years: dashboardQuery.data?.anos_disponiveis,
    selectedYear,
    setSelectedYear,
    fallbackYear: year,
  });

  const currentData = dashboardQuery.data?.resumo_atual;
  const previousData = dashboardQuery.data?.resumo_anterior;
  const currentTotalComprado = parseDecimal(currentData?.total_comprado ?? 0);
  const previousTotalComprado = parseDecimal(previousData?.total_comprado ?? 0);
  const currentDocCount = sumNumberField(currentData?.top_fornecedores_quantidade ?? [], 'quantidade_documentos');
  const previousDocCount = sumNumberField(previousData?.top_fornecedores_quantidade ?? [], 'quantidade_documentos');
  const currentItemCount = sumDecimalField(currentData?.top_produtos_quantidade ?? [], 'quantidade_total');
  const previousItemCount = sumDecimalField(previousData?.top_produtos_quantidade ?? [], 'quantidade_total');
  const currentTicketMedio = currentDocCount ? currentTotalComprado / currentDocCount : 0;
  const previousTicketMedio = previousDocCount ? previousTotalComprado / previousDocCount : 0;

  const stats = [
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
      title: 'Ticket Médio por Compra',
      value: formatCurrency(currentTicketMedio),
      description: formatPercent(calculateChange(currentTicketMedio, previousTicketMedio)),
      icon: Box,
      trend: currentTicketMedio >= previousTicketMedio ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ] as const;

  const purchasePanels = useMemo(
    () => [
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
      },
    ],
    [currentData, currentItemCount, currentTotalComprado],
  );

  const hasDetalhamentoCompras = purchasePanels.some((panel) => panel.items.length > 0);
  const notasCompras = notasComprasQuery.data?.notas ?? [];

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Detalhamento de compras"
        subtitle="Expansao hierarquica focada somente nas compras, com leitura em camadas ate o nivel de produto."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="stat-card-grid">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />
        ))}
      </div>

      <Card className="border border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]">
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <Badge className="border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">
                Drill-down hierarquico
              </Badge>
              <h2 className="text-2xl font-semibold tracking-tight">Expansao em 4 niveis</h2>
              <p className="max-w-3xl text-sm text-slate-300">
                Esta tela usa exatamente os dados disponiveis no painel de compras. Quando um nivel nao existe nessa
                fonte, ele nao e exibido aqui.
              </p>
            </div>
            <Button asChild variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100">
              <Link to="/analise-compras">
                Voltar ao dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {isSped && (
        <Alert>
          <AlertTitle>Detalhamento por nota ainda nao disponivel para SPED</AlertTitle>
          <AlertDescription>
            Esta versao foi conectada a estrutura detalhada de NFe/XML. Se voce quiser, eu posso preparar a mesma
            experiencia para SPED no proximo passo.
          </AlertDescription>
        </Alert>
      )}

      {!isSped && notasComprasQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar notas de compra</AlertTitle>
          <AlertDescription>
            {notasComprasQuery.error instanceof Error
              ? notasComprasQuery.error.message
              : 'Nao foi possivel consultar as notas detalhadas de compra deste periodo.'}
          </AlertDescription>
        </Alert>
      )}

      {dashboardQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar detalhamento de compras</AlertTitle>
          <AlertDescription>
            {dashboardQuery.error instanceof Error
              ? dashboardQuery.error.message
              : 'Nao foi possivel consultar os dados detalhados de compras deste periodo.'}
          </AlertDescription>
        </Alert>
      )}

      {!dashboardQuery.isLoading && !dashboardQuery.isError && !hasDetalhamentoCompras && (
        <Alert>
          <AlertTitle>Detalhamento indisponivel para compras neste periodo</AlertTitle>
          <AlertDescription>
            Nao existem visoes detalhadas de compras disponiveis na fonte atual para o recorte selecionado.
          </AlertDescription>
        </Alert>
      )}

      {hasDetalhamentoCompras && (
        <RankingPanelGroup
          rankings={purchasePanels.map(p => ({
            ...p,
            emptyMessage: "Sem dados para o periodo selecionado.",
          }))}
          isLoading={dashboardQuery.isLoading}
          totalValue={formatCurrency(currentTotalComprado)}
        />
      )}

      {!isSped && (
        <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
          <CardContent className="p-0">
            <div className="border-b border-slate-800/80 px-6 py-4">
              <div className="flex flex-col gap-2">
                <Badge className="w-fit border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">
                  Tributos por item
                </Badge>
                <h2 className="text-xl font-semibold tracking-tight">Compras por fornecedor, NCM e produto</h2>
                <p className="max-w-3xl text-sm text-slate-300">
                  A grade usa os tributos complementares sincronizados por item quando existem; caso contrario, mantem
                  a leitura proporcional dos tributos legados da nota.
                </p>
              </div>
            </div>

            {notasComprasQuery.isLoading ? (
              <div className="p-6 text-sm text-slate-300">Carregando notas detalhadas de compra...</div>
            ) : notasCompras.length > 0 ? (
              <DetalhamentoComprasNotaMode
                notas={notasCompras}
                openNoteValues={openPurchaseSupplierValues}
                onOpenNoteValuesChange={setOpenPurchaseSupplierValues}
                openSupplierValues={openPurchaseNcmValues}
                onOpenSupplierValuesChange={setOpenPurchaseNcmValues}
                openNcmValues={openPurchaseProductValues}
                onOpenNcmValuesChange={setOpenPurchaseProductValues}
              />
            ) : (
              <div className="p-6 text-sm text-slate-300">
                Nenhuma nota detalhada de compra encontrada para o periodo selecionado.
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
