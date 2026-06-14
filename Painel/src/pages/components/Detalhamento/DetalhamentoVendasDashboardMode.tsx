import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { monthLabels } from '@/services/utils';
import { formatCurrency, parseDecimal } from '@/utils/formatters';

type DashboardData = {
  resumo_atual?: {
    total_vendido?: number | string;
    quantidade_notas?: number;
    total_impostos?: number | string;
    total_impostos_complementares?: number | string;
    total_tributos_reforma?: number | string;
    ticket_medio?: number | string;
  };
  serie_mensal?: Array<{
    periodo_ano: number;
    periodo_mes: number;
    total_vendido?: number | string;
    quantidade_notas?: number;
    total_impostos?: number | string;
  }>;
};

type Props = {
  dashboardData?: DashboardData;
  isLoading: boolean;
  availableYears: number[];
  selectedYear: string;
  onYearChange: (year: string) => void;
};

const compactCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value);

const EmptyChart = ({ message }: { message: string }) => (
  <div className="flex h-full min-h-[260px] items-center justify-center rounded-md border border-dashed border-slate-700 bg-slate-950/45 px-4 text-center text-sm text-slate-400">
    {message}
  </div>
);

const currencyTooltipFormatter = (value: number | string) => [formatCurrency(parseDecimal(value)), 'Faturamento'];

export function DetalhamentoVendasDashboardMode({
  dashboardData,
  isLoading,
  availableYears,
  selectedYear,
  onYearChange,
}: Props) {
  const [startMonth, setStartMonth] = useState('1');
  const [endMonth, setEndMonth] = useState('12');

  useEffect(() => {
    if (Number.parseInt(startMonth, 10) > Number.parseInt(endMonth, 10)) {
      setEndMonth(startMonth);
    }
  }, [endMonth, startMonth]);

  const resumo = dashboardData?.resumo_atual;
  const startMonthNumber = Number.parseInt(startMonth, 10);
  const endMonthNumber = Number.parseInt(endMonth, 10);

  const serieMensal = useMemo(() => (dashboardData?.serie_mensal ?? [])
    .filter((item) => item.periodo_mes >= startMonthNumber && item.periodo_mes <= endMonthNumber)
    .sort((a, b) => a.periodo_mes - b.periodo_mes)
    .map((item) => ({
      month: monthLabels[item.periodo_mes - 1] ?? `Mes ${item.periodo_mes}`,
      faturamento: parseDecimal(item.total_vendido ?? 0),
      impostos: parseDecimal(item.total_impostos ?? 0),
      notas: item.quantidade_notas ?? 0,
      ticketMedio: item.quantidade_notas ? parseDecimal(item.total_vendido ?? 0) / item.quantidade_notas : 0,
    })), [dashboardData?.serie_mensal, endMonthNumber, startMonthNumber]);

  const totalVendido = serieMensal.reduce((total, item) => total + item.faturamento, 0);
  const totalImpostos = serieMensal.reduce((total, item) => total + item.impostos, 0);
  const quantidadeNotas = serieMensal.reduce((total, item) => total + item.notas, 0);
  const isFullYearRange = startMonthNumber === 1 && endMonthNumber === 12;
  const ticketMedio = isFullYearRange
    ? parseDecimal(resumo?.ticket_medio ?? 0)
    : quantidadeNotas
      ? totalVendido / quantidadeNotas
      : 0;

  const noDataMessage = isLoading ? 'Carregando dashboard de vendas...' : 'Nenhum dado encontrado para montar o grafico.';

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 rounded-md border border-slate-800 bg-slate-900/80 p-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-100">Filtros da visao grafica</p>
          <p className="mt-1 text-xs text-slate-400">Selecione um ano e um intervalo de meses para o grafico.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Ano</label>
            <Select value={selectedYear} onValueChange={onYearChange}>
              <SelectTrigger className="w-full border-slate-700 bg-slate-950 text-slate-100 sm:w-32">
                <SelectValue placeholder="Ano" />
              </SelectTrigger>
              <SelectContent className="border-slate-700 bg-slate-950 text-slate-100">
                {availableYears.map((year) => (
                  <SelectItem key={year} value={String(year)}>
                    {year}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Mes inicial</label>
            <Select value={startMonth} onValueChange={(value) => {
              setStartMonth(value);
              if (Number.parseInt(value, 10) > Number.parseInt(endMonth, 10)) {
                setEndMonth(value);
              }
            }}>
              <SelectTrigger className="w-full border-slate-700 bg-slate-950 text-slate-100 sm:w-40">
                <SelectValue placeholder="Mes inicial" />
              </SelectTrigger>
              <SelectContent className="border-slate-700 bg-slate-950 text-slate-100">
                {monthLabels.map((month, index) => (
                  <SelectItem key={month} value={String(index + 1)}>
                    {month}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Mes final</label>
            <Select value={endMonth} onValueChange={setEndMonth}>
              <SelectTrigger className="w-full border-slate-700 bg-slate-950 text-slate-100 sm:w-40">
                <SelectValue placeholder="Mes final" />
              </SelectTrigger>
              <SelectContent className="border-slate-700 bg-slate-950 text-slate-100">
                {monthLabels.map((month, index) => (
                  <SelectItem key={month} value={String(index + 1)} disabled={index + 1 < startMonthNumber}>
                    {month}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Vendas', value: formatCurrency(totalVendido) },
          { label: 'Notas', value: quantidadeNotas.toLocaleString('pt-BR') },
          { label: 'Ticket medio', value: formatCurrency(ticketMedio) },
          { label: 'Impostos', value: formatCurrency(totalImpostos) },
        ].map((item) => (
          <div key={item.label} className="rounded-md border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{item.label}</p>
            <p className="mt-2 text-xl font-semibold text-slate-100">{item.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-5">
        <Card className="border-slate-800 bg-slate-900/80 text-white">
          <CardHeader>
            <CardTitle className="text-base">Evolucao das vendas</CardTitle>
          </CardHeader>
          <CardContent className="h-[420px]">
            {serieMensal.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={serieMensal} margin={{ top: 12, right: 16, left: 8, bottom: 4 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(value) => compactCurrency(Number(value))} tickLine={false} axisLine={false} />
                  <Tooltip formatter={currencyTooltipFormatter} contentStyle={{ background: '#020617', border: '1px solid #1e293b', borderRadius: 8, color: '#e2e8f0' }} />
                  <Bar dataKey="faturamento" name="Faturamento" fill="#38bdf8" radius={[8, 8, 0, 0]} maxBarSize={72} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message={noDataMessage} />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="border-slate-800 bg-slate-900/80 text-white">
          <CardHeader>
            <CardTitle className="text-base">Vendas x impostos por mes</CardTitle>
          </CardHeader>
          <CardContent className="h-[340px]">
            {serieMensal.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={serieMensal} margin={{ top: 12, right: 16, left: 8, bottom: 4 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(value) => compactCurrency(Number(value))} tickLine={false} axisLine={false} />
                  <Tooltip
                    formatter={(value: number | string, name: string) => [
                      formatCurrency(parseDecimal(value)),
                      name === 'faturamento' ? 'Vendas' : 'Impostos',
                    ]}
                    labelFormatter={(label, payload) => {
                      const point = payload?.[0]?.payload;
                      const faturamento = parseDecimal(point?.faturamento ?? 0);
                      const impostos = parseDecimal(point?.impostos ?? 0);
                      const taxPercent = faturamento ? (impostos / faturamento) * 100 : 0;
                      return `${label} - Imposto sobre venda: ${taxPercent.toFixed(2)}%`;
                    }}
                    contentStyle={{ background: '#020617', border: '1px solid #1e293b', borderRadius: 8, color: '#e2e8f0' }}
                  />
                  <Bar dataKey="faturamento" name="faturamento" fill="#38bdf8" radius={[6, 6, 0, 0]} maxBarSize={46} />
                  <Bar dataKey="impostos" name="impostos" fill="#a78bfa" radius={[6, 6, 0, 0]} maxBarSize={46} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message={noDataMessage} />
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/80 text-white">
          <CardHeader>
            <CardTitle className="text-base">Ticket medio por mes</CardTitle>
          </CardHeader>
          <CardContent className="h-[340px]">
            {serieMensal.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={serieMensal} margin={{ top: 12, right: 16, left: 8, bottom: 4 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(value) => compactCurrency(Number(value))} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value: number | string) => [formatCurrency(parseDecimal(value)), 'Ticket medio']} contentStyle={{ background: '#020617', border: '1px solid #1e293b', borderRadius: 8, color: '#e2e8f0' }} />
                  <Line type="monotone" dataKey="ticketMedio" name="Ticket medio" stroke="#22c55e" strokeWidth={3} dot={{ fill: '#22c55e', r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message={noDataMessage} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
