import { useEffect, useMemo, useState } from 'react';
import { TrendingDown, TrendingUp, Users, Percent  } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

import { Header } from './components/Header';
import { RankingCard } from './components/RankingCard';
import { StatCard } from './components/StatCard';
import { SalesRegionCityMap } from './components/SalesRegionCityMap';
import { EvolucaoChart } from './components/EvolucaoChart';

import { fetchNfeKpis, fetchNfeKpisComparativoAtual, parseDecimal } from '@/services/nfe';
import { useAuth } from '@/contexts/AuthContext'
import { fetchSpedKpis } from '@/services/sped';
// import { useChat } from '@/contexts/ChatContext';
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
  title = 'Dashboard', 
  subtitle = 'Visão geral do seu negócio' 
}: DashboardProps) {
  const { user } = useAuth();
  // const { toggleChat, sendMessage, isOpen } = useChat();

  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const usaSped = Boolean(user?.tem_sped);

  const monthNumber = Number.parseInt(selectedMonth, 10);
  const year = Number.parseInt(selectedYear, 10);

  const yearsQuery = useQuery({
    queryKey: ['kpis-years', usaSped ? 'sped' : 'xml', emitenteCnpj],
    queryFn: () => (usaSped ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }) : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const kpisQuery = useQuery({
    queryKey: ['kpis', usaSped ? 'sped' : 'xml', emitenteCnpj, year],
    queryFn: () => (usaSped ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year }) : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year })),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const previousYearQuery = useQuery({
    queryKey: ['kpis', usaSped ? 'sped' : 'xml', emitenteCnpj, year - 1],
    queryFn: () => (usaSped ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year - 1 }) : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year - 1 })),
    enabled: hasEmitenteCnpj && year > 2000,
    staleTime: 5 * 60 * 1000,
  });

  const isAllMonths = selectedMonth === 'all';

  const filteredResultados = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    if (isAllMonths) {
      return resultados;
    }
    return resultados.filter((item) => item.periodo_mes === monthNumber);
  }, [isAllMonths, kpisQuery.data, monthNumber]);

  const aggregatedData = useMemo(() => {
    const totals = {
      totalSales: 0,
      totalNotes: 0,
      totalTaxes: 0,
    };
    const topClientesMap = new Map<string, number>();
    const topProdutosMap = new Map<string, number>();
    const topCidadesMap = new Map<string, number>();

    filteredResultados.forEach((item) => {
      const kpis = item.kpis;
      totals.totalSales += parseDecimal(kpis.total_vendas ?? 0);
      totals.totalNotes += kpis.quantidade_notas ?? 0;
      totals.totalTaxes += parseDecimal(kpis.total_icms ?? 0)
        + parseDecimal(kpis.total_ipi ?? 0)
        + parseDecimal(kpis.total_pis ?? 0)
        + parseDecimal(kpis.total_cofins ?? 0);

      (kpis.top_clientes ?? []).forEach((cliente, index) => {
        const nome = cliente.cliente ?? `Cliente não identificado ${index + 1}`;
        const atual = topClientesMap.get(nome) ?? 0;
        topClientesMap.set(nome, atual + parseDecimal(cliente.valor_total ?? 0));
      });

      (kpis.top_produtos ?? []).forEach((produto, index) => {
        const nome = produto.produto ?? `Produto não identificado ${index + 1}`;
        const atual = topProdutosMap.get(nome) ?? 0;
        topProdutosMap.set(nome, atual + parseDecimal(produto.valor_total ?? 0));
      });

      (kpis.top_cidades ?? []).forEach((cidade, index) => {
        const nome = cidade.cidade ?? `Cidade não identificada ${index + 1}`;
        const atual = topCidadesMap.get(nome) ?? 0;
        topCidadesMap.set(nome, atual + parseDecimal(cidade.valor_total ?? 0));
      });
    });

    return {
      totals,
      topClientesMap,
      topProdutosMap,
      topCidadesMap,
    };
  }, [filteredResultados]);

  const latestKpi = useMemo(() => {
    return [...filteredResultados].sort((a, b) => {
      const anoA = a.periodo_ano ?? 0;
      const anoB = b.periodo_ano ?? 0;
      if (anoA !== anoB) {
        return anoB - anoA;
      }
      return (b.periodo_mes ?? 0) - (a.periodo_mes ?? 0);
    })[0];
  }, [filteredResultados]);

  const previousPeriodKpi = useMemo(() => {
    if (!latestKpi?.periodo_mes || !latestKpi?.periodo_ano) {
      return null;
    }

    const currentMonth = latestKpi.periodo_mes;
    const currentYear = latestKpi.periodo_ano;
    const previousMonth = currentMonth - 1;

    if (previousMonth >= 1) {
      return (
        (kpisQuery.data?.resultados ?? []).find(
          (item) => item.periodo_mes === previousMonth && item.periodo_ano === currentYear
        ) ?? null
      );
    }

    return (
      (previousYearQuery.data?.resultados ?? []).find(
        (item) => item.periodo_mes === 12 && item.periodo_ano === currentYear - 1
      ) ?? null
    );
  }, [kpisQuery.data, latestKpi, previousYearQuery.data]);

  const faturamentoPeriodo = useMemo(() => {
    if (isAllMonths) {
      const months = filteredResultados
        .map((item) => item.periodo_mes)
        .filter((item): item is number => Boolean(item));
      if (!months.length) {
        return null;
      }
      const minMonth = Math.min(...months);
      const maxMonth = Math.max(...months);
      return `${String(minMonth).padStart(2, '0')}/${selectedYear} a ${String(maxMonth).padStart(2, '0')}/${selectedYear}`;
    }

    const mes = latestKpi?.periodo_mes;
    const ano = latestKpi?.periodo_ano;

    if (!mes || !ano) {
      return null;
    }

    return `${String(mes).padStart(2, '0')}/${ano}`;
  }, [filteredResultados, isAllMonths, latestKpi?.periodo_mes, latestKpi?.periodo_ano, selectedYear]);

  const stats = useMemo(() => {
    const currentKpis = latestKpi?.kpis;
    const previousKpis = previousPeriodKpi?.kpis;

    const previousYearResultados = previousYearQuery.data?.resultados ?? [];

    const totals = isAllMonths
      ? aggregatedData.totals
      : {
        totalSales: parseDecimal(currentKpis?.total_vendas ?? 0),
        totalNotes: currentKpis?.quantidade_notas ?? 0,
        totalTaxes: parseDecimal(currentKpis?.total_icms ?? 0)
          + parseDecimal(currentKpis?.total_ipi ?? 0)
          + parseDecimal(currentKpis?.total_pis ?? 0)
          + parseDecimal(currentKpis?.total_cofins ?? 0),
      };

    const previousTotals = isAllMonths
      ? previousYearResultados.reduce(
        (acc, item) => {
          acc.totalSales += parseDecimal(item.kpis.total_vendas ?? 0);
          acc.totalNotes += item.kpis.quantidade_notas ?? 0;
          acc.totalTaxes += parseDecimal(item.kpis.total_icms ?? 0)
            + parseDecimal(item.kpis.total_ipi ?? 0)
            + parseDecimal(item.kpis.total_pis ?? 0)
            + parseDecimal(item.kpis.total_cofins ?? 0);
          return acc;
        },
        { totalSales: 0, totalNotes: 0, totalTaxes: 0 }
      )
      : {
        totalSales: parseDecimal(previousKpis?.total_vendas ?? 0),
        totalNotes: previousKpis?.quantidade_notas ?? 0,
        totalTaxes: parseDecimal(previousKpis?.total_icms ?? 0)
          + parseDecimal(previousKpis?.total_ipi ?? 0)
          + parseDecimal(previousKpis?.total_pis ?? 0)
          + parseDecimal(previousKpis?.total_cofins ?? 0),
      };

    const totalSalesChange = previousTotals.totalSales
      ? ((totals.totalSales - previousTotals.totalSales) / previousTotals.totalSales) * 100
      : 0;
    const comparativoAnualSalesChange = previousTotals.totalSales
      ? ((totals.totalSales - previousTotals.totalSales) / previousTotals.totalSales) * 100
      : 0;
    const ticketMedio = totals.totalNotes ? totals.totalSales / totals.totalNotes : 0;
    const previousTicketMedio = previousTotals.totalNotes
      ? previousTotals.totalSales / previousTotals.totalNotes
      : 0;
    const ticketChange = previousTicketMedio
      ? ((ticketMedio - previousTicketMedio) / previousTicketMedio) * 100
      : 0;
    const totalTaxesChange = previousTotals.totalTaxes
      ? ((totals.totalTaxes - previousTotals.totalTaxes) / previousTotals.totalTaxes) * 100
      : 0;

    return [
      {
        title: `Faturamento Mensal${faturamentoPeriodo ? ` (Período ${faturamentoPeriodo})` : ''}`,
        value: formatCurrency(totals.totalSales),
        description: formatPercent(totalSalesChange),
        icon: TrendingUp,
        trend: totalSalesChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-sky-500',
      },
      {
        title: 'Comparativo anual',
        value: `${comparativoAnualSalesChange >= 0 ? '+' : ''}${comparativoAnualSalesChange.toFixed(1)}%`,
        description: isAllMonths
          ? `vs. mesmo período de ${year - 1}`
          : `vs. ${String(latestKpi?.periodo_mes ?? 1).padStart(2, '0')}/${year - 1}`,
        icon: comparativoAnualSalesChange >= 0 ? TrendingUp : TrendingDown,
        trend: comparativoAnualSalesChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-emerald-500',
      },
      {
        title: 'Ticket Médio',
        value: formatCurrency(ticketMedio),
        description: formatPercent(ticketChange),
        icon: Users,
        trend: ticketChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-amber-400',
      },
      {
        title: 'Impostos sobre vendas',
        value: formatCurrency(totals.totalTaxes),
        description: formatPercent(totalTaxesChange),
        icon: Percent,
        trend: totalTaxesChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-violet-500',
      },
    ];
  }, [aggregatedData.totals, faturamentoPeriodo, isAllMonths, latestKpi, previousPeriodKpi, previousYearQuery.data, year]);

  const salesEvolutionData = useMemo(() => {
    return [...filteredResultados]
      .filter((item) => item.periodo_mes)
      .sort((a, b) => (a.periodo_mes ?? 0) - (b.periodo_mes ?? 0))
      .map((item, index) => {
        const monthIndex = (item.periodo_mes ?? index + 1) - 1;
        return {
          month: monthLabels[monthIndex] ?? `Mês ${item.periodo_mes ?? index + 1}`,
          faturamento: parseDecimal(item.kpis.total_vendas ?? 0),
        };
      });
  }, [filteredResultados]);

  const selectedMonthLabel = selectedMonth === 'all' ? null : monthLabels[monthNumber - 1];
  const chartMessage = kpisQuery.isLoading
    ? 'Carregando dados...'
    : kpisQuery.isError
      ? 'Não foi possível carregar o gráfico.'
      : selectedMonthLabel
        ? `Nenhum dado disponível para ${selectedMonthLabel} de ${selectedYear}.`
        : `Nenhum dado disponível para ${selectedYear}.`;
  const hasChartData = salesEvolutionData.length > 0;

  const aggregatedTopClientes = useMemo(() => {
    return [...aggregatedData.topClientesMap.entries()]
      .map(([cliente, valor_total]) => ({ cliente, valor_total }))
      .sort((a, b) => b.valor_total - a.valor_total)
      .slice(0, 5);
  }, [aggregatedData.topClientesMap]);

  const aggregatedTopProdutos = useMemo(() => {
    return [...aggregatedData.topProdutosMap.entries()]
      .map(([produto, valor_total]) => ({ produto, valor_total }))
      .sort((a, b) => b.valor_total - a.valor_total)
      .slice(0, 5);
  }, [aggregatedData.topProdutosMap]);

  const aggregatedTopCidades = useMemo(() => {
    return [...aggregatedData.topCidadesMap.entries()]
      .map(([cidade, valor_total]) => ({ cidade, valor_total }))
      .sort((a, b) => b.valor_total - a.valor_total)
      .slice(0, 5);
  }, [aggregatedData.topCidadesMap]);

  const totalFaturamento = isAllMonths
    ? aggregatedData.totals.totalSales
    : parseDecimal(latestKpi?.kpis.total_vendas ?? 0);
  const topClientes = useMemo(
    () => (isAllMonths ? aggregatedTopClientes : (latestKpi?.kpis.top_clientes ?? [])),
    [aggregatedTopClientes, isAllMonths, latestKpi?.kpis.top_clientes],
  );
  const topProdutos = useMemo(
    () => (isAllMonths ? aggregatedTopProdutos : (latestKpi?.kpis.top_produtos ?? [])),
    [aggregatedTopProdutos, isAllMonths, latestKpi?.kpis.top_produtos],
  );
  const topCidades = useMemo(
    () => (isAllMonths ? aggregatedTopCidades : (latestKpi?.kpis.top_cidades ?? [])),
    [aggregatedTopCidades, isAllMonths, latestKpi?.kpis.top_cidades],
  );

  const resolvePercentual = (percentual?: number | string, valorTotal?: number | string) => {
    if (percentual !== undefined && percentual !== null) {
      return parseDecimal(percentual);
    }

    const valor = parseDecimal(valorTotal ?? 0);
    if (!totalFaturamento || !valor) {
      return null;
    }

    return (valor / totalFaturamento) * 100;
  };

  const isLoading = kpisQuery.isLoading || previousYearQuery.isLoading;
  const hasError = kpisQuery.isError || previousYearQuery.isError;

  const topClientesItems = topClientes.map((cliente, index) => {
    const percentual = resolvePercentual(cliente.percentual, cliente.valor_total);
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

  const topProdutosItems = topProdutos.map((produto, index) => {
    const percentual = resolvePercentual(produto.percentual, produto.valor_total);
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

  const topCidadesItems = topCidades.map((cidade, index) => {
    const percentual = resolvePercentual(cidade.percentual, cidade.valor_total);
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

  useEffect(() => {
    if (!yearOptions.length) {
      return;
    }

    if (!yearOptions.includes(year)) {
      setSelectedYear(String(yearOptions[0]));
    }
  }, [year, yearOptions]);

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

      {/* <Button onClick={handleAIPlanAction} className="w-fit gap-2">
        <Sparkles className="h-4 w-4" />
        Gerar Plano de Ação com IA
      </Button> */}

      {hasError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar indicadores</AlertTitle>
          <AlertDescription>
            Não foi possível buscar os KPIs mais recentes na API.
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
          title="Top Clientes"
          description="Clientes com maior faturamento no último período"
          items={topClientesItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum cliente registrado."
          totalValue={formatCurrency(totalFaturamento)}
        />
        <RankingCard
          title="Top Produtos"
          description="Itens com maior faturamento no último período"
          items={topProdutosItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum produto registrado."
          totalValue={formatCurrency(totalFaturamento)}
        />
        <RankingCard
          title="Top Cidades"
          description="Cidades com maior faturamento no último período"
          items={topCidadesItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhuma cidade registrada."
          totalValue={formatCurrency(totalFaturamento)}
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