import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ClientesListSection } from '@/features/clientes/components/ClientesListSection';
import { RiskDistributionCard } from '@/features/clientes/components/RiskDistributionCard';
import { TopContributorsCard } from '@/features/clientes/components/TopContributorsCard';
import { useClientesDashboardData } from '@/features/clientes/hooks/useClientesDashboardData';
import { monthLabels } from '@/utils/formatters';

import { Header } from './components/Header';
import { StatCard } from './components/StatCard';

export default function Clientes() {
  const {
    search,
    setSearch,
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    availableYears,
    kpisQuery,
    totalReceita,
    filteredClientes,
    topClientesItems,
    clientesEmRisco,
    clientesSemRisco,
    stats,
  } = useClientesDashboardData();

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Clientes"
        subtitle="Visao consolidada de faturamento e risco de perda"
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      {kpisQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar clientes</AlertTitle>
          <AlertDescription>
            Nao foi possivel buscar o ranking de clientes na API.
          </AlertDescription>
        </Alert>
      )}

      <div className="stat-card-grid">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={kpisQuery.isLoading} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.8fr)]">
        <ClientesListSection
          search={search}
          onSearchChange={setSearch}
          clientesCount={filteredClientes.length}
          topClientesItems={topClientesItems}
          isLoading={kpisQuery.isLoading}
          totalReceita={totalReceita}
        />

        <div className="space-y-6">
          <RiskDistributionCard
            totalClientes={filteredClientes.length}
            clientesSemRisco={clientesSemRisco}
            clientesEmRisco={clientesEmRisco}
          />
          <TopContributorsCard topClientesItems={topClientesItems} />
        </div>
      </div>
    </div>
  );
}
