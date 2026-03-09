import { useEffect, useMemo, useState } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import { Box, Package, ShoppingCart, Truck } from 'lucide-react';
import { Navigate } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

import { useAuth } from '@/contexts/AuthContext';

import { parseDecimal } from '@/services/nfe';
import { fetchSpedAnaliseCompras, fetchSpedKpis, type AnaliseComprasResponse } from '@/services/sped';

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

const resolvePreviousPeriod = (year: number, month: string) => {
  if (month === 'all') {
    return { periodo_ano: year - 1, periodo_mes: undefined as number | undefined };
  }

  const monthNumber = Number.parseInt(month, 10);

  if (monthNumber > 1) {
    return { periodo_ano: year, periodo_mes: monthNumber - 1 };
  }

  return { periodo_ano: year - 1, periodo_mes: 12 };
};

const calculateDocumentCount = (data?: AnaliseComprasResponse) =>
  (data?.top_fornecedores_quantidade ?? []).reduce((acc, row) => acc + (row.quantidade_documentos ?? 0), 0);

const calculateItemCount = (data?: AnaliseComprasResponse) =>
  (data?.top_produtos_quantidade ?? []).reduce((acc, row) => acc + parseDecimal(row.quantidade_total ?? 0), 0);

export default function AnaliseFiscal() {
  const { user } = useAuth();

  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);

  const yearsQuery = useQuery({
    queryKey: ['analise-years', emitenteCnpj],
    queryFn: () => fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const analiseComprasQuery = useQuery({
    queryKey: ['analise-compras', emitenteCnpj, yearNumber, selectedMonth],
    queryFn: () =>
      fetchSpedAnaliseCompras({
        emitente_cnpj: emitenteCnpj,
        periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
        periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
        limite: 5,
      }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const previousPeriod = useMemo(
    () => resolvePreviousPeriod(yearNumber, selectedMonth),
    [selectedMonth, yearNumber],
  );

  const previousAnaliseComprasQuery = useQuery({
    queryKey: ['analise-compras-previous', emitenteCnpj, previousPeriod.periodo_ano, previousPeriod.periodo_mes],
    queryFn: () =>
      fetchSpedAnaliseCompras({
        emitente_cnpj: emitenteCnpj,
        periodo_ano: previousPeriod.periodo_ano,
        periodo_mes: previousPeriod.periodo_mes,
        limite: 5,
      }),
    enabled: hasEmitenteCnpj && previousPeriod.periodo_ano > 2000,
    staleTime: 5 * 60 * 1000,
  });

  const monthlyComprasQueries = useQueries({
    queries: Array.from({ length: 12 }, (_, index) => {
      const month = index + 1;
      return {
        queryKey: ['analise-compras-mensal', emitenteCnpj, yearNumber, month],
        queryFn: () =>
          fetchSpedAnaliseCompras({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: month,
            limite: 5,
          }),
        enabled: hasEmitenteCnpj && !Number.isNaN(yearNumber),
        staleTime: 5 * 60 * 1000,
      };
    }),
  });

  const yearOptions = useMemo(() => {
    const resultados = yearsQuery.data?.resultados ?? [];
    const years = new Set<number>();

    resultados.forEach((item) => {
      if (item.periodo_ano) {
        years.add(item.periodo_ano);
      }
    });

    return [...years].sort((a, b) => b - a);
  }, [yearsQuery.data]);

  useEffect(() => {
    if (!yearOptions.length) {
      return;
    }

    const current = Number.parseInt(selectedYear, 10);
    if (!yearOptions.includes(current)) {
      setSelectedYear(String(yearOptions[0]));
    }
  }, [selectedYear, yearOptions]);

  const availableYears = yearOptions.length ? yearOptions : [yearNumber];

  const data = analiseComprasQuery.data;

  const previousData = previousAnaliseComprasQuery.data;

  const currentTotalComprado = parseDecimal(data?.total_comprado ?? 0);
  const previousTotalComprado = parseDecimal(previousData?.total_comprado ?? 0);

  const currentDocCount = calculateDocumentCount(data);
  const previousDocCount = calculateDocumentCount(previousData);

  const currentItemCount = calculateItemCount(data);
  const previousItemCount = calculateItemCount(previousData);

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
      title: 'Ticket Médio por Compra',
      value: formatCurrency(currentTicketMedio),
      description: formatPercent(safePercentage(currentTicketMedio, previousTicketMedio)),
      icon: Box,
      trend: currentTicketMedio >= previousTicketMedio ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ] as const;

  const comprasEvolutionData = useMemo(() => {
    const itens = monthlyComprasQueries
      .map((query, index) => ({
        month: index + 1,
        total: parseDecimal(query.data?.total_comprado ?? 0),
      }))
      .filter((item) => (selectedMonth === 'all' ? true : item.month === monthNumber));

    return itens.map((item) => ({
      month: monthLabels[item.month - 1] ?? `Mês ${item.month}`,
      faturamento: item.total,
    }));
  }, [monthNumber, monthlyComprasQueries, selectedMonth]);

  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const hasChartData = comprasEvolutionData.some((item) => item.faturamento > 0);
  const isMonthlyComprasLoading = monthlyComprasQueries.some((query) => query.isLoading);
  const hasMonthlyComprasError = monthlyComprasQueries.some((query) => query.isError);
  const chartMessage = isMonthlyComprasLoading
    ? 'Carregando dados...'
    : hasMonthlyComprasError
      ? 'Não foi possível carregar o gráfico.'
      : selectedMonthLabel
        ? `Nenhum dado disponível para ${selectedMonthLabel} de ${selectedYear}.`
        : `Nenhum dado disponível para ${selectedYear}.`;

  if (!user?.tem_sped) {
    return <Navigate to="/analise-vendas" replace />;
  }

  const isLoading = analiseComprasQuery.isLoading || previousAnaliseComprasQuery.isLoading;
  const hasError = analiseComprasQuery.isError || previousAnaliseComprasQuery.isError;

  return (
    <div className="space-y-6">
      <Header
        title="Análise de Compras"
        subtitle="Visão analitica das compras"
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      {hasError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar análise de compras</AlertTitle>
          <AlertDescription>
            {analiseComprasQuery.error instanceof Error
              ? analiseComprasQuery.error.message
              : previousAnaliseComprasQuery.error instanceof Error
                ? previousAnaliseComprasQuery.error.message
                : 'Não foi possível consultar os dados de compras no momento.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={isLoading} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <RankingCard
          title="Top Fornecedores"
          description="Fornecedores com maior valor de compras no período"
          items={(data?.top_fornecedores_valor ?? []).map((row, index) => {
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
          isLoading={isLoading}
          loadingMessage="Carregando ranking de fornecedores..."
          emptyMessage="Sem dados para o período selecionado."
          totalValue={formatCurrency(currentTotalComprado)}
        />

        <RankingCard
          title="Top Produtos por Valor"
          description="Produtos com maior valor de compra no período"
          items={(data?.top_produtos_valor ?? []).map((row, index) => {
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
          isLoading={isLoading}
          loadingMessage="Carregando ranking de produtos..."
          emptyMessage="Sem dados para o período selecionado."
          totalValue={formatCurrency(currentTotalComprado)}
        />

        <RankingCard
          title="Top Produtos por Quantidade"
          description="Produtos mais comprados no período"
          items={(data?.top_produtos_quantidade ?? []).map((row, index) => {
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
          isLoading={isLoading}
          loadingMessage="Carregando ranking de produtos por quantidade..."
          emptyMessage="Sem dados para o período selecionado."
          totalValue={formatCurrency(currentTotalComprado)}
        />
      </div>

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