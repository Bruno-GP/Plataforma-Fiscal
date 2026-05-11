import { check, group } from 'k6';
import { consultaDuration } from '../helpers/metrics.js';
import { get, getCompanyCnpj, getCompanyMode, jsonBody, testData } from '../helpers/httpClient.js';

export function consultaFlow(session) {
  return group('consulta/listagem', () => {
    const mode = getCompanyMode(session);
    const cnpj = getCompanyCnpj(session, mode);

    const consultasComuns = [
      get('/reforma-tributaria/tributos', 'reforma_tributos', [200], 1500),
      get(`/ncm/tributacao?codigo=${testData.ncm}&uf=${testData.uf}`, 'ncm_tributacao', [200, 404], 1500),
      get('/jobs?limit=10&offset=0', 'jobs_list', [200], 1500),
    ];

    const endpoint =
      mode === 'sped'
        ? `/sped/analise/fiscal/cfop?emitente_cnpj=${cnpj}&periodo_ano=${testData.ano}&periodo_mes=${testData.mes}&limite=100`
        : `/nfe/analise/fiscal/cfop?emitente_cnpj=${cnpj}&periodo_ano=${testData.ano}&periodo_mes=${testData.mes}&limite=100`;

    const listagem = get(endpoint, `${mode}_analise_fiscal_cfop`, [200, 400, 404], 3000);
    consultaDuration.add(listagem.timings.duration);

    check(listagem, {
      'consulta: contrato esperado': (res) => [200, 400, 404].includes(res.status),
      'consulta: payload validavel': (res) => res.status !== 200 || jsonBody(res)?.status === 'ok',
    });

    return { mode, cnpj, listagem, consultasComuns };
  });
}
