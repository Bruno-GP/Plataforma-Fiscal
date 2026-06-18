import type { JobStatus, ProcessingJobResponse } from '@/services/jobs';
import type { FiscalOperationEntry } from '@/services/operations';

export interface InconsistenciasOverviewAlertProps {
  hasPendencias: boolean;
  hasActiveJobs: boolean;
  hasFailedJobs: boolean;
  hasLatestError: boolean;
  hasLatestWarning: boolean;
  activeJobsCount: number;
  pendingCount: number;
}

export interface InconsistenciasPendenciasCardProps {
  actionLabel: string;
  actionLink: string;
  hasPendencias: boolean;
  pendingCount: number;
  usaSped: boolean;
}

export interface InconsistenciasJobsCardProps {
  isError: boolean;
  isLoading: boolean;
  jobs: ProcessingJobResponse[];
}

export interface InconsistenciasHistoryCardProps {
  entries: FiscalOperationEntry[];
}

export type InconsistenciasJobStatus = JobStatus;
