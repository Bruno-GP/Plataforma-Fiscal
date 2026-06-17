import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Header } from '@/pages/components/Header';
import { ReformaTributariaApuracaoTable } from '@/features/reformaTributaria/components/ReformaTributariaApuracaoTable';
import { ReformaTributariaFiltersCard } from '@/features/reformaTributaria/components/ReformaTributariaFiltersCard';
import { ReformaTributariaMemoriaTable } from '@/features/reformaTributaria/components/ReformaTributariaMemoriaTable';
import { ReformaTributariaStatsGrid } from '@/features/reformaTributaria/components/ReformaTributariaStatsGrid';
import { useReformaTributariaPageData } from '@/features/reformaTributaria/hooks/useReformaTributariaPageData';
import { monthLabels } from '@/utils/formatters';

export default function ReformaTributaria() {
  const {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    selectedTributo,
    setSelectedTributo,
    searchTerm,
    setSearchTerm,
    availableYears,
    tributosDisponiveis,
    apuracoes,
    memoriaFiltrada,
    stats,
    hasEmitenteCnpj,
    origemBackfill,
    backfillMutation,
    apuracaoQuery,
    memoriaQuery,
    tributosQuery,
  } = useReformaTributariaPageData();

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Reforma Tributaria"
        subtitle="Acompanhamento de CBS, IBS, Imposto Seletivo, apuracao e memoria de calculo."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <ReformaTributariaFiltersCard
        selectedTributo={selectedTributo}
        tributos={tributosDisponiveis}
        hasEmitenteCnpj={hasEmitenteCnpj}
        isBackfilling={backfillMutation.isPending}
        onTributoChange={setSelectedTributo}
        onBackfill={() => backfillMutation.mutate()}
      />

      {backfillMutation.isSuccess && (
        <Alert>
          <AlertTitle>Dados sincronizados</AlertTitle>
          <AlertDescription>
            {backfillMutation.data.periodos_processados} periodo(s) recalculado(s) para {origemBackfill.toUpperCase()}.
          </AlertDescription>
        </Alert>
      )}

      {(apuracaoQuery.isError || memoriaQuery.isError || tributosQuery.isError || backfillMutation.isError) && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar dados da Reforma</AlertTitle>
          <AlertDescription>
            {(apuracaoQuery.error instanceof Error && apuracaoQuery.error.message)
              || (memoriaQuery.error instanceof Error && memoriaQuery.error.message)
              || (tributosQuery.error instanceof Error && tributosQuery.error.message)
              || (backfillMutation.error instanceof Error && backfillMutation.error.message)
              || 'Nao foi possivel consultar a base tributaria.'}
          </AlertDescription>
        </Alert>
      )}

      <ReformaTributariaStatsGrid stats={stats} isLoading={apuracaoQuery.isLoading || memoriaQuery.isLoading} />

      <ReformaTributariaApuracaoTable apuracoes={apuracoes} isLoading={apuracaoQuery.isLoading} />

      <ReformaTributariaMemoriaTable
        memoria={memoriaFiltrada}
        searchTerm={searchTerm}
        isLoading={memoriaQuery.isLoading}
        onSearchTermChange={setSearchTerm}
      />
    </div>
  );
}
