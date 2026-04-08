import { useEffect, useMemo, useState } from 'react';
import { TrendingDown, TrendingUp, Users, Percent } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Header } from './components/Header';
import { RankingCard } from './components/RankingCard';
import { StatCard } from './components/StatCard';
import { SalesRegionCityMap } from './components/SalesRegionCityMap';
import { EvolucaoChart } from './components/EvolucaoChart';

import { useAuth } from '@/contexts/AuthContext';
import { monthLabels } from '../services/utils';
import { usePeriodFilter } from '@/hooks/usePeriodFilter';
import { useDashboardVendasQueries } from '@/hooks/useDashboardQueries';
import {
  formatCurrency,
  formatPercent,
  hasValidEmitenteCnpj,
  parseDecimal,
  safePercentage,
  calculateChange,
} from '@/utils/formatters';

interface DashboardProps {
  title?: string;
  subtitle?: string;
}

export default function Dashboard({
  title = 'Vendas',
  subtitle = 'Visão geral do seu negócio',
}: DashboardProps) {
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
    faturamentoPeriodo,
  } = usePeriodFilter();

  const { dashboardQuery, mapQuery } = useDashboardVendasQueries({
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
  const totalFaturamento = parseDecimal(mapQuery.data?.total_vendido ?? currentData?.total_vendido ?? 0);

  const totalSalesChange = calculateChange(totalFaturamento, previousData?.total_vendido ?? 0);
  const ticketChange = calculateChange(currentData?.ticket_medio ?? 0, previousData?.ticket_medio ?? 0);
  const totalTaxesChange = calculateChange(currentData?.total_impostos ?? 0, previousData?.total_impostos ?? 0);

  const stats = [
    {
      title: `Faturamento Mensal${faturamentoPeriodo ? ` (Período ${faturamentoPeriodo})` : ''}`,
      value: formatCurrency(totalFaturamento),
      description: formatPercent(totalSalesChange),
      icon: TrendingUp,
      trend: totalSalesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Comparativo anual',
      value: formatPercent(totalSalesChange),
      description: selectedMonth === 'all'
        ? `vs. mesmo período de ${year - 1}`
        : 'vs. período anterior',
      icon: totalSalesChange >= 0 ? TrendingUp : TrendingDown,
      trend: totalSalesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-emerald-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Ticket Médio',
      value: formatCurrency(parseDecimal(currentData?.ticket_medio ?? 0)),
      description: formatPercent(ticketChange),
      icon: Users,
      trend: ticketChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Impostos sobre vendas',
      value: formatCurrency(parseDecimal(currentData?.total_impostos ?? 0)),
      description: formatPercent(totalTaxesChange),
      icon: Percent,
      trend: totalTaxesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ];

  const salesEvolutionData = useMemo(() => {
    const serie = dashboardQuery.data?.serie_mensal ?? [];
    const itens = selectedMonth === 'all'
      ? serie
      : serie.filter((item: any) => item.periodo_mes === monthNumber);

    return itens.map((item: any) => ({
      month: monthLabels[item.periodo_mes - 1] ?? `Mês ${item.periodo_mes}`,
      faturamento: parseDecimal(item.total_vendido ?? 0),
    }));
  }, [dashboardQuery.data?.serie_mensal, monthNumber, selectedMonth]);

  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const chartMessage = dashboardQuery.isLoading
    ? 'Carregando dados...'
    : dashboardQuery.isError
      ? 'Não foi possível carregar o gráfico.'
      : selectedMonthLabel
        ? `Nenhum dado disponível para ${selectedMonthLabel} de ${selectedYear}.`
        : `Nenhum dado disponível para ${selectedYear}.`;
  const hasChartData = salesEvolutionData.length > 0;

  const resolvePercentual = (valorTotal?: number | string) => safePercentage(valorTotal || 0, totalFaturamento);

  const topClientesBase = mapQuery.data?.top_clientes_valor?.length
    ? mapQuery.data.top_clientes_valor
    : currentData?.top_clientes ?? [];

  const topClientesItems = topClientesBase.slice(0, 5).map((cliente: any, index: number) => {
    const percentual = resolvePercentual(cliente.valor_total);
    const valorTotal = parseDecimal(cliente.valor_total ?? 0);
    return {
      key: `${cliente.cliente}-${index}`,
      title: cliente.cliente ?? 'Cliente não identificado',
      subtitle: percentual !== null ? `${percentual.toFixed(1)}% do faturamento` : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const topProdutosBase = mapQuery.data?.top_produtos_valor?.length
    ? mapQuery.data.top_produtos_valor
    : currentData?.top_produtos ?? [];

  const topProdutosItems = topProdutosBase.slice(0, 5).map((produto: any, index: number) => {
    const percentual = resolvePercentual(produto.valor_total);
    const valorTotal = parseDecimal(produto.valor_total ?? 0);
    return {
      key: `${produto.produto}-${index}`,
      title: produto.produto ?? 'Produto não identificado',
      subtitle: percentual !== null ? `${percentual.toFixed(1)}% do faturamento` : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const topCidadesBase = mapQuery.data?.top_cidades_valor?.length
    ? mapQuery.data.top_cidades_valor
    : currentData?.top_cidades ?? [];

  const topCidadesItems = topCidadesBase.slice(0, 5).map((cidade: any, index: number) => {
    const percentual = resolvePercentual(cidade.valor_total);
    const valorTotal = parseDecimal(cidade.valor_total ?? 0);
    return {
      key: `${cidade.cidade}-${'uf' in cidade ? cidade.uf ?? 'sem-uf' : 'sem-uf'}-${index}`,
      title: cidade.cidade ?? 'Cidade não identificada',
      subtitle: percentual !== null ? `${percentual.toFixed(1)}% do faturamento` : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const mapTopCidadesItems = (mapQuery.data?.top_cidades_valor ?? []).map((cidade: any, index: number) => {
    const valorTotal = parseDecimal(cidade.valor_total ?? 0);
    const percentual = resolvePercentual(valorTotal);
    const cidadeComUf = cidade.uf?.trim()
      ? `${cidade.cidade ?? 'Cidade não identificada'} - ${cidade.uf.trim().toUpperCase()}`
      : cidade.cidade ?? 'Cidade não identificada';
    return {
      key: `${cidade.cidade}-${cidade.uf ?? 'sem-uf'}-${index}`,
      title: cidadeComUf,
      subtitle: percentual !== null ? `${percentual.toFixed(1)}% do faturamento` : 'Participção não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const mapTopRegioesItems = (mapQuery.data?.top_regioes_valor ?? []).map((regiao: any) => ({
    regiao: regiao.regiao,
    rawValue: parseDecimal(regiao.valor_total ?? 0),
  }));

  return (
    <div className="space-y-6 py-6">
      <Header
        title={title}
        subtitle={subtitle}
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="flex justify-end">
        <Button asChild variant="outline">
          <Link to="/detalhamento-vendas">Abrir detalhamento analítico</Link>
        </Button>
      </div>

      {dashboardQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar indicadores</AlertTitle>
          <AlertDescription>
            {dashboardQuery.error instanceof Error ? dashboardQuery.error.message : 'Não foi possível buscar KPIs.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <RankingCard
          title="Top Clientes"
          description="Clientes com maior faturamento"
          items={topClientesItems}
          isLoading={dashboardQuery.isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum cliente registrado."
          totalValue={formatCurrency(totalFaturamento)}
          showAbcReport={false}
          showAbcClassification={false}
        />
        <RankingCard
          title="Top Produtos"
          description="Itens com maior faturamento"
          items={topProdutosItems}
          isLoading={dashboardQuery.isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum produto registrado."
          totalValue={formatCurrency(totalFaturamento)}
          showAbcReport={false}
          showAbcClassification={false}
        />
        <RankingCard
          title="Top Cidades"
          description="Cidades com maior faturamento"
          items={topCidadesItems}
          isLoading={dashboardQuery.isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhuma cidade registrada."
          totalValue={formatCurrency(totalFaturamento)}
          showAbcReport={false}
          showAbcClassification={false}
        />
      </div>

      <EvolucaoChart
        billingData={salesEvolutionData}
        hasChartData={hasChartData}
        chartMessage={chartMessage}
        selectedMonthLabel={selectedMonthLabel}
        selectedYear={selectedYear}
        title="Evolução das Vendas"
        descriptionPrefix="Vendas"
        metricLabel="Vendas"
      />

      <SalesRegionCityMap
        topCidadesItems={mapTopCidadesItems.length ? mapTopCidadesItems : topCidadesItems}
        topRegioesItems={mapTopRegioesItems}
        totalFaturamento={totalFaturamento}
        formatCurrency={formatCurrency}
      />
    </div>
  );
}
