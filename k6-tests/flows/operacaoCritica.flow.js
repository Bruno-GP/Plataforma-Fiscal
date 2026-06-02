import http from 'k6/http';
import { check, group } from 'k6';
import { env } from '../config/environments.js';
import { criticalValidationFailureRate, operacaoCriticaDuration } from '../helpers/metrics.js';
import { apiPath, get, getCompanyCnpj, getCompanyMode, jsonBody, testData } from '../helpers/httpClient.js';

export function operacaoCriticaFlow(session) {
  return group('operacao critica controlada', () => {
    const mode = getCompanyMode(session);
    const cnpj = getCompanyCnpj(session, mode);

    const consultaPesadaPath =
      mode === 'sped'
        ? `/sped/analise/fiscal/hierarquia?emitente_cnpj=${cnpj}&periodo_ano=${testData.ano}&periodo_mes=${testData.mes}&nivel_atual=${testData.fiscalNivel}&limite=500&offset=0`
        : `/nfe/analise/fiscal/hierarquia?emitente_cnpj=${cnpj}&periodo_ano=${testData.ano}&periodo_mes=${testData.mes}&nivel_atual=${testData.fiscalNivel}&limite=500&offset=0`;

    const consultaPesada = get(consultaPesadaPath, `${mode}_fiscal_hierarquia`, [200, 400, 404], 5000);
    operacaoCriticaDuration.add(consultaPesada.timings.duration);

    const consultaOk = check(consultaPesada, {
      'operacao critica: contrato esperado': (res) => [200, 400, 404].includes(res.status),
      'operacao critica: payload validavel': (res) => res.status !== 200 || jsonBody(res)?.status === 'ok',
    });

    criticalValidationFailureRate.add(!consultaOk);

    if (!env.allowSideEffects) {
      return { mode, cnpj, consultaPesada, sideEffectSkipped: true };
    }

    const processamentoPath =
      mode === 'sped'
        ? `/sped/processar-importados?cnpj_emitente=${cnpj}`
        : `/nfe/xml/processar-importados?cnpj_emitente=${cnpj}`;

    const expectedStatuses = [202, 400, 403, 404];
    const processamento = http.post(apiPath(processamentoPath), null, {
      responseCallback: http.expectedStatuses(...expectedStatuses),
      tags: { endpoint: `${mode}_processar_importados` },
    });

    const processamentoOk = check(processamento, {
      'processamento importados: contrato esperado': (res) => expectedStatuses.includes(res.status),
    });

    criticalValidationFailureRate.add(!processamentoOk);

    return { mode, cnpj, consultaPesada, processamento };
  });
}
