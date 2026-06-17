import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';

import type { InconsistenciasOverviewAlertProps } from '../types';
import { getInconsistenciasOverviewDescription } from '../helpers/inconsistenciasDisplay';

export function InconsistenciasOverviewAlert({
  activeJobsCount,
  hasActiveJobs,
  hasFailedJobs,
  hasLatestError,
  hasLatestWarning,
  hasPendencias,
  pendingCount,
}: InconsistenciasOverviewAlertProps) {
  const description = getInconsistenciasOverviewDescription({
    activeJobsCount,
    hasActiveJobs,
    hasFailedJobs,
    hasLatestError,
    hasLatestWarning,
    hasPendencias,
    pendingCount,
  });

  if (!hasPendencias && !hasActiveJobs && !hasFailedJobs && !hasLatestError && !hasLatestWarning) {
    return (
      <Alert className="border-emerald-200 bg-emerald-50 text-emerald-900 [&>svg]:text-emerald-700">
        <CheckCircle2 className="h-4 w-4" />
        <AlertTitle>Operacao sem inconsistencias abertas</AlertTitle>
        <AlertDescription>
          Nao encontramos pendencias fiscais abertas nem falhas recentes registradas para esta empresa.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert variant={hasFailedJobs || hasLatestError ? 'destructive' : 'default'}>
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>Existem pontos que pedem atencao</AlertTitle>
      <AlertDescription>{description}</AlertDescription>
    </Alert>
  );
}
