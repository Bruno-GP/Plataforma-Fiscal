import { Line, LineChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

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
  }).format(value);

export function EvolucaoChart({
  billingData,
  hasChartData,
  chartMessage,
  selectedMonthLabel,
  selectedYear,
  title = 'Evolução do Faturamento',
  descriptionPrefix = 'Faturamento',
  metricLabel = 'Faturamento',
}: EvolucaoChartProps) {
  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            {selectedMonthLabel
              ? `${descriptionPrefix} de ${selectedMonthLabel} em ${selectedYear}`
              : `${descriptionPrefix} mensal ao longo de ${selectedYear}`}
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
                    formatter={(value: number) => [formatCurrency(value), metricLabel]}
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
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
                    name={metricLabel}
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
  );
}