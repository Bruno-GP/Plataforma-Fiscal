import { check, group } from 'k6';
import { dashboardDuration } from '../helpers/metrics.js';
import { get, getCompanyCnpj, getCompanyMode, jsonBody, testData } from '../helpers/httpClient.js';

export function dashboardFlow(session) {
  return group('dashboard autenticado', () => {
    const mode = getCompanyMode(session);
    const cnpj = getCompanyCnpj(session, mode);

    const jobsMetrics = get('/jobs/metrics', 'jobs_metrics', [200], 1500);
    check(jobsMetrics, {
      'jobs metrics: corpo json': (res) => jsonBody(res) !== null,
    });

    const dashboardPath =
      mode === 'sped'
        ? `/sped/analise/vendas/dashboard?emitente_cnpj=${cnpj}&periodo_ano=${testData.ano}&periodo_mes=${testData.mes}&limite=5`
        : `/nfe/analise/vendas/dashboard?emitente_cnpj=${cnpj}&periodo_ano=${testData.ano}&periodo_mes=${testData.mes}&limite=5`;

    const dashboard = get(dashboardPath, `${mode}_dashboard_vendas`, [200, 400, 404], 3500);
    dashboardDuration.add(dashboard.timings.duration);

    check(dashboard, {
      'dashboard: contrato esperado': (res) => [200, 400, 404].includes(res.status),
      'dashboard: retorno validavel': (res) => res.status !== 200 || jsonBody(res)?.status === 'ok',
    });

    return { mode, cnpj, jobsMetrics, dashboard };
  });
}
