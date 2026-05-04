import { useEffect, useMemo, useState } from 'react';
import { Box, Package, Scale, ShoppingCart, Truck } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { formatCurrency, monthLabels } from '@/services/utils';
import { Header } from '@/pages/components/Header';
import { RankingPanelGroup, RankingConfig } from '@/pages/components/RankingPanelGroup';
import { StatCard } from '@/pages/components/StatCard';
import { EvolucaoChart } from '@/pages/components/EvolucaoChart';

import { usePeriodFilter } from '@/hooks/usePeriodFilter';
import { useDashboardComprasQueries } from '@/hooks/useDashboardQueries';
import {
  formatPercent,
  hasValidEmitenteCnpj,
  parseDecimal,
  safePercentage,
  calculateChange,
} from '@/utils/formatters';

const resolvePeriodDescription = (year: number, month: string) => {
  if (month === 'all') {
    return `Acumulado em ${year}`;
  }

  const monthNumber = Number.parseInt(month, 10);
  return `${monthLabels[monthNumber - 1]} de ${year}`;
};

export default function AnaliseFiscal() {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    monthNumber,
    year,
  } = usePeriodFilter();

  const { dashboardQuery } = useDashboardComprasQueries({
    emitenteCnpj,
    email: user?.email,
    temSped: user?.tem_sped,
    year,
    selectedMonth,
    monthNumber,
    hasEmitenteCnpj,
  });

  const availableYears = dashboardQuery.data?.anos_disponiveis?.length
    ? dashboardQuery.data.anos_disponiveis
    : [year];

  useEffect(() => {
    if (!dashboardQuery.data?.anos_disponiveis?.length) return;
    if (!dashboardQuery.data.anos_disponiveis.includes(year)) {
      setSelectedYear(String(dashboardQuery.data.anos_disponiveis[0]));
    }
  }, [dashboardQuery.data?.anos_disponiveis, year, setSelectedYear]);

  const currentData = dashboardQuery.data?.resumo_atual;
  const previousData = dashboardQuery.data?.resumo_anterior;

  const currentTotalComprado = parseDecimal(currentData?.total_comprado ?? 0);
  const previousTotalComprado = parseDecimal(previousData?.total_comprado ?? 0);
  
  const currentDocCount = (currentData?.top_fornecedores_quantidade ?? []).reduce(
    (acc: number, row: any) => acc + (row.quantidade_documentos ?? 0),
    0,
  );
  const previousDocCount = (previousData?.top_fornecedores_quantidade ?? []).reduce(
    (acc: number, row: any) => acc + (row.quantidade_documentos ?? 0),
    0,
  );
  const currentItemCount = (currentData?.top_produtos_quantidade ?? []).reduce(
    (acc: number, row: any) => acc + parseDecimal(row.quantidade_total ?? 0),
    0,
  );
  const previousItemCount = (previousData?.top_produtos_quantidade ?? []).reduce(
    (acc: number, row: any) => acc + parseDecimal(row.quantidade_total ?? 0),
    0,
  );
  
  const currentTicketMedio = currentDocCount ? currentTotalComprado / currentDocCount : 0;
  const previousTicketMedio = previousDocCount ? previousTotalComprado / previousDocCount : 0;
  const reformaTaxes = parseDecimal(currentData?.total_tributos_reforma ?? 0);
  const previousReformaTaxes = parseDecimal(previousData?.total_tributos_reforma ?? 0);

  const stats = [
    {
      title: `Total Comprado (${resolvePeriodDescription(year, selectedMonth)})`,
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
    {
      title: 'Reforma Tributaria',
      value: formatCurrency(reformaTaxes),
      description: reformaTaxes > 0 ? 'IBS, CBS e IS no periodo' : 'Sem IBS/CBS/IS apurados',
      icon: Scale,
      trend: reformaTaxes >= previousReformaTaxes ? 'up' : 'down',
      accentClass: 'border-l-cyan-500',
    },
  ] as const;

  const comprasEvolutionData = useMemo(() => {
    const serie = dashboardQuery.data?.serie_mensal ?? [];
    const itens = selectedMonth === 'all'
      ? serie
      : serie.filter((item: any) => item.periodo_mes === monthNumber);

    return itens.map((item: any) => ({
      month: monthLabels[item.periodo_mes - 1] ?? `Mês ${item.periodo_mes}`,
      faturamento: parseDecimal(item.total_comprado),
    }));
  }, [dashboardQuery.data?.serie_mensal, monthNumber, selectedMonth]);

  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const hasChartData = comprasEvolutionData.some((item) => item.faturamento > 0);
  const chartMessage = dashboardQuery.isLoading
    ? 'Carregando dados...'
    : dashboardQuery.isError
      ? 'Não foi possível carregar o gráfico.'
      : selectedMonthLabel
        ? `Nenhum dado disponível para ${selectedMonthLabel} de ${selectedYear}.`
        : `Nenhum dado disponível para ${selectedYear}.`;

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Compras"
        subtitle="Visão analítica das compras"
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="flex justify-end">
        <Button asChild variant="outline">
          <Link to="/detalhamento-compras">Abrir detalhamento analítico</Link>
        </Button>
      </div>

      {dashboardQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar análise de compras</AlertTitle>
          <AlertDescription>
            {dashboardQuery.error instanceof Error
              ? dashboardQuery.error.message
              : 'Não foi possível consultar os dados de compras no momento.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />
        ))}
      </div>

      <RankingPanelGroup
        isLoading={dashboardQuery.isLoading}
        totalValue={formatCurrency(currentTotalComprado)}
        rankings={[
          {
            title: "Top Fornecedores",
            description: "Fornecedores com maior valor de compras no período",
            emptyMessage: "Sem dados para o período selecionado.",
            items: (currentData?.top_fornecedores_valor ?? []).slice(0, 5).map((row: any, index: number) => {
              const valorTotal = parseDecimal(row.valor_total);
              const percentual = safePercentage(valorTotal, currentTotalComprado);
              return {
                key: `${row.fornecedor}-${index}`,
                title: row.fornecedor,
                subtitle: `${row.quantidade_documentos} documentos`,
                value: formatCurrency(valorTotal),
                rawValue: valorTotal,
                percent: percentual,
              };
            })
          },
          {
            title: "Top Produtos por Valor",
            description: "Produtos com maior valor de compra no período",
            emptyMessage: "Sem dados para o período selecionado.",
            items: (currentData?.top_produtos_valor ?? []).slice(0, 5).map((row: any, index: number) => {
              const valorTotal = parseDecimal(row.valor_total);
              const percentual = safePercentage(valorTotal, currentTotalComprado);
              return {
                key: `${row.produto}-${index}`,
                title: row.produto,
                subtitle: `Qtd. ${parseDecimal(row.quantidade_total).toFixed(2)}`,
                value: formatCurrency(valorTotal),
                rawValue: valorTotal,
                percent: percentual,
              };
            })
          },
          {
            title: "Top Produtos por Quantidade",
            description: "Produtos mais comprados no período",
            emptyMessage: "Sem dados para o período selecionado.",
            items: (currentData?.top_produtos_quantidade ?? []).slice(0, 5).map((row: any, index: number) => {
              const quantidade = parseDecimal(row.quantidade_total);
              const percentual = safePercentage(quantidade, currentItemCount);
              const valorTotal = parseDecimal(row.valor_total);
              return {
                key: `${row.produto}-${index}-quantidade`,
                title: row.produto,
                subtitle: `${quantidade.toFixed(2)} itens comprados`,
                value: formatCurrency(valorTotal),
                rawValue: valorTotal,
                percent: percentual,
              };
            })
          }
        ]}
      />


      <EvolucaoChart
        billingData={comprasEvolutionData}
        hasChartData={hasChartData}
        chartMessage={chartMessage}
        selectedMonthLabel={selectedMonthLabel}
        selectedYear={selectedYear}
        title="Evolução das compras"
        descriptionPrefix="Compras"
        metricLabel="Compras"
      />
    </div>
  );
}
