import { useMemo, useState } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Receipt } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useQuery } from '@tanstack/react-query';

import { fetchNfeKpis, parseDecimal } from '@/services/nfe';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '@/contexts/AuthContext';
import { getBillingData, getBillingStats } from '@/data/billingData';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
};

export default function Faturamento() {
  const [selectedYear, setSelectedYear] = useState('2025');
  
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  
  const year = Number.parseInt(selectedYear, 10);
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
    const monthLabels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    const resultados = kpisQuery.data?.resultados ?? [];

    return [...resultados]
      .filter((item) => item.periodo_mes)
      .sort((a, b) => (a.periodo_mes ?? 0) - (b.periodo_mes ?? 0))
      .map((item, index) => {
        const monthIndex = (item.periodo_mes ?? index + 1) - 1;
        const faturamento = parseDecimal(item.kpis.total_vendas);
        return {
          month: monthLabels[monthIndex] ?? `Mês ${item.periodo_mes ?? index + 1}`,
          faturamento,
          meta: faturamento * 1.05,
        };
      });
  }, [kpisQuery.data]);

  const stats = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    const previousResultados = previousYearQuery.data?.resultados ?? [];

    const totals = resultados.reduce(
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

    const previousTotals = previousResultados.reduce(
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
  }, [kpisQuery.data, previousYearQuery.data]);
  const chartMessage = kpisQuery.isLoading
    ? 'Carregando dados...'
    : kpisQuery.isError
      ? 'Não foi possível carregar os gráficos.'
      : `Nenhum dado disponível para ${selectedYear}.`;
  const hasChartData = billingData.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Faturamento</h1>
          <p className="text-muted-foreground">Acompanhe suas receitas e métricas financeiras</p>
        </div>
        <Select value={selectedYear} onValueChange={setSelectedYear}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="2024">2024</SelectItem>
            <SelectItem value="2025">2025</SelectItem>
          </SelectContent>
        </Select>
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
              Acumulado em {selectedYear}
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
              vs. mesmo período {year - 1}
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
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Evolução do Faturamento</CardTitle>
            <CardDescription>Faturamento mensal ao longo de {selectedYear}</CardDescription>
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

        <Card>
          <CardHeader>
            <CardTitle>Faturamento vs Meta</CardTitle>
            <CardDescription>Comparação com metas mensais</CardDescription>
          </CardHeader>
          <CardContent>
            {hasChartData ? (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={billingData}>
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
                      formatter={(value: number, name: string) => [
                        formatCurrency(value), 
                        name === 'faturamento' ? 'Faturamento' : 'Meta'
                      ]}
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--background))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Bar 
                      dataKey="faturamento" 
                      fill="hsl(var(--primary))" 
                      name="Faturamento"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar 
                      dataKey="meta" 
                      fill="hsl(var(--muted))" 
                      name="Meta"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
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
    </div>
  );
}
