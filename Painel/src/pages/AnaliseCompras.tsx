import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Box, Package, ShoppingCart, Truck } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useAuth } from '@/contexts/AuthContext';
import { fetchNfeDashboardCompras, parseDecimal } from '@/services/nfe';
import { fetchSpedDashboardCompras } from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';
import { Header } from '@/pages/components/Header';
import { RankingCard } from '@/pages/components/RankingCard';
import { StatCard } from '@/pages/components/StatCard';
import { EvolucaoChart } from '@/pages/components/EvolucaoChart';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

const resolvePeriodDescription = (year: number, month: string) => {
  if (month === 'all') {
    return `Acumulado em ${year}`;
  }

  const monthNumber = Number.parseInt(month, 10);
  return `${monthLabels[monthNumber - 1]} de ${year}`;
};

export default function AnaliseFiscal() {
  const { user } = useAuth();
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);

  const dashboardQuery = useQuery({
    queryKey: ['dashboard-compras', emitenteCnpj, user?.tem_sped, yearNumber, selectedMonth],
    queryFn: () =>
      user?.tem_sped
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
    if (!dashboardQuery.data?.anos_disponiveis?.length) {
      return;
    }

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
      title: `Total Comprado (${resolvePeriodDescription(yearNumber, selectedMonth)})`,
      value: formatCurrency(currentTotalComprado),
      description: formatPercent(safePercentage(currentTotalComprado, previousTotalComprado)),
      icon: ShoppingCart,
      trend: currentTotalComprado >= previousTotalComprado ? 'up' : 'down',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Documentos de Compra (Top 5 fornecedores)',
      value: currentDocCount.toString(),
      description: formatPercent(safePercentage(currentDocCount, previousDocCount)),
      icon: Truck,
      trend: currentDocCount >= previousDocCount ? 'up' : 'down',
      accentClass: 'border-l-emerald-500',
    },
    {
      title: 'Quantidade Comprada',
      value: currentItemCount.toFixed(2),
      description: formatPercent(safePercentage(currentItemCount, previousItemCount)),
      icon: Package,
      trend: currentItemCount >= previousItemCount ? 'up' : 'down',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Ticket M\\u00e9dio por Compra',
      value: formatCurrency(currentTicketMedio),
      description: formatPercent(safePercentage(currentTicketMedio, previousTicketMedio)),
      icon: Box,
      trend: currentTicketMedio >= previousTicketMedio ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ] as const;

  const comprasEvolutionData = useMemo(() => {
    const serie = dashboardQuery.data?.serie_mensal ?? [];
    const itens = selectedMonth === 'all'
      ? serie
      : serie.filter((item) => item.periodo_mes === monthNumber);

    return itens.map((item) => ({
      month: monthLabels[item.periodo_mes - 1] ?? `M\\u00eas ${item.periodo_mes}`,
      faturamento: parseDecimal(item.total_comprado),
    }));
  }, [dashboardQuery.data?.serie_mensal, monthNumber, selectedMonth]);

  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const hasChartData = comprasEvolutionData.some((item) => item.faturamento > 0);
  const chartMessage = dashboardQuery.isLoading
    ? 'Carregando dados...'
    : dashboardQuery.isError
      ? 'N\\u00e3o foi poss\\u00edvel carregar o gr\\u00e1fico.'
      : selectedMonthLabel
        ? `Nenhum dado dispon\\u00edvel para ${selectedMonthLabel} de ${selectedYear}.`
        : `Nenhum dado dispon\\u00edvel para ${selectedYear}.`;

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Compras"
        subtitle="Vis\\u00e3o anal\\u00edtica das compras"
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      {dashboardQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar an\\u00e1lise de compras</AlertTitle>
          <AlertDescription>
            {dashboardQuery.error instanceof Error
              ? dashboardQuery.error.message
              : 'N\\u00e3o foi poss\\u00edvel consultar os dados de compras no momento.'}
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
          title="Top Fornecedores"
          description="Fornecedores com maior valor de compras no per\\u00edodo"
          items={(currentData?.top_fornecedores_valor ?? []).map((row, index) => {
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
          })}
          isLoading={dashboardQuery.isLoading}
          loadingMessage="Carregando ranking de fornecedores..."
          emptyMessage="Sem dados para o per\\u00edodo selecionado."
          totalValue={formatCurrency(currentTotalComprado)}
          showAbcReport={false}
          showAbcClassification={false}
        />

        <RankingCard
          title="Top Produtos por Valor"
          description="Produtos com maior valor de compra no per\\u00edodo"
          items={(currentData?.top_produtos_valor ?? []).map((row, index) => {
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
          })}
          isLoading={dashboardQuery.isLoading}
          loadingMessage="Carregando ranking de produtos..."
          emptyMessage="Sem dados para o per\\u00edodo selecionado."
          totalValue={formatCurrency(currentTotalComprado)}
          showAbcReport={false}
          showAbcClassification={false}
        />

        <RankingCard
          title="Top Produtos por Quantidade"
          description="Produtos mais comprados no per\\u00edodo"
          items={(currentData?.top_produtos_quantidade ?? []).map((row, index) => {
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
          })}
          isLoading={dashboardQuery.isLoading}
          loadingMessage="Carregando ranking de produtos por quantidade..."
          emptyMessage="Sem dados para o per\\u00edodo selecionado."
          totalValue={formatCurrency(currentTotalComprado)}
          showAbcReport={false}
          showAbcClassification={false}
        />
      </div>

      <EvolucaoChart
        billingData={comprasEvolutionData}
        hasChartData={hasChartData}
        chartMessage={chartMessage}
        selectedMonthLabel={selectedMonthLabel}
        selectedYear={selectedYear}
        title="Evolu\\u00e7\\u00e3o das compras"
        descriptionPrefix="Compras"
        metricLabel="Compras"
      />
    </div>
  );
}
