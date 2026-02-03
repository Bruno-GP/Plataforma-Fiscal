import { useEffect, useMemo, useState } from 'react';
import { TrendingUp, Users, Receipt, Percent, Sparkles } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
// import { Button } from '@/components/ui/button';

import { DashboardHeader } from './DashboardHeader';
import { DashboardRankingCard } from './DashboardRankingCard';
import { DashboardStatCard } from './DashboardStatCard';

import { fetchNfeKpis, fetchNfeKpisComparativoAtual, parseDecimal } from '@/services/nfe';
import { useAuth } from '@/contexts/AuthContext'
// import { useChat } from '@/contexts/ChatContext';
import { monthLabels } from '../../faturamento/utils/utils';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

export default function Dashboard() {
  const { user } = useAuth();
  // const { toggleChat, sendMessage, isOpen } = useChat();

  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));

  const emitenteCnpj = user?.emitente_cnpj;

  const monthNumber = Number.parseInt(selectedMonth, 10);
  const year = Number.parseInt(selectedYear, 10);

  const yearsQuery = useQuery({
    queryKey: ['nfe-kpis-years', emitenteCnpj],
    queryFn: () => fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    staleTime: 5 * 60 * 1000,
  });

  const kpisQuery = useQuery({
    queryKey: ['nfe-kpis', emitenteCnpj, year],
    queryFn: () => fetchNfeKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year }),
    staleTime: 5 * 60 * 1000,
  });

  const previousYearQuery = useQuery({
    queryKey: ['nfe-kpis', emitenteCnpj, year - 1],
    queryFn: () => fetchNfeKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year - 1 }),
    enabled: year > 2000,
    staleTime: 5 * 60 * 1000,
  });

  const filteredResultados = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    if (selectedMonth === 'all') {
      return resultados;
    }
    return resultados.filter((item) => item.periodo_mes === monthNumber);
  }, [kpisQuery.data, monthNumber, selectedMonth]);

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
    const mes = latestKpi?.periodo_mes;
    const ano = latestKpi?.periodo_ano;

    if (!mes || !ano) {
      return null;
    }

    return `${String(mes).padStart(2, '0')}/${ano}`;
  }, [latestKpi?.periodo_mes, latestKpi?.periodo_ano]);

  const stats = useMemo(() => {
    const currentKpis = latestKpi?.kpis;
    const previousKpis = previousPeriodKpi?.kpis;

    const totals = {
      totalSales: parseDecimal(currentKpis?.total_vendas ?? 0),
      totalNotes: currentKpis?.quantidade_notas ?? 0,
      totalTaxes: parseDecimal(currentKpis?.total_icms ?? 0)
        + parseDecimal(currentKpis?.total_ipi ?? 0)
        + parseDecimal(currentKpis?.total_pis ?? 0)
        + parseDecimal(currentKpis?.total_cofins ?? 0),
    };

    const previousTotals = {
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
    const totalNotesChange = previousTotals.totalNotes
      ? ((totals.totalNotes - previousTotals.totalNotes) / previousTotals.totalNotes) * 100
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
        title: 'Notas Emitidas',
        value: totals.totalNotes.toString(),
        description: formatPercent(totalNotesChange),
        icon: Receipt,
        trend: totalNotesChange >= 0 ? 'up' : 'down',
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
  }, [faturamentoPeriodo, latestKpi, previousPeriodKpi]);

  const totalFaturamento = parseDecimal(latestKpi?.kpis.total_vendas ?? 0);
  const topClientes = latestKpi?.kpis.top_clientes ?? [];
  const topProdutos = latestKpi?.kpis.top_produtos ?? [];
  const topCidades = latestKpi?.kpis.top_cidades ?? [];

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
    <div className="space-y-6">
      <DashboardHeader
        title="Dashboard"
        subtitle="Visão geral do seu negócio"
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
          <DashboardStatCard key={stat.title} {...stat} isLoading={isLoading} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <DashboardRankingCard
          title="Top Clientes"
          description="Clientes com maior faturamento no último período"
          items={topClientesItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum cliente registrado."
          totalValue={formatCurrency(totalFaturamento)}
        />
        <DashboardRankingCard
          title="Top Produtos"
          description="Itens com maior faturamento no último período"
          items={topProdutosItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum produto registrado."
          totalValue={formatCurrency(totalFaturamento)}
        />
        <DashboardRankingCard
          title="Top Cidades"
          description="Cidades com maior faturamento no último período"
          items={topCidadesItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhuma cidade registrada."
          totalValue={formatCurrency(totalFaturamento)}
        />
      </div>
    </div>
  );
}
