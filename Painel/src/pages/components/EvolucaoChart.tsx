import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface BillingDataPoint {
  month: string;
  faturamento: number;
}

interface EvolucaoChartProps {
  billingData: BillingDataPoint[];
  hasChartData: boolean;
  chartMessage: string;
  selectedMonthLabel: string | null;
  selectedYear: string;
  title?: string;
  descriptionPrefix?: string;
  metricLabel?: string;
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(value);

export function EvolucaoChart({
  billingData,
  hasChartData,
  chartMessage,
  selectedMonthLabel,
  selectedYear,
  title = 'Evolucao do Faturamento',
  descriptionPrefix = 'Faturamento',
  metricLabel = 'Faturamento',
}: EvolucaoChartProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="tv-panel-header">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription className="mt-2">
              {selectedMonthLabel
                ? `${descriptionPrefix} de ${selectedMonthLabel} em ${selectedYear}`
                : `${descriptionPrefix} mensal ao longo de ${selectedYear}`}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
            <span className="h-2.5 w-2.5 rounded-full bg-sky-400" />
            {metricLabel}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-5">
        {hasChartData ? (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={billingData} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="taxvisionEvolution" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.42} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#334155" strokeDasharray="4 8" vertical={false} opacity={0.55} />
                <XAxis
                  dataKey="month"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  tickFormatter={(value) => `${(Number(value) / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  formatter={(value: number) => [formatCurrency(value), metricLabel]}
                  cursor={{ stroke: '#38bdf8', strokeOpacity: 0.28 }}
                  contentStyle={{
                    backgroundColor: '#0b1425',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#e5e7eb',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="faturamento"
                  stroke="#7dd3fc"
                  strokeWidth={3}
                  fill="url(#taxvisionEvolution)"
                  activeDot={{ r: 5, fill: '#38bdf8', stroke: '#08111f', strokeWidth: 2 }}
                  name={metricLabel}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-80 items-center justify-center rounded-md border border-dashed border-slate-700 bg-slate-950/25 text-sm text-slate-400">
            {chartMessage}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
