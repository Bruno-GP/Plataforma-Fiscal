import { useEffect, useMemo, useState } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Receipt } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useQuery } from '@tanstack/react-query';

import { fetchNfeKpis, parseDecimal } from '@/services/nfe';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '@/contexts/AuthContext';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
};

const monthLabels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

export default function Faturamento() {
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState('2025');
  
  const { user } = useAuth();
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
  ) => items.map((item, index) => {
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Faturamento</h1>
          <p className="text-muted-foreground">Acompanhe suas receitas e métricas financeiras</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedMonth} onValueChange={setSelectedMonth}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Mês" />
            </SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="all">Todos os meses</SelectItem>
              {monthLabels.map((label, index) => (
                <SelectItem key={label} value={(index + 1).toString()}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={selectedYear} onValueChange={setSelectedYear}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-white">
              {availableYears.map((yearOption) => (
                <SelectItem key={yearOption} value={String(yearOption)}>
                  {yearOption}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

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

      {/* Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Faturamento Total
            </CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {kpisQuery.isLoading ? 'Carregando...' : formatCurrency(stats.totalSales)}
            </div>
            <p className="text-xs text-muted-foreground">
              {selectedMonthLabel ? `${selectedMonthLabel} de ${selectedYear}` : `Acumulado em ${selectedYear}`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Comparativo
            </CardTitle>
            {stats.percentChange >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${stats.percentChange >= 0 ? 'text-emerald-600 dark:text-emerald-500' : 'text-destructive'}`}>
              {kpisQuery.isLoading ? '--' : `${stats.percentChange >= 0 ? '+' : ''}${stats.percentChange.toFixed(1)}%`}
            </div>
            <p className="text-xs text-muted-foreground">
              {selectedMonthLabel
                ? `vs. ${selectedMonthLabel} de ${year - 1}`
                : `vs. mesmo período ${year - 1}`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Ticket Médio
            </CardTitle>
            <Receipt className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {kpisQuery.isLoading ? 'Carregando...' : formatCurrency(stats.ticketMedio)}
            </div>
            <p className="text-xs text-muted-foreground">
              {kpisQuery.isLoading ? 'Aguardando dados...' : `${stats.totalNotes} notas emitidas`}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Evolução do Faturamento</CardTitle>
            <CardDescription>
              {selectedMonthLabel
                ? `Faturamento de ${selectedMonthLabel} em ${selectedYear}`
                : `Faturamento mensal ao longo de ${selectedYear}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {hasChartData ? (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={billingData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis 
                      dataKey="month" 
                      className="text-xs"
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                    />
                    <YAxis 
                      className="text-xs"
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip 
                      formatter={(value: number) => [formatCurrency(value), 'Faturamento']}
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--background))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="faturamento" 
                      stroke="hsl(var(--primary))" 
                      strokeWidth={2}
                      dot={{ fill: 'hsl(var(--primary))' }}
                      connectNulls={false}
                      name="Faturamento"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-80 items-center justify-center text-sm text-muted-foreground">
                {chartMessage}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Top Clientes</CardTitle>
            <CardDescription>Ranking por faturamento no período selecionado</CardDescription>
          </CardHeader>
          <CardContent>
            {kpisQuery.isLoading ? (
              <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                Carregando ranking...
              </div>
            ) : topClientesData.length ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topClientesData} layout="vertical" margin={{ left: 12 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      type="number"
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      className="text-xs"
                      tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={110}
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      className="text-xs"
                    />
                    <Tooltip
                      formatter={(value: number) => [formatCurrency(value), 'Faturamento']}
                      labelFormatter={(_, payload) => payload?.[0]?.payload.fullName ?? ''}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                    />
                    <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                Nenhum cliente registrado.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Cidades</CardTitle>
            <CardDescription>Ranking por faturamento no período selecionado</CardDescription>
          </CardHeader>
          <CardContent>
            {kpisQuery.isLoading ? (
              <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                Carregando ranking...
              </div>
            ) : topCidadesData.length ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topCidadesData} layout="vertical" margin={{ left: 12 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      type="number"
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      className="text-xs"
                      tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                    />
                     <YAxis
                      dataKey="name"
                      type="category"
                      width={110}
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      className="text-xs"
                    />
                    <Tooltip
                      formatter={(value: number) => [formatCurrency(value), 'Faturamento']}
                      labelFormatter={(_, payload) => payload?.[0]?.payload.fullName ?? ''}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                Nenhuma cidade registrada.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Produtos</CardTitle>
            <CardDescription>Ranking por faturamento no período selecionado</CardDescription>
          </CardHeader>
          <CardContent>
            {kpisQuery.isLoading ? (
              <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                Carregando ranking...
              </div>
            ) : topProdutosData.length ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topProdutosData} layout="vertical" margin={{ left: 12 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      type="number"
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      className="text-xs"
                      tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={110}
                      tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      className="text-xs"
                    />
                    <Tooltip
                      formatter={(value: number) => [formatCurrency(value), 'Faturamento']}
                      labelFormatter={(_, payload) => payload?.[0]?.payload.fullName ?? ''}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                    />
                    <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                {chartMessage}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
