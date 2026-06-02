import { check } from 'k6';
import { ensureTestUser, login, validateAuthenticatedSession } from '../helpers/auth.js';
import { get, getCompanyCnpj, getCompanyMode, jsonBody, testData } from '../helpers/httpClient.js';

export const options = {
  scenarios: {
    debug_status: {
      executor: 'shared-iterations',
      vus: 1,
      iterations: 1,
      maxDuration: '1m',
    },
  },
  thresholds: {},
};

export function setup() {
  ensureTestUser();
}

function printResponse(name, response) {
  const body = jsonBody(response) || response.body;
  console.log(`${name}: status=${response.status} body=${JSON.stringify(body).slice(0, 800)}`);
}

export default function () {
  const auth = login();
  const session = validateAuthenticatedSession(auth.session?.email);
  const mode = getCompanyMode(session || auth.session);
  const cnpj = getCompanyCnpj(session || auth.session, mode);

  console.log(`sessao: mode=${mode} cnpj=${cnpj} tem_sped=${Boolean((session || auth.session)?.tem_sped)}`);

  const reforma = get('/reforma-tributaria/tributos', 'debug_reforma_tributos', [200, 400, 401, 403, 404, 422, 500, 503], 5000);
  printResponse('reforma_tributos', reforma);

  const hierarquiaPath =
    mode === 'sped'
      ? `/sped/analise/fiscal/hierarquia?emitente_cnpj=${cnpj}&periodo_ano=${testData.ano}&periodo_mes=${testData.mes}&nivel_atual=${testData.fiscalNivel}&limite=500&offset=0`
      : `/nfe/analise/fiscal/hierarquia?emitente_cnpj=${cnpj}&periodo_ano=${testData.ano}&periodo_mes=${testData.mes}&nivel_atual=${testData.fiscalNivel}&limite=500&offset=0`;

  const hierarquia = get(hierarquiaPath, 'debug_fiscal_hierarquia', [200, 400, 401, 403, 404, 422, 500, 503], 5000);
  printResponse(`${mode}_fiscal_hierarquia`, hierarquia);

  check(null, {
    'debug executado': () => true,
  });
}
