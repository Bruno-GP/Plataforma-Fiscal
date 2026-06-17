import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/contexts/AuthContext';
import { consultarPendenciasXmlImportados } from '@/services/nfe';
import { consultarPendenciasSped } from '@/services/sped';
import { fetchJobs } from '@/services/jobs';
import { readFiscalOperations } from '@/services/operations';

import { isActiveJob, isFailedJob } from '../helpers/inconsistenciasDisplay';

export function useInconsistenciasPageData() {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const usaSped = Boolean(user?.tem_sped);

  const pendenciasQuery = useQuery({
    queryKey: ['inconsistencias-pendencias', emitenteCnpj, usaSped],
    queryFn: async () => {
      if (!emitenteCnpj) {
        return { total_pendentes: 0, possui_pendentes: false };
      }

      return usaSped ? consultarPendenciasSped(emitenteCnpj) : consultarPendenciasXmlImportados(emitenteCnpj);
    },
    enabled: Boolean(emitenteCnpj),
    staleTime: 60_000,
  });

  const jobsQuery = useQuery({
    queryKey: ['inconsistencias-jobs', usaSped],
    queryFn: () =>
      fetchJobs({
        tipo: usaSped ? 'SPED_PROCESSAMENTO_IMPORTADOS' : 'NFE_PROCESSAMENTO_IMPORTADOS',
        limit: 10,
      }),
    staleTime: 30_000,
  });

  const operationHistory = useMemo(
    () => readFiscalOperations().filter((entry) => entry.cnpj === emitenteCnpj),
    [emitenteCnpj],
  );

  const latestError = operationHistory.find((entry) => entry.status === 'error');
  const latestWarning = operationHistory.find((entry) => entry.status === 'warning');
  const recentJobs = jobsQuery.data?.resultados ?? [];
  const activeJobs = recentJobs.filter(isActiveJob);
  const failedJobs = recentJobs.filter(isFailedJob);
  const pendingCount = pendenciasQuery.data?.total_pendentes ?? 0;
  const hasPendencias = pendingCount > 0;
  const hasActiveJobs = activeJobs.length > 0;
  const hasFailedJobs = failedJobs.length > 0;

  const actionLink = usaSped ? '/importacao-sped' : '/importacao-xml';
  const actionLabel = usaSped ? 'Abrir fluxo SPED' : 'Abrir fluxo XML';

  return {
    actionLabel,
    actionLink,
    activeJobsCount: activeJobs.length,
    hasActiveJobs,
    hasFailedJobs,
    hasLatestError: Boolean(latestError),
    hasLatestWarning: Boolean(latestWarning),
    hasPendencias,
    isJobsError: jobsQuery.isError,
    isJobsLoading: jobsQuery.isLoading,
    isRefreshingPendencias: pendenciasQuery.isFetching,
    jobs: recentJobs,
    operationHistory,
    pendingCount,
    refetchPendencias: pendenciasQuery.refetch,
    usaSped,
  };
}
