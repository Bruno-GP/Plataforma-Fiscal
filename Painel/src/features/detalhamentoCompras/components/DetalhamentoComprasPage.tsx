import { Header } from '@/pages/components/Header';
import { RankingPanelGroup } from '@/pages/components/RankingPanelGroup';
import { StatCard } from '@/pages/components/StatCard';
import { monthLabels } from '@/utils/formatters';

import { DetalhamentoComprasNotasSection } from './DetalhamentoComprasNotasSection';
import { DetalhamentoComprasOverviewCard } from './DetalhamentoComprasOverviewCard';
import { DetalhamentoComprasStatusAlerts } from './DetalhamentoComprasStatusAlerts';
import { useDetalhamentoComprasPageData } from '../hooks/useDetalhamentoComprasPageData';

export function DetalhamentoComprasPage() {
  const {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    availableYears,
    dashboardQuery,
    notasComprasQuery,
    notasCompras,
    isSped,
    stats,
    purchasePanels,
    hasDetalhamentoCompras,
    rankingTotalValue,
    openPurchaseSupplierValues,
    setOpenPurchaseSupplierValues,
    openPurchaseNcmValues,
    setOpenPurchaseNcmValues,
    openPurchaseProductValues,
    setOpenPurchaseProductValues,
  } = useDetalhamentoComprasPageData();

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Detalhamento de compras"
        subtitle="Expansao hierarquica focada somente nas compras, com leitura em camadas ate o nivel de produto."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="stat-card-grid">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />
        ))}
      </div>

      <DetalhamentoComprasOverviewCard />

      <DetalhamentoComprasStatusAlerts
        isSped={isSped}
        notasComprasError={notasComprasQuery.error}
        dashboardError={dashboardQuery.error}
        hasDetalhamentoCompras={hasDetalhamentoCompras}
        isDashboardLoading={dashboardQuery.isLoading}
      />

      {hasDetalhamentoCompras && (
        <RankingPanelGroup rankings={purchasePanels} isLoading={dashboardQuery.isLoading} totalValue={rankingTotalValue} />
      )}

      <DetalhamentoComprasNotasSection
        isSped={isSped}
        notas={notasCompras}
        isLoading={notasComprasQuery.isLoading}
        openPurchaseSupplierValues={openPurchaseSupplierValues}
        onOpenPurchaseSupplierValuesChange={setOpenPurchaseSupplierValues}
        openPurchaseNcmValues={openPurchaseNcmValues}
        onOpenPurchaseNcmValuesChange={setOpenPurchaseNcmValues}
        openPurchaseProductValues={openPurchaseProductValues}
        onOpenPurchaseProductValuesChange={setOpenPurchaseProductValues}
      />
    </div>
  );
}

