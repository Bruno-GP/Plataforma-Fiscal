import { API_BASE_URL, apiFetch } from './api';

export type JobStatus = 'PENDING' | 'QUEUED' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELED';

export interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface ProcessingJobResponse {
  job_id: string;
  tipo: string;
  status: JobStatus;
  mensagem?: string | null;
  total_itens: number;
  itens_processados: number;
  erro?: string | null;
  criado_em: string;
  iniciado_em?: string | null;
  finalizado_em?: string | null;
}

export interface ProcessingJobListResponse {
  total: number;
  limit: number;
  offset: number;
  resultados: ProcessingJobResponse[];
}

export interface JobsMetricsResponse {
  total_jobs: number;
  por_status: Record<string, number>;
  por_tipo: Record<string, number>;
  duracao_media_ms: Record<string, number>;
}

export interface FetchJobsParams {
  status?: JobStatus;
  tipo?: string;
  data_inicio?: string;
  data_fim?: string;
  limit?: number;
  offset?: number;
}

export interface FetchJobMetricsParams {
  status?: JobStatus;
  tipo?: string;
  data_inicio?: string;
  data_fim?: string;
}

export interface WaitForJobOptions {
  signal?: AbortSignal;
  intervalMs?: number;
  timeoutMs?: number;
  onUpdate?: (job: ProcessingJobResponse) => void;
}

const TERMINAL_STATUSES = new Set<JobStatus>(['SUCCESS', 'FAILED', 'CANCELED']);
const DEFAULT_POLL_INTERVAL_MS = 2500;
const DEFAULT_TIMEOUT_MS = 15 * 60 * 1000;

const buildSearchParams = (params: Record<string, unknown>) => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if ((typeof value === 'string' || typeof value === 'number') && value !== '') {
      searchParams.set(key, String(value));
    }
  });

  return searchParams;
};

const parseApiError = async (response: Response, fallback: string) => {
  const error = await response.json().catch(() => ({ detail: fallback }));
  return error.detail ?? fallback;
};

export const fetchJob = async (jobId: string, options: { signal?: AbortSignal } = {}): Promise<ProcessingJobResponse> => {
  const response = await apiFetch(`${API_BASE_URL}/jobs/${jobId}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao consultar o processamento.'));
  }

  return response.json() as Promise<ProcessingJobResponse>;
};

export const fetchJobs = async (
  params: FetchJobsParams = {},
  options: { signal?: AbortSignal } = {},
): Promise<ProcessingJobListResponse> => {
  const searchParams = buildSearchParams({
    status: params.status,
    tipo: params.tipo,
    data_inicio: params.data_inicio,
    data_fim: params.data_fim,
    limit: params.limit,
    offset: params.offset,
  });
  const queryString = searchParams.toString();
  const response = await apiFetch(`${API_BASE_URL}/jobs${queryString ? `?${queryString}` : ''}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao consultar os processamentos.'));
  }

  return response.json() as Promise<ProcessingJobListResponse>;
};

export const fetchJobMetrics = async (
  params: FetchJobMetricsParams = {},
  options: { signal?: AbortSignal } = {},
): Promise<JobsMetricsResponse> => {
  const searchParams = buildSearchParams({
    status: params.status,
    tipo: params.tipo,
    data_inicio: params.data_inicio,
    data_fim: params.data_fim,
  });
  const queryString = searchParams.toString();
  const response = await apiFetch(`${API_BASE_URL}/jobs/metrics${queryString ? `?${queryString}` : ''}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Falha ao consultar metricas de processamento.'));
  }

  return response.json() as Promise<JobsMetricsResponse>;
};

const delay = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Acompanhamento do processamento cancelado.', 'AbortError'));
      return;
    }

    const timeoutId = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      'abort',
      () => {
        window.clearTimeout(timeoutId);
        reject(new DOMException('Acompanhamento do processamento cancelado.', 'AbortError'));
      },
      { once: true },
    );
  });

export const waitForJob = async (
  jobId: string,
  {
    signal,
    intervalMs = DEFAULT_POLL_INTERVAL_MS,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    onUpdate,
  }: WaitForJobOptions = {},
): Promise<ProcessingJobResponse> => {
  const startedAt = Date.now();

  while (true) {
    if (signal?.aborted) {
      throw new DOMException('Acompanhamento do processamento cancelado.', 'AbortError');
    }

    if (Date.now() - startedAt > timeoutMs) {
      throw new Error('Tempo limite excedido ao acompanhar o processamento.');
    }

    const job = await fetchJob(jobId, { signal });
    onUpdate?.(job);

    if (!TERMINAL_STATUSES.has(job.status)) {
      await delay(intervalMs, signal);
      continue;
    }

    if (job.status === 'SUCCESS') {
      return job;
    }

    throw new Error(job.erro ?? job.mensagem ?? 'Processamento nao concluido.');
  }
};
