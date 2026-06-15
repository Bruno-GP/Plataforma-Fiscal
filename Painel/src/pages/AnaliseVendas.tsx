import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Header } from './components/Header';
import { RankingPanelGroup } from './components/RankingPanelGroup';
import { StatCard } from './components/StatCard';
import { SalesRegionCityMap } from './components/SalesRegionCityMap';
import { EvolucaoChart } from './components/EvolucaoChart';

import { useAnaliseVendasPageData } from '@/features/analiseVendas/hooks/useAnaliseVendasPageData';
import type { AnaliseVendasPageProps } from '@/features/analiseVendas/types';
import { monthLabels } from '@/utils/formatters';

export default function Dashboard({
  title = 'Vendas',
  subtitle = 'VisÃ£o geral do seu negÃ³cio',
}: AnaliseVendasPageProps) {
  const {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    availableYears,
    stats,
    salesEvolutionData,
    hasChartData,
    chartMessage,
    selectedMonthLabel,
    dashboardQuery,
    totalFaturamento,
    rankings,
    mapTopCidadesItems,
    mapTopRegioesItems,
    formatCurrency,
  } = useAnaliseVendasPageData();

  return (
    <div className="space-y-6 py-6">
      <Header
        title={title}
        subtitle={subtitle}
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="flex justify-end">
        <Button asChild variant="outline" className="h-10">
          <Link to="/detalhamento-vendas">Abrir detalhamento analí­tico</Link>
        </Button>
      </div>

      {dashboardQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar indicadores</AlertTitle>
          <AlertDescription>
            {dashboardQuery.error instanceof Error ? dashboardQuery.error.message : 'NÃ£o foi possÃ­vel buscar KPIs.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="stat-card-grid">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />
        ))}
      </div>

      <RankingPanelGroup
        rankings={rankings}
        isLoading={dashboardQuery.isLoading}
        totalValue={formatCurrency(totalFaturamento)}
      />

      <EvolucaoChart
        billingData={salesEvolutionData}
        hasChartData={hasChartData}
        chartMessage={chartMessage}
        selectedMonthLabel={selectedMonthLabel}
        selectedYear={selectedYear}
        title="Evolução das Vendas"
        descriptionPrefix="Vendas"
        metricLabel="Vendas"
      />

      <SalesRegionCityMap
        topCidadesItems={mapTopCidadesItems}
        topRegioesItems={mapTopRegioesItems}
        totalFaturamento={totalFaturamento}
        formatCurrency={formatCurrency}
      />
    </div>
  );
}
