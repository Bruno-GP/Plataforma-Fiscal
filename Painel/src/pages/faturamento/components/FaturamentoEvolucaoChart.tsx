import { Line, LineChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import { formatCurrency } from '../components/utils';

interface BillingDataPoint {
  month: string;
  faturamento: number;
}

interface FaturamentoEvolucaoChartProps {
  billingData: BillingDataPoint[];
  hasChartData: boolean;
  chartMessage: string;
  selectedMonthLabel: string | null;
  selectedYear: string;
}

export function FaturamentoEvolucaoChart({
  billingData,
  hasChartData,
  chartMessage,
  selectedMonthLabel,
  selectedYear,
}: FaturamentoEvolucaoChartProps) {
  return (
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
  );
}