import { DollarSign, Receipt, TrendingDown, TrendingUp } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { formatCurrency } from '../utils/utils';

interface FaturamentoStatsData {
  totalSales: number;
  totalNotes: number;
  totalTaxes: number;
  ticketMedio: number;
  percentChange: number;
}

interface FaturamentoStatsProps {
  stats: FaturamentoStatsData;
  isLoading: boolean;
  selectedMonthLabel: string | null;
  selectedYear: string;
  year: number;
}

export function FaturamentoStats({
  stats,
  isLoading,
  selectedMonthLabel,
  selectedYear,
  year,
}: FaturamentoStatsProps) {
  return (
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
            {isLoading ? 'Carregando...' : formatCurrency(stats.totalSales)}
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
          <div
            className={`text-2xl font-bold ${
              stats.percentChange >= 0 ? 'text-emerald-600 dark:text-emerald-500' : 'text-destructive'
            }`}
          >
            {isLoading ? '--' : `${stats.percentChange >= 0 ? '+' : ''}${stats.percentChange.toFixed(1)}%`}
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
            {isLoading ? 'Carregando...' : formatCurrency(stats.ticketMedio)}
          </div>
          <p className="text-xs text-muted-foreground">
            {isLoading ? 'Aguardando dados...' : `${stats.totalNotes} notas emitidas`}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}