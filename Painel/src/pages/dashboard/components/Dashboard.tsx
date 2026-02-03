import { useMemo } from 'react';
import { TrendingUp, Users, Receipt, Percent, Sparkles } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

import { DashboardHeader } from './DashboardHeader';
import { DashboardRankingCard } from './DashboardRankingCard';
import { DashboardStatCard } from './DashboardStatCard';

import { fetchNfeKpis, fetchNfeKpisComparativoAtual, parseDecimal } from '@/services/nfe';
import { useAuth } from '@/contexts/AuthContext'
import { useChat } from '@/contexts/ChatContext';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

export default function Dashboard() {
  const { user } = useAuth();
  const { toggleChat, sendMessage, isOpen } = useChat();

  const emitenteCnpj = user?.emitente_cnpj;

  const comparativoQuery = useQuery({
    queryKey: ['nfe-kpis-comparativo-atual', emitenteCnpj],
    queryFn: () => fetchNfeKpisComparativoAtual(emitenteCnpj),
    staleTime: 5 * 60 * 1000,
  });

  const latestKpiQuery = useQuery({
    queryKey: ['nfe-kpis-latest', emitenteCnpj],
    queryFn: () => fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 12 }),
    staleTime: 5 * 60 * 1000,
  });

  const latestKpi = useMemo(() => {
    const resultados = latestKpiQuery.data?.resultados ?? [];
    return [...resultados].sort((a, b) => {
      const anoA = a.periodo_ano ?? 0;
      const anoB = b.periodo_ano ?? 0;
      if (anoA !== anoB) {
        return anoB - anoA;
      }
      return (b.periodo_mes ?? 0) - (a.periodo_mes ?? 0);
    })[0];
  }, [latestKpiQuery.data]);

    const faturamentoPeriodo = useMemo(() => {
    const mes = latestKpi?.periodo_mes;
    const ano = latestKpi?.periodo_ano;

    if (!mes || !ano) {
      return null;
    }

    return `${String(mes).padStart(2, '0')}/${ano}`;
  }, [latestKpi?.periodo_mes, latestKpi?.periodo_ano]);

  const stats = useMemo(() => {
    const kpis = comparativoQuery.data?.kpis;
    const totalSales = parseDecimal(kpis?.total_vendas.atual ?? 0);
    const totalSalesChange = parseDecimal(kpis?.total_vendas.variacao_percentual ?? 0);
    const totalNotes = kpis?.quantidade_notas.atual ?? 0;
    const totalNotesChange = parseDecimal(kpis?.quantidade_notas.variacao_percentual ?? 0);
    const ticketMedio = parseDecimal(kpis?.ticket_medio.atual ?? 0);
    const ticketChange = parseDecimal(kpis?.ticket_medio.variacao_percentual ?? 0);
    const totalTaxes = parseDecimal(kpis?.total_icms.atual ?? 0)
      + parseDecimal(kpis?.total_ipi.atual ?? 0)
      + parseDecimal(kpis?.total_pis.atual ?? 0)
      + parseDecimal(kpis?.total_cofins.atual ?? 0);
    const previousTaxes = parseDecimal(kpis?.total_icms.anterior ?? 0)
      + parseDecimal(kpis?.total_ipi.anterior ?? 0)
      + parseDecimal(kpis?.total_pis.anterior ?? 0)
      + parseDecimal(kpis?.total_cofins.anterior ?? 0);
    const totalTaxesChange = previousTaxes
      ? ((totalTaxes - previousTaxes) / previousTaxes) * 100
      : 0;

    return [
      {
        title: `Faturamento Mensal${faturamentoPeriodo ? ` (Período ${faturamentoPeriodo})` : ''}`,
        value: formatCurrency(totalSales),
        description: formatPercent(totalSalesChange),
        icon: TrendingUp,
        trend: totalSalesChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-sky-500',
      },
      {
        title: 'Notas Emitidas',
        value: totalNotes.toString(),
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
        value: formatCurrency(totalTaxes),
        description: formatPercent(totalTaxesChange),
        icon: Percent,
        trend: totalTaxesChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-violet-500',
      },
    ];
  }, [comparativoQuery.data, faturamentoPeriodo]);

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

  const isLoading = comparativoQuery.isLoading || latestKpiQuery.isLoading;
  const hasError = comparativoQuery.isError || latestKpiQuery.isError;

  const handleAIPlanAction = async () => {
    if (!isOpen) {
      toggleChat();
    }
    setTimeout(() => {
      sendMessage('Gere um plano de ação baseado nos dados atuais de faturamento');
    }, 300);
  };

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

  return (
    <div className="space-y-6">
      <DashboardHeader title="Dashboard" subtitle="Visão geral do seu negócio" />

      <Button onClick={handleAIPlanAction} className="w-fit gap-2">
        <Sparkles className="h-4 w-4" />
        Gerar Plano de Ação com IA
      </Button>

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
        />
        <DashboardRankingCard
          title="Top Produtos"
          description="Itens com maior faturamento no último período"
          items={topProdutosItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum produto registrado."
        />
        <DashboardRankingCard
          title="Top Cidades"
          description="Cidades com maior faturamento no último período"
          items={topCidadesItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhuma cidade registrada."
        />
      </div>
    </div>
  );
}
