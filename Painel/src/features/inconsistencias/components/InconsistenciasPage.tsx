import { RefreshCcw } from 'lucide-react';

import { Button } from '@/components/ui/button';

import { InconsistenciasHistoryCard } from './InconsistenciasHistoryCard';
import { InconsistenciasJobsCard } from './InconsistenciasJobsCard';
import { InconsistenciasOverviewAlert } from './InconsistenciasOverviewAlert';
import { InconsistenciasPendenciasCard } from './InconsistenciasPendenciasCard';
import { useInconsistenciasPageData } from '../hooks/useInconsistenciasPageData';

export function InconsistenciasPage() {
  const {
    actionLabel,
    actionLink,
    activeJobsCount,
    hasActiveJobs,
    hasFailedJobs,
    hasLatestError,
    hasLatestWarning,
    hasPendencias,
    isJobsError,
    isJobsLoading,
    isRefreshingPendencias,
    jobs,
    operationHistory,
    pendingCount,
    refetchPendencias,
    usaSped,
  } = useInconsistenciasPageData();

  return (
    <section className="space-y-6 py-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Central de inconsistencias</h1>
          <p className="text-muted-foreground">
            Acompanhe pendencias fiscais, falhas recentes e atalhos para retomar a operacao.
          </p>
        </div>

        <Button variant="outline" onClick={() => refetchPendencias()} disabled={isRefreshingPendencias}>
          <RefreshCcw className="mr-2 h-4 w-4" />
          Atualizar
        </Button>
      </div>

      <InconsistenciasOverviewAlert
        activeJobsCount={activeJobsCount}
        hasActiveJobs={hasActiveJobs}
        hasFailedJobs={hasFailedJobs}
        hasLatestError={hasLatestError}
        hasLatestWarning={hasLatestWarning}
        hasPendencias={hasPendencias}
        pendingCount={pendingCount}
      />

      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <InconsistenciasPendenciasCard
          actionLabel={actionLabel}
          actionLink={actionLink}
          hasPendencias={hasPendencias}
          pendingCount={pendingCount}
          usaSped={usaSped}
        />

        <InconsistenciasJobsCard isError={isJobsError} isLoading={isJobsLoading} jobs={jobs} />

        <InconsistenciasHistoryCard entries={operationHistory} />
      </div>
    </section>
  );
}
