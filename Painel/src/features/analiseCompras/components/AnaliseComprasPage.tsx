import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EvolucaoChart } from '@/pages/components/EvolucaoChart';
import { Header } from '@/pages/components/Header';
import { RankingPanelGroup } from '@/pages/components/RankingPanelGroup';
import { StatCard } from '@/pages/components/StatCard';
import { monthLabels } from '@/utils/formatters';

import { useAnaliseComprasPageData } from '../hooks/useAnaliseComprasPageData';

export function AnaliseComprasPage() {
  const {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    availableYears,
    dashboardQuery,
    stats,
    rankings,
    rankingTotalValue,
    comprasEvolutionData,
    hasChartData,
    chartMessage,
    selectedMonthLabel,
  } = useAnaliseComprasPageData();

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Compras"
        subtitle="Visão analítica das compras"
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="flex justify-end">
        <Button asChild variant="outline">
          <Link to="/detalhamento-compras">Abrir detalhamento analí­tico</Link>
        </Button>
      </div>

      {dashboardQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar analise de compras</AlertTitle>
          <AlertDescription>
            {dashboardQuery.error instanceof Error
              ? dashboardQuery.error.message
              : 'Não foi possÃ­vel consultar os dados de compras no momento.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="stat-card-grid">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />
        ))}
      </div>

      <RankingPanelGroup
        isLoading={dashboardQuery.isLoading}
        totalValue={rankingTotalValue}
        rankings={rankings}
      />

      <EvolucaoChart
        billingData={comprasEvolutionData}
        hasChartData={hasChartData}
        chartMessage={chartMessage}
        selectedMonthLabel={selectedMonthLabel}
        selectedYear={selectedYear}
        title="Evolução das compras"
        descriptionPrefix="Compras"
        metricLabel="Compras"
      />
    </div>
  );
}
