import { useCallback, useEffect, useRef, useState } from 'react';

import {
  waitForJob,
  type JobCreateResponse,
  type ProcessingJobResponse,
  type WaitForJobOptions,
} from '@/services/jobs';

interface TrackCreatedJobOptions {
  signal?: AbortSignal;
  onUpdate?: (job: ProcessingJobResponse) => void;
  intervalMs?: number;
  timeoutMs?: number;
}

interface RunProcessingJobOptions {
  createJob: (signal: AbortSignal) => Promise<JobCreateResponse>;
  onCreated?: (job: JobCreateResponse) => void;
  onUpdate?: (job: ProcessingJobResponse) => void;
  intervalMs?: number;
  timeoutMs?: number;
}

export const isJobAbortError = (error: unknown) =>
  error instanceof DOMException && error.name === 'AbortError';

/**
 * Encapsula criação, polling e cancelamento local de jobs assíncronos do backend.
 * Cancelar aqui interrompe o acompanhamento da tela; um job já enfileirado pode continuar no backend.
 */
export function useProcessingJobFlow() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentJob, setCurrentJob] = useState<ProcessingJobResponse | null>(null);
  const [jobMessage, setJobMessage] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const currentJobRef = useRef<ProcessingJobResponse | null>(null);

  const setTrackedJob = useCallback((job: ProcessingJobResponse | null) => {
    currentJobRef.current = job;
    setCurrentJob(job);
  }, []);

  const resetJobState = useCallback(() => {
    setTrackedJob(null);
    setJobMessage(null);
  }, [setTrackedJob]);

  const cancelProcessing = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const getCurrentJob = useCallback(() => currentJobRef.current, []);

  /**
   * Acompanha um job já criado sem criar outro, útil quando a tela precisa orquestrar etapas próprias.
   */
  const trackCreatedJob = useCallback(
    async (
      createdJob: JobCreateResponse,
      { signal, onUpdate, intervalMs, timeoutMs }: TrackCreatedJobOptions = {},
    ) => {
      setJobMessage(createdJob.message);

      const waitOptions: WaitForJobOptions = {
        signal,
        intervalMs,
        timeoutMs,
        onUpdate: (job) => {
          setTrackedJob(job);
          setJobMessage(job.mensagem ?? `Status do processamento: ${job.status}`);
          onUpdate?.(job);
        },
      };

      const finishedJob = await waitForJob(createdJob.job_id, waitOptions);
      setTrackedJob(finishedJob);
      return finishedJob;
    },
    [setTrackedJob],
  );

  const runProcessingJob = useCallback(
    async ({ createJob, onCreated, onUpdate, intervalMs, timeoutMs }: RunProcessingJobOptions) => {
      abortRef.current?.abort();
      const abortController = new AbortController();
      abortRef.current = abortController;

      setIsProcessing(true);
      resetJobState();

      try {
        const createdJob = await createJob(abortController.signal);
        onCreated?.(createdJob);
        return await trackCreatedJob(createdJob, {
          signal: abortController.signal,
          onUpdate,
          intervalMs,
          timeoutMs,
        });
      } finally {
        if (abortRef.current === abortController) {
          abortRef.current = null;
        }
        setIsProcessing(false);
      }
    },
    [resetJobState, trackCreatedJob],
  );

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return {
    isProcessing,
    currentJob,
    jobMessage,
    setJobMessage,
    resetJobState,
    trackCreatedJob,
    runProcessingJob,
    cancelProcessing,
    getCurrentJob,
  };
}
