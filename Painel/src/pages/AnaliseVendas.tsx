import { useEffect, useMemo, useState } from 'react';
import { TrendingDown, TrendingUp, Users, Percent } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Header } from './components/Header';
import { RankingCard } from './components/RankingCard';
import { StatCard } from './components/StatCard';
import { SalesRegionCityMap } from './components/SalesRegionCityMap';
import { EvolucaoChart } from './components/EvolucaoChart';
import { fetchNfeDashboardVendas, parseDecimal } from '@/services/nfe';
import { useAuth } from '@/contexts/AuthContext';
import { fetchSpedDashboardVendas } from '@/services/sped';
import { monthLabels } from '../services/utils';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);

const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

interface DashboardProps {
  title?: string;
  subtitle?: string;
}

export default function Dashboard({
  title = 'Vendas',
  subtitle = 'Visão geral do seu negócio',
}: DashboardProps) {
  const { user } = useAuth();

  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const year = Number.parseInt(selectedYear, 10);

  const dashboardQuery = useQuery({
    queryKey: ['dashboard-vendas', emitenteCnpj, user?.tem_sped, year, selectedMonth],
    queryFn: () =>
      user?.tem_sped
        ? fetchSpedDashboardVendas({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          })
        : fetchNfeDashboardVendas({
            emitente_cnpj: emitenteCnpj,
            email: user?.email,
            periodo_ano: Number.isNaN(year) ? undefined : year,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const availableYears = dashboardQuery.data?.anos_disponiveis?.length
    ? dashboardQuery.data.anos_disponiveis
    : [year];

  useEffect(() => {
    if (!dashboardQuery.data?.anos_disponiveis?.length) {
      return;
    }

    if (!dashboardQuery.data.anos_disponiveis.includes(year)) {
      setSelectedYear(String(dashboardQuery.data.anos_disponiveis[0]));
    }
  }, [dashboardQuery.data?.anos_disponiveis, year]);

  const currentData = dashboardQuery.data?.resumo_atual;
  const previousData = dashboardQuery.data?.resumo_anterior;
  const totalFaturamento = parseDecimal(currentData?.total_vendido ?? 0);

  const totalSalesChange = parseDecimal(previousData?.total_vendido ?? 0)
    ? ((totalFaturamento - parseDecimal(previousData?.total_vendido ?? 0)) / parseDecimal(previousData?.total_vendido ?? 0)) * 100
    : 0;
  const ticketChange = parseDecimal(previousData?.ticket_medio ?? 0)
    ? ((parseDecimal(currentData?.ticket_medio ?? 0) - parseDecimal(previousData?.ticket_medio ?? 0)) / parseDecimal(previousData?.ticket_medio ?? 0)) * 100
    : 0;
  const totalTaxesChange = parseDecimal(previousData?.total_impostos ?? 0)
    ? ((parseDecimal(currentData?.total_impostos ?? 0) - parseDecimal(previousData?.total_impostos ?? 0)) / parseDecimal(previousData?.total_impostos ?? 0)) * 100
    : 0;

  const faturamentoPeriodo = useMemo(() => {
    if (selectedMonth === 'all') {
      return selectedYear;
    }
    return `${String(monthNumber).padStart(2, '0')}/${selectedYear}`;
  }, [monthNumber, selectedMonth, selectedYear]);

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
      value: `${totalSalesChange >= 0 ? '+' : ''}${totalSalesChange.toFixed(1)}%`,
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
      : serie.filter((item) => item.periodo_mes === monthNumber);

    return itens.map((item) => ({
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

  const resolvePercentual = (valorTotal?: number | string) => {
    const valor = parseDecimal(valorTotal ?? 0);
    if (!totalFaturamento || !valor) {
      return null;
    }
    return (valor / totalFaturamento) * 100;
  };

  const topClientesItems = (currentData?.top_clientes ?? []).map((cliente, index) => {
    const percentual = resolvePercentual(cliente.valor_total);
    const valorTotal = parseDecimal(cliente.valor_total ?? 0);

    return {
      key: `${cliente.cliente}-${index}`,
      title: cliente.cliente ?? 'Cliente não identificado',
      subtitle:
        percentual !== null
          ? `${percentual.toFixed(1)}% do faturamento`
        : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const topProdutosItems = (currentData?.top_produtos ?? []).map((produto, index) => {
    const percentual = resolvePercentual(produto.valor_total);
    const valorTotal = parseDecimal(produto.valor_total ?? 0);

    return {
      key: `${produto.produto}-${index}`,
      title: produto.produto ?? 'Produto não identificado',
      subtitle:
        percentual !== null
          ? `${percentual.toFixed(1)}% do faturamento`
        : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const topCidadesItems = (currentData?.top_cidades ?? []).map((cidade, index) => {
    const percentual = resolvePercentual(cidade.valor_total);
    const valorTotal = parseDecimal(cidade.valor_total ?? 0);

    return {
      key: `${cidade.cidade}-${index}`,
      title: cidade.cidade ?? 'Cidade não identificada',
      subtitle:
        percentual !== null
          ? `${percentual.toFixed(1)}% do faturamento`
        : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

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

      {dashboardQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar indicadores</AlertTitle>
          <AlertDescription>
            {dashboardQuery.error instanceof Error
              ? dashboardQuery.error.message
            : 'Não foi possível buscar os KPIs mais recentes na API.'}
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
          description="Clientes com maior faturamento no último período"
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
          description="Itens com maior faturamento no último período"
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
          description="Cidades com maior faturamento no último período"
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
        topCidadesItems={topCidadesItems}
        totalFaturamento={totalFaturamento}
        formatCurrency={formatCurrency}
      />
    </div>
  );
}
