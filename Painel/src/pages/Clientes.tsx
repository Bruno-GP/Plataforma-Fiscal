import { useEffect, useMemo, useState } from 'react';
import { Loader2, Percent, Sparkles, TrendingUp, Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import { useAuth } from '@/contexts/AuthContext';
import { fetchNfeAnaliseVendas, fetchNfeKpis, parseDecimal } from '@/services/nfe';
import { fetchSpedAnaliseVendas, fetchSpedKpis } from '@/services/sped';
import { monthLabels } from '@/services/utils';

import { Header } from './components/Header';
import { RankingCard } from './components/RankingCard';
import { StatCard } from './components/StatCard';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);

const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? "").replace(/\D/g, "");
  return digits.length === 14 && ![...digits].every((digit) => digit === "0");
};

export default function Clientes() {
  const [search, setSearch] = useState("");
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const { user } = useAuth();
  const usaSped = Boolean(user?.tem_sped);
  
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const kpisQuery = useQuery({
    queryKey: ["kpis-clientes", usaSped ? "sped" : "xml", emitenteCnpj],
    queryFn: () =>
      usaSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const sortedResultados = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    return [...resultados].sort((a, b) => {
      const anoA = a.periodo_ano ?? 0;
      const anoB = b.periodo_ano ?? 0;
      if (anoA !== anoB) {
        return anoB - anoA;
      }
      return (b.periodo_mes ?? 0) - (a.periodo_mes ?? 0);
    })[0];
  }, [kpisQuery.data]);

const latestKpi = sortedResultados;

  const availableYears = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    const years = new Set<number>();

    resultados.forEach((item) => {
      if (item.periodo_ano) {
        years.add(item.periodo_ano);
      }
    });

    return [...years].sort((a, b) => b - a);
  }, [kpisQuery.data]);

  useEffect(() => {
    if (!availableYears.length) {
      return;
    }

    const parsedYear = Number.parseInt(selectedYear, 10);
    if (!availableYears.includes(parsedYear)) {
      setSelectedYear(String(availableYears[0]));
    }
  }, [availableYears, selectedYear]);

  const safeYear = availableYears.length
    ? Number.parseInt(selectedYear, 10)
    : (latestKpi?.periodo_ano ?? new Date().getFullYear());

  const selectedPeriodKpis = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    const filteredByYear = resultados.filter((item) => item.periodo_ano === safeYear);

    if (selectedMonth !== 'all') {
      const selectedMonthNumber = Number.parseInt(selectedMonth, 10);
      return filteredByYear.find((item) => item.periodo_mes === selectedMonthNumber)?.kpis;
    }

    if (!filteredByYear.length) {
      return undefined;
    }

    const topClientesMap = new Map<string, number>();

    const aggregated = filteredByYear.reduce(
      (acc, item) => {
        const kpi = item.kpis;
        acc.total_vendas += parseDecimal(kpi.total_vendas ?? 0);
        acc.total_icms += parseDecimal(kpi.total_icms ?? 0);
        acc.total_ipi += parseDecimal(kpi.total_ipi ?? 0);
        acc.total_pis += parseDecimal(kpi.total_pis ?? 0);
        acc.total_cofins += parseDecimal(kpi.total_cofins ?? 0);

        (kpi.top_clientes ?? []).forEach((cliente) => {
          const name = cliente.cliente ?? 'Cliente não identificado';
          const value = parseDecimal(cliente.valor_total ?? 0);
          topClientesMap.set(name, (topClientesMap.get(name) ?? 0) + value);
        });

        return acc;
      },
      {
        total_vendas: 0,
        total_icms: 0,
        total_ipi: 0,
        total_pis: 0,
        total_cofins: 0,
      },
    );

    const topClientes = [...topClientesMap.entries()]
      .sort(([, valorA], [, valorB]) => valorB - valorA)
      .map(([cliente, valor_total]) => ({ cliente, valor_total, percentual: undefined }));

    return {
      ...aggregated,
      top_clientes: topClientes,
    };
  }, [kpisQuery.data, safeYear, selectedMonth]);

  const totalReceita = parseDecimal(selectedPeriodKpis?.total_vendas ?? 0);

  const totalImpostos =
    parseDecimal(selectedPeriodKpis?.total_icms ?? 0) +
    parseDecimal(selectedPeriodKpis?.total_ipi ?? 0) +
    parseDecimal(selectedPeriodKpis?.total_pis ?? 0) +
    parseDecimal(selectedPeriodKpis?.total_cofins ?? 0);
  const margem =
    totalReceita > 0
      ? ((totalReceita - totalImpostos) / totalReceita) * 100
      : 0;
  
  const topClientes = useMemo(() => selectedPeriodKpis?.top_clientes ?? [], [selectedPeriodKpis]);
  const filteredClientes = useMemo(
    () =>
      topClientes.filter((client) =>
        (client.cliente ?? '').toLowerCase().includes(search.toLowerCase()),
      ),
    [search, topClientes],
  );

  const topClientesItems = filteredClientes.map((cliente, index) => {
    const valorTotal = parseDecimal(cliente.valor_total ?? 0);
    const percentual =
      cliente.percentual !== undefined && cliente.percentual !== null
        ? parseDecimal(cliente.percentual)
        : totalReceita > 0
          ? (valorTotal / totalReceita) * 100
          : null;

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

  const stats = [
    {
      title: 'Faturamento por Cliente',
      value: formatCurrency(totalReceita),
      description: 'Total no último período',
      icon: TrendingUp,
      trend: 'up',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Total de Clientes no Ranking',
      value: String(topClientes.length),
      description: `${filteredClientes.length} após filtro`,
      icon: Users,
      trend: 'up',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Margem',
      value: `${margem.toFixed(1)}%`,
      description: formatPercent(margem),
      icon: Percent,
      trend: margem >= 0 ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ] as const;

  const handleGenerateReport = async () => {
    if (!hasEmitenteCnpj || !emitenteCnpj) {
      setReportError('CNPJ emitente inválido. Verifique o cadastro da empresa.');
      return;
    }

    setIsGeneratingReport(true);
    setReportError(null);

    try {
      const payload = {
        emitente_cnpj: emitenteCnpj,
        periodo_ano: safeYear,
        periodo_mes: selectedMonth === 'all' ? undefined : Number.parseInt(selectedMonth, 10),
        limite: 5,
        gerar_relatorio_ia: true,
      };

      const response = usaSped
        ? await fetchSpedAnaliseVendas(payload)
        : await fetchNfeAnaliseVendas(payload);

      setReport(response.relatorio_ia ?? 'A IA não retornou conteúdo para este período.');
    } catch (error) {
      setReport(null);
      setReportError(error instanceof Error ? error.message : 'Falha ao gerar relatório de clientes com IA.');
    } finally {
      setIsGeneratingReport(false);
    }
  };

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Análise de Clientes"
        subtitle="Visão consolidada de faturamento e desempenho"
        selectedMonth={selectedMonth}
        selectedYear={String(safeYear)}
        availableYears={availableYears.length ? availableYears : [safeYear]}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      {kpisQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar clientes</AlertTitle>
          <AlertDescription>
            Não foi possível buscar o ranking de clientes na API.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={kpisQuery.isLoading} />
        ))}
      </div>

      <div className="space-y-3">
        <Input
          placeholder="Buscar clientes..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="max-w-sm"
        />

        <RankingCard
          title="Ranking de Clientes"
          description="Lista de clientes por participação no faturamento"
          items={topClientesItems}
          isLoading={kpisQuery.isLoading}
          loadingMessage="Carregando clientes..."
          emptyMessage="Nenhum cliente encontrado."
          totalValue={formatCurrency(totalReceita)}
          listClassName="max-h-[420px] overflow-y-auto pr-1"
          showAbcReport={false}
          showAbcClassification={false}
        />

        <Card>
          <CardHeader>
            <CardTitle>Relatório de Clientes com IA</CardTitle>
            <CardDescription>
              Gere um resumo executivo com base no mesmo prompt dos relatórios de vendas.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={handleGenerateReport} disabled={isGeneratingReport || !hasEmitenteCnpj} className="gap-2">
              {isGeneratingReport ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {isGeneratingReport ? 'Gerando relatório...' : 'Gerar relatório de clientes com IA'}
            </Button>

            {reportError && (
              <Alert variant="destructive">
                <AlertTitle>Falha ao gerar relatório</AlertTitle>
                <AlertDescription>{reportError}</AlertDescription>
              </Alert>
            )}

            {report && (
              <pre className="whitespace-pre-wrap rounded-md border bg-muted/40 p-4 text-sm leading-6 text-foreground">
                {report}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}