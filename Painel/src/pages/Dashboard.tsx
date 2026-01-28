import { useMemo } from 'react';
import { TrendingUp, Users, Receipt, Percent, Sparkles } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

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
      },
      {
        title: 'Notas Emitidas',
        value: totalNotes.toString(),
        description: formatPercent(totalNotesChange),
        icon: Receipt,
        trend: totalNotesChange >= 0 ? 'up' : 'down',
      },
      {
        title: 'Ticket Médio',
        value: formatCurrency(ticketMedio),
        description: formatPercent(ticketChange),
        icon: Users,
        trend: ticketChange >= 0 ? 'up' : 'down',
      },
      {
        title: 'Impostos sobre vendas',
        value: formatCurrency(totalTaxes),
        description: formatPercent(totalTaxesChange),
        icon: Percent,
        trend: totalTaxesChange >= 0 ? 'up' : 'down',
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Visão geral do seu negócio</p>
      </div>

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
          <Card key={stat.title} className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading ? 'Carregando...' : stat.value}
              </div>
              <p className={`text-xs ${
                stat.trend === 'up' ? 'text-green-600' : 
                stat.trend === 'down' ? 'text-red-600' : 
                'text-muted-foreground'
              }`}>
                {isLoading ? '--' : `${stat.description} vs mês anterior`}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Top Clientes</CardTitle>
            <CardDescription>Clientes com maior faturamento no último período</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Carregando ranking...</p>
              ) : topClientes.length ? (
                topClientes.map((cliente, index) => {
                  const percentual = resolvePercentual(cliente.percentual, cliente.valor_total);

                  return (
                      <div key={`${cliente.cliente}-${index}`} className="flex items-center justify-between border-b pb-2 last:border-0">
                        <div>
                          <p className="font-medium">{cliente.cliente ?? 'Cliente não identificado'}</p>
                          <p className="text-sm text-muted-foreground">
                            {percentual !== null
                              ? `${percentual.toFixed(1)}% do faturamento`
                              : 'Participação não informada'}
                          </p>
                        </div>
                        <span className="text-sm font-medium">
                          {formatCurrency(parseDecimal(cliente.valor_total ?? 0))}
                        </span>
                      </div>
                    );
                })
              ) : (
                <p className="text-sm text-muted-foreground">Nenhum cliente registrado.</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Produtos</CardTitle>
            <CardDescription>Itens com maior faturamento no último período</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Carregando ranking...</p>
              ) : topProdutos.length ? (
                topProdutos.map((produto, index) => {
                  const percentual = resolvePercentual(produto.percentual, produto.valor_total);

                  return (
                      <div key={`${produto.produto}-${index}`} className="flex items-center justify-between border-b pb-2 last:border-0">
                        <div>
                          <p className="font-medium">{produto.produto ?? 'Produto não identificado'}</p>
                          <p className="text-sm text-muted-foreground">
                            {percentual !== null
                              ? `${percentual.toFixed(1)}% do faturamento`
                              : 'Participação não informada'}
                          </p>
                        </div>
                        <span className="text-sm font-medium">
                          {formatCurrency(parseDecimal(produto.valor_total ?? 0))}
                        </span>
                      </div>
                    );
                })
              ) : (
                <p className="text-sm text-muted-foreground">Nenhum produto registrado.</p>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Top Cidades</CardTitle>
            <CardDescription>Cidades com maior faturamento no último período</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Carregando ranking...</p>
              ) : topCidades.length ? (
                topCidades.map((cidade, index) => {
                  const percentual = resolvePercentual(cidade.percentual, cidade.valor_total);

                  return (
                    <div key={`${cidade.cidade}-${index}`} className="flex items-center justify-between border-b pb-2 last:border-0">
                      <div>
                        <p className="font-medium">{cidade.cidade ?? 'Cidade não identificada'}</p>
                        <p className="text-sm text-muted-foreground">
                          {percentual !== null
                            ? `${percentual.toFixed(1)}% do faturamento`
                            : 'Participação não informada'}
                        </p>
                      </div>
                      <span className="text-sm font-medium">
                        {formatCurrency(parseDecimal(cidade.valor_total ?? 0))}
                      </span>
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-muted-foreground">Nenhuma cidade registrada.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
