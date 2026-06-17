import type { JobStatus } from '@/services/jobs';
import type { FiscalOperationEntry } from '@/services/operations';

export const operationTypeLabel: Record<FiscalOperationEntry['type'], string> = {
  'xml-import': 'Importacao XML',
  'xml-process': 'Processamento XML',
  'sped-import': 'Importacao SPED',
  'sped-process': 'Processamento SPED',
};

export const statusVariantMap: Record<FiscalOperationEntry['status'], 'default' | 'secondary' | 'destructive' | 'outline'> = {
  success: 'default',
  warning: 'secondary',
  error: 'destructive',
  cancelled: 'outline',
  queued: 'secondary',
  running: 'secondary',
};

export const statusLabelMap: Record<FiscalOperationEntry['status'], string> = {
  success: 'Sucesso',
  warning: 'Atencao',
  error: 'Erro',
  cancelled: 'Cancelada',
  queued: 'Em fila',
  running: 'Em execucao',
};

export const jobStatusVariantMap: Record<JobStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  PENDING: 'secondary',
  QUEUED: 'secondary',
  RUNNING: 'secondary',
  SUCCESS: 'default',
  FAILED: 'destructive',
  CANCELED: 'outline',
};

export const jobStatusLabelMap: Record<JobStatus, string> = {
  PENDING: 'Pendente',
  QUEUED: 'Em fila',
  RUNNING: 'Em execucao',
  SUCCESS: 'Concluido',
  FAILED: 'Falhou',
  CANCELED: 'Cancelado',
};

export const isActiveJob = (job: { status: JobStatus }) =>
  job.status === 'PENDING' || job.status === 'QUEUED' || job.status === 'RUNNING';

export const isFailedJob = (job: { status: JobStatus }) => job.status === 'FAILED';

export const getInconsistenciasOverviewDescription = ({
  activeJobsCount,
  hasActiveJobs,
  hasFailedJobs,
  hasLatestError,
  hasLatestWarning,
  hasPendencias,
  pendingCount,
}: {
  activeJobsCount: number;
  hasActiveJobs: boolean;
  hasFailedJobs: boolean;
  hasLatestError: boolean;
  hasLatestWarning: boolean;
  hasPendencias: boolean;
  pendingCount: number;
}) => {
  if (hasActiveJobs) {
    return `Ha ${activeJobsCount} processamento(s) em fila ou execucao. Pendencias podem permanecer ate a conclusao.`;
  }

  if (hasPendencias) {
    return `Ha ${pendingCount} arquivo(s) aguardando processamento.`;
  }

  if (hasFailedJobs || hasLatestError) {
    return 'Encontramos uma falha recente na operacao fiscal.';
  }

  if (hasLatestWarning) {
    return 'Ha um evento recente que merece revisao.';
  }

  return '';
};
