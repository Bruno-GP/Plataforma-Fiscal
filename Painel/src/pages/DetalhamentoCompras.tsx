import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Box, Package, ShoppingCart, Truck } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useAuth } from '@/contexts/AuthContext';
import { Header } from '@/pages/components/Header';
import { RankingCard } from '@/pages/components/RankingCard';
import { StatCard } from '@/pages/components/StatCard';
import {
  fetchNfeDashboardCompras,
  parseDecimal,
} from '@/services/nfe';
import { fetchSpedDashboardCompras } from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

export default function DetalhamentoCompras() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);
  const isSped = Boolean(user?.tem_sped);

  const dashboardQuery = useQuery({
    queryKey: ['detalhamento-compras-dashboard', emitenteCnpj, isSped, yearNumber, selectedMonth],
    queryFn: () =>
      isSped
        ? fetchSpedDashboardCompras({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          })
        : fetchNfeDashboardCompras({
            emitente_cnpj: emitenteCnpj,
            email: user?.email,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const availableYears = dashboardQuery.data?.anos_disponiveis?.length
    ? dashboardQuery.data.anos_disponiveis
    : [yearNumber];

  useEffect(() => {
    if (!dashboardQuery.data?.anos_disponiveis?.length) return;
    if (!dashboardQuery.data.anos_disponiveis.includes(yearNumber)) {
      setSelectedYear(String(dashboardQuery.data.anos_disponiveis[0]));
    }
  }, [dashboardQuery.data?.anos_disponiveis, yearNumber]);

  const currentData = dashboardQuery.data?.resumo_atual;
  const previousData = dashboardQuery.data?.resumo_anterior;
  const currentTotalComprado = parseDecimal(currentData?.total_comprado ?? 0);
  const previousTotalComprado = parseDecimal(previousData?.total_comprado ?? 0);
  const currentDocCount = (currentData?.top_fornecedores_quantidade ?? []).reduce(
    (acc, row) => acc + (row.quantidade_documentos ?? 0),
    0,
  );
  const previousDocCount = (previousData?.top_fornecedores_quantidade ?? []).reduce(
    (acc, row) => acc + (row.quantidade_documentos ?? 0),
    0,
  );
  const currentItemCount = (currentData?.top_produtos_quantidade ?? []).reduce(
    (acc, row) => acc + parseDecimal(row.quantidade_total ?? 0),
    0,
  );
  const previousItemCount = (previousData?.top_produtos_quantidade ?? []).reduce(
    (acc, row) => acc + parseDecimal(row.quantidade_total ?? 0),
    0,
  );
  const currentTicketMedio = currentDocCount ? currentTotalComprado / currentDocCount : 0;
  const previousTicketMedio = previousDocCount ? previousTotalComprado / previousDocCount : 0;

  const safePercentage = (current: number, previous: number) =>
    previous ? ((current - previous) / previous) * 100 : 0;

  const stats = [
    {
      title: 'Total Comprado',
      value: formatCurrency(currentTotalComprado),
      description: `${safePercentage(currentTotalComprado, previousTotalComprado) >= 0 ? '+' : ''}${safePercentage(currentTotalComprado, previousTotalComprado).toFixed(1)}%`,
      icon: ShoppingCart,
      trend: currentTotalComprado >= previousTotalComprado ? 'up' : 'down',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Documentos de Compra (Top 5 fornecedores)',
      value: currentDocCount.toString(),
      description: `${safePercentage(currentDocCount, previousDocCount) >= 0 ? '+' : ''}${safePercentage(currentDocCount, previousDocCount).toFixed(1)}%`,
      icon: Truck,
      trend: currentDocCount >= previousDocCount ? 'up' : 'down',
      accentClass: 'border-l-emerald-500',
    },
    {
      title: 'Quantidade Comprada',
      value: currentItemCount.toFixed(2),
      description: `${safePercentage(currentItemCount, previousItemCount) >= 0 ? '+' : ''}${safePercentage(currentItemCount, previousItemCount).toFixed(1)}%`,
      icon: Package,
      trend: currentItemCount >= previousItemCount ? 'up' : 'down',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Ticket Medio por Compra',
      value: formatCurrency(currentTicketMedio),
      description: `${safePercentage(currentTicketMedio, previousTicketMedio) >= 0 ? '+' : ''}${safePercentage(currentTicketMedio, previousTicketMedio).toFixed(1)}%`,
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
        items: (currentData?.top_fornecedores_valor ?? []).map((row, index) => {
          const valorTotal = parseDecimal(row.valor_total);
          const percentual = currentTotalComprado ? (valorTotal / currentTotalComprado) * 100 : null;

          return {
            key: `${row.fornecedor}-${index}`,
            title: row.fornecedor,
            subtitle: `${row.quantidade_documentos} documentos`,
            value: formatCurrency(valorTotal),
            rawValue: valorTotal,
            percent: percentual,
          };
        }),
        loadingMessage: 'Carregando ranking de fornecedores...',
      },
      {
        title: 'Top Produtos por Valor',
        description: 'Produtos com maior valor de compra no periodo',
        items: (currentData?.top_produtos_valor ?? []).map((row, index) => {
          const valorTotal = parseDecimal(row.valor_total);
          const percentual = currentTotalComprado ? (valorTotal / currentTotalComprado) * 100 : null;

          return {
            key: `${row.produto}-${index}`,
            title: row.produto,
            subtitle: `Qtd. ${parseDecimal(row.quantidade_total).toFixed(2)}`,
            value: formatCurrency(valorTotal),
            rawValue: valorTotal,
            percent: percentual,
          };
        }),
        loadingMessage: 'Carregando ranking de produtos...',
      },
      {
        title: 'Top Produtos por Quantidade',
        description: 'Produtos mais comprados no periodo',
        items: (currentData?.top_produtos_quantidade ?? []).map((row, index) => {
          const quantidade = parseDecimal(row.quantidade_total);
          const percentual = currentItemCount ? (quantidade / currentItemCount) * 100 : null;
          const valorTotal = parseDecimal(row.valor_total);

          return {
            key: `${row.produto}-${index}-quantidade`,
            title: row.produto,
            subtitle: `${quantidade.toFixed(2)} itens comprados`,
            value: formatCurrency(valorTotal),
            rawValue: valorTotal,
            percent: percentual,
          };
        }),
        loadingMessage: 'Carregando ranking de produtos por quantidade...',
      },
    ],
    [currentData, currentItemCount, currentTotalComprado],
  );

  const hasDetalhamentoCompras = purchasePanels.some((panel) => panel.items.length > 0);

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

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
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
        <div className="grid gap-6 lg:grid-cols-3">
          {purchasePanels.map((panel) => (
            <RankingCard
              key={panel.title}
              title={panel.title}
              description={panel.description}
              items={panel.items}
              isLoading={dashboardQuery.isLoading}
              loadingMessage={panel.loadingMessage}
              emptyMessage="Sem dados para o periodo selecionado."
              totalValue={formatCurrency(currentTotalComprado)}
              showAbcReport={false}
              showAbcClassification={false}
            />
          ))}
        </div>
      )}
    </div>
  );
}
