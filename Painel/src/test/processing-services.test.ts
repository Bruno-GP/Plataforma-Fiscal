import { beforeEach, describe, expect, it, vi } from 'vitest';

import { processarXmlsImportados } from '@/services/nfe';
import { processarSpedsImportados } from '@/services/sped';

const { apiFetchMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
}));

vi.mock('@/services/api', () => ({
  API_BASE_URL: 'http://localhost:8000/api',
  apiFetch: apiFetchMock,
}));

const jobResponse = {
  job_id: '00000000-0000-0000-0000-000000000001',
  status: 'QUEUED',
  message: 'Processamento enviado para fila',
};

const jsonResponse = (body: unknown) =>
  new Response(JSON.stringify(body), {
    status: 202,
    headers: { 'Content-Type': 'application/json' },
  });

describe('processing services', () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  it('processarXmlsImportados retorna JobCreateResponse', async () => {
    apiFetchMock.mockResolvedValueOnce(jsonResponse(jobResponse));

    const response = await processarXmlsImportados('12.345.678/0001-99');

    expect(response).toEqual(jobResponse);
    expect(apiFetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/nfe/xml/processar-importados?cnpj_emitente=12345678000199',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('processarSpedsImportados retorna JobCreateResponse', async () => {
    apiFetchMock.mockResolvedValueOnce(jsonResponse(jobResponse));

    const response = await processarSpedsImportados('12.345.678/0001-99');

    expect(response).toEqual(jobResponse);
    expect(apiFetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/sped/processar-importados?cnpj_emitente=12345678000199',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
