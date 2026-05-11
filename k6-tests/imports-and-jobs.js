import http from 'k6/http';
import { check, group } from 'k6';
import { API_URL, DATA, get, login, shouldRunUploads, think } from './lib/helpers.js';

const xmlFixture = open('../API/app/tests/fixtures/nfe_valida.xml', 'b');
const spedFixture = open('../API/app/tests/fixtures/sped_valido.txt', 'b');

export const options = {
  scenarios: {
    importacao_controlada: {
      executor: 'constant-vus',
      vus: Number(__ENV.K6_IMPORT_VUS || 1),
      duration: __ENV.K6_IMPORT_DURATION || '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.20'],
    'http_req_duration{endpoint:xml_importar}': ['p(95)<5000'],
    'http_req_duration{endpoint:sped_importar}': ['p(95)<5000'],
  },
};

export default function () {
  login();

  group('pendencias antes da importacao', () => {
    get(`/nfe/xml/pendencias?cnpj_emitente=${DATA.xmlCnpj}`, 'xml_pendencias', [200, 400, 404]);
    get(`/sped/pendencias?cnpj_emitente=${DATA.spedCnpj}`, 'sped_pendencias', [200, 400, 404]);
  });

  if (shouldRunUploads()) {
    group('upload XML e SPED', () => {
      const xmlExpected = [200, 400, 403];
      const xmlResponse = http.post(
        `${API_URL}/nfe/xml/importar?cnpj_empresa_origem=${DATA.xmlCnpj}`,
        { arquivos: http.file(xmlFixture, `k6-nfe-${__VU}-${__ITER}.xml`, 'application/xml') },
        {
          responseCallback: http.expectedStatuses(...xmlExpected),
          tags: { endpoint: 'xml_importar' },
        },
      );
      check(xmlResponse, {
        'xml importar: contrato esperado': (res) => xmlExpected.includes(res.status),
      });

      const spedExpected = [200, 400, 403];
      const spedResponse = http.post(
        `${API_URL}/sped/importar?cnpj_empresa_origem=${DATA.spedCnpj}`,
        { arquivos: http.file(spedFixture, `k6-sped-${__VU}-${__ITER}.txt`, 'text/plain') },
        {
          responseCallback: http.expectedStatuses(...spedExpected),
          tags: { endpoint: 'sped_importar' },
        },
      );
      check(spedResponse, {
        'sped importar: contrato esperado': (res) => spedExpected.includes(res.status),
      });
    });
  }

  group('jobs de processamento', () => {
    const expected = shouldRunUploads() ? [202, 400, 403, 404] : [400, 403, 404];
    const xmlJob = http.post(`${API_URL}/nfe/xml/processar-importados?cnpj_emitente=${DATA.xmlCnpj}`, null, {
      responseCallback: http.expectedStatuses(...expected),
      tags: { endpoint: 'xml_processar_importados' },
    });
    check(xmlJob, {
      'xml processar importados: contrato esperado': (res) => expected.includes(res.status),
    });

    const spedJob = http.post(`${API_URL}/sped/processar-importados?cnpj_emitente=${DATA.spedCnpj}`, null, {
      responseCallback: http.expectedStatuses(...expected),
      tags: { endpoint: 'sped_processar_importados' },
    });
    check(spedJob, {
      'sped processar importados: contrato esperado': (res) => expected.includes(res.status),
    });

    get('/jobs?limit=20&offset=0', 'jobs_list');
    get('/jobs/metrics', 'jobs_metrics');
  });

  think(1, 2);
}
