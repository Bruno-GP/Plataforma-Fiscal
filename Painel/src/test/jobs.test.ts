import { beforeEach, describe, expect, it, vi } from 'vitest';

import { waitForJob, type ProcessingJobResponse } from '@/services/jobs';

const { apiFetchMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
}));

vi.mock('@/services/api', () => ({
  API_BASE_URL: 'http://localhost:8000/api',
  apiFetch: apiFetchMock,
}));

const makeJob = (status: ProcessingJobResponse['status']): ProcessingJobResponse => ({
  job_id: '00000000-0000-0000-0000-000000000001',
  tipo: 'NFE_PROCESSAMENTO_IMPORTADOS',
  status,
  mensagem: status === 'FAILED' ? 'Falha no processamento.' : `Status ${status}`,
  total_itens: 10,
  itens_processados: status === 'SUCCESS' ? 10 : 2,
  erro: status === 'FAILED' ? 'Falha no processamento.' : null,
  criado_em: '2026-05-05T12:00:00',
  iniciado_em: null,
  finalizado_em: null,
});

const jsonResponse = (body: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });

describe('jobs service', () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  it('waitForJob encerra quando o job retorna SUCCESS', async () => {
    apiFetchMock
      .mockResolvedValueOnce(jsonResponse(makeJob('QUEUED')))
      .mockResolvedValueOnce(jsonResponse(makeJob('RUNNING')))
      .mockResolvedValueOnce(jsonResponse(makeJob('SUCCESS')));

    const job = await waitForJob('00000000-0000-0000-0000-000000000001', {
      intervalMs: 1,
      timeoutMs: 1000,
    });

    expect(job.status).toBe('SUCCESS');
    expect(apiFetchMock).toHaveBeenCalledTimes(3);
  });

  it('waitForJob lança erro amigável quando o job retorna FAILED', async () => {
    apiFetchMock.mockResolvedValueOnce(jsonResponse(makeJob('FAILED')));

    await expect(
      waitForJob('00000000-0000-0000-0000-000000000001', {
        intervalMs: 1,
        timeoutMs: 1000,
      }),
    ).rejects.toThrow('Falha no processamento.');
  });
});
