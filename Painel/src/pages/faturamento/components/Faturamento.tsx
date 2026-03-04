import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { fetchNfeKpis, parseDecimal } from '@/services/nfe';
import { fetchSpedKpis } from '@/services/sped';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useAuth } from '@/contexts/AuthContext';

import { FaturamentoEvolucaoChart } from './FaturamentoEvolucaoChart';
import { FaturamentoHeader } from './FaturamentoHeader';
import { FaturamentoRankingCard, type RankingEntry } from './FaturamentoRankingCard';
import { FaturamentoStats } from './FaturamentoStats';
import { monthLabels } from '../utils/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

export default function Faturamento() {
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState('2025');
  
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const usaSped = Boolean(user?.tem_sped);
  
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const year = Number.parseInt(selectedYear, 10);

  const yearsQuery = useQuery({
    queryKey: ['kpis-years', usaSped ? 'sped' : 'xml', emitenteCnpj],
    queryFn: () => (usaSped
      ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
      : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const kpisQuery = useQuery({
    queryKey: ['kpis', usaSped ? 'sped' : 'xml', emitenteCnpj, year],
    queryFn: () => (usaSped
      ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year })
      : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year })),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const previousYearQuery = useQuery({
    queryKey: ['kpis', usaSped ? 'sped' : 'xml', emitenteCnpj, year - 1],
    queryFn: () => (usaSped
      ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year - 1 })
      : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year - 1 })),
    enabled: hasEmitenteCnpj && year > 2000,
    staleTime: 5 * 60 * 1000,
  });

  const billingData = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];

    const filteredResultados = selectedMonth === 'all'
      ? resultados
      : resultados.filter((item) => item.periodo_mes === monthNumber);

    return [...filteredResultados]
      .filter((item) => item.periodo_mes)
      .sort((a, b) => (a.periodo_mes ?? 0) - (b.periodo_mes ?? 0))
      .map((item, index) => {
        const monthIndex = (item.periodo_mes ?? index + 1) - 1;
        const faturamento = parseDecimal(item.kpis.total_vendas);
        return {
          month: monthLabels[monthIndex] ?? `Mês ${item.periodo_mes ?? index + 1}`,
          faturamento
        };
      });
  }, [kpisQuery.data, monthNumber, selectedMonth]);

  const rankingSource = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];

    const filteredResultados = selectedMonth === 'all'
      ? resultados
      : resultados.filter((item) => item.periodo_mes === monthNumber);

    return [...filteredResultados]
      .filter((item) => item.periodo_mes)
      .sort((a, b) => (b.periodo_mes ?? 0) - (a.periodo_mes ?? 0))[0];
  }, [kpisQuery.data, monthNumber, selectedMonth]);

  const buildRankingData = (
    items: Array<{ valor_total?: number | string; cliente?: string; produto?: string; cidade?: string }>,
    key: 'cliente' | 'produto' | 'cidade',
    fallbackLabel: string
  ): RankingEntry[] => items.map((item, index) => {
    const fullName = item[key] ?? `${fallbackLabel} ${index + 1}`;
    const name = fullName.length > 18 ? `${fullName.slice(0, 18)}…` : fullName;
    return {
      name,
      fullName,
      value: parseDecimal(item.valor_total ?? 0),
    };
  });

  const topClientesData = buildRankingData(rankingSource?.kpis.top_clientes ?? [], 'cliente', 'Cliente');
  const topProdutosData = buildRankingData(rankingSource?.kpis.top_produtos ?? [], 'produto', 'Produto');
  const topCidadesData = buildRankingData(rankingSource?.kpis.top_cidades ?? [], 'cidade', 'Cidade');

  const stats = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    const previousResultados = previousYearQuery.data?.resultados ?? [];

    const filteredResultados = selectedMonth === 'all'
      ? resultados
      : resultados.filter((item) => item.periodo_mes === monthNumber);

    const filteredPreviousResultados = selectedMonth === 'all'
      ? previousResultados
      : previousResultados.filter((item) => item.periodo_mes === monthNumber);

    const totals = filteredResultados.reduce(
      (acc, item) => {
        acc.totalSales += parseDecimal(item.kpis.total_vendas);
        acc.totalNotes += item.kpis.quantidade_notas ?? 0;
        acc.totalTaxes += parseDecimal(item.kpis.total_icms)
          + parseDecimal(item.kpis.total_ipi)
          + parseDecimal(item.kpis.total_pis)
          + parseDecimal(item.kpis.total_cofins);
        return acc;
      },
      { totalSales: 0, totalNotes: 0, totalTaxes: 0 }
    );

    const previousTotals = filteredPreviousResultados.reduce(
      (acc, item) => {
        acc.totalSales += parseDecimal(item.kpis.total_vendas);
        return acc;
      },
      { totalSales: 0 }
    );

    const ticketMedio = totals.totalNotes ? totals.totalSales / totals.totalNotes : 0;
    const percentChange = previousTotals.totalSales
      ? ((totals.totalSales - previousTotals.totalSales) / previousTotals.totalSales) * 100
      : 0;

    return {
      totalSales: totals.totalSales,
      totalNotes: totals.totalNotes,
      totalTaxes: totals.totalTaxes,
      ticketMedio,
      percentChange,
    };
  }, [kpisQuery.data, monthNumber, previousYearQuery.data, selectedMonth]);

  const yearOptions = useMemo(() => {
    const resultados = yearsQuery.data?.resultados ?? [];
    const uniqueYears = new Set<number>();

    resultados.forEach((item) => {
      if (item.periodo_ano) {
        uniqueYears.add(item.periodo_ano);
      }
    });

    return [...uniqueYears].sort((a, b) => b - a);
  }, [yearsQuery.data]);
  const availableYears = yearOptions.length ? yearOptions : [year];
  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const chartMessage = kpisQuery.isLoading
    ? 'Carregando dados...'
    : kpisQuery.isError
      ? 'Não foi possível carregar os gráficos.'
      : selectedMonthLabel
        ? `Nenhum dado disponível para ${selectedMonthLabel} de ${selectedYear}.`
        : `Nenhum dado disponível para ${selectedYear}.`;
  const hasChartData = billingData.length > 0;

  useEffect(() => {
    if (!yearOptions.length) {
      return;
    }

    if (!yearOptions.includes(year)) {
      setSelectedYear(String(yearOptions[0]));
    }
  }, [year, yearOptions]);

  return (
    <div className="space-y-6">
      <FaturamentoHeader
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      {kpisQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar os dados</AlertTitle>
          <AlertDescription>
            {kpisQuery.error instanceof Error
              ? kpisQuery.error.message
              : 'Não foi possível carregar os KPIs da API.'}
          </AlertDescription>
        </Alert>
      )}

      <FaturamentoStats
        stats={stats}
        isLoading={kpisQuery.isLoading}
        selectedMonthLabel={selectedMonthLabel}
        selectedYear={selectedYear}
        year={year}
      />

      <FaturamentoEvolucaoChart
        billingData={billingData}
        hasChartData={hasChartData}
        chartMessage={chartMessage}
        selectedMonthLabel={selectedMonthLabel}
        selectedYear={selectedYear}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <FaturamentoRankingCard
          title="Top Clientes"
          description="Ranking por faturamento no período selecionado"
          data={topClientesData}
          isLoading={kpisQuery.isLoading}
          emptyMessage="Nenhum cliente registrado."
        />
        <FaturamentoRankingCard
          title="Top Cidades"
          description="Ranking por faturamento no período selecionado"
          data={topCidadesData}
          isLoading={kpisQuery.isLoading}
          emptyMessage="Nenhuma cidade registrada."
        />
        <FaturamentoRankingCard
          title="Top Produtos"
          description="Ranking por faturamento no período selecionado"
          data={topProdutosData}
          isLoading={kpisQuery.isLoading}
          emptyMessage={chartMessage}
        />
      </div>
    </div>
  );
}
