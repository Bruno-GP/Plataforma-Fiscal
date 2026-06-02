import { group } from 'k6';
import { DATA, get, login, think } from './lib/helpers.js';

export const options = {
  scenarios: {
    consultas_readonly: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 5 },
        { duration: '1m', target: 10 },
        { duration: '30s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.10'],
    http_req_duration: ['p(95)<2500', 'p(99)<5000'],
    'http_req_duration{endpoint:nfe_dashboard_vendas}': ['p(95)<3500'],
    'http_req_duration{endpoint:sped_dashboard_vendas}': ['p(95)<3500'],
  },
};

const RUN_MODE = (__ENV.K6_RUN_MODE || 'both').toLowerCase();
const DASHBOARD_MAX_DURATION_MS = Number(__ENV.K6_DASHBOARD_MAX_DURATION_MS || 3500);

export default function () {
  login();

  group('jobs e cadastro fiscal', () => {
    get('/jobs/metrics', 'jobs_metrics');
    get('/jobs?limit=10&offset=0', 'jobs_list');
    get('/reforma-tributaria/tributos', 'reforma_tributos');
    get(`/ncm/tributacao?codigo=${DATA.ncm}&uf=${DATA.uf}`, 'ncm_tributacao', [200, 404]);
  });

  if (RUN_MODE === 'both' || RUN_MODE === 'nfe') {
    group('consultas NFe/XML', () => {
      get(`/nfe/kpis?emitente_cnpj=${DATA.xmlCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=50`, 'nfe_kpis', [200, 400, 404]);
      get(`/nfe/analise/vendas?emitente_cnpj=${DATA.xmlCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=10`, 'nfe_analise_vendas', [200, 400, 404]);
      get(`/nfe/analise/compras?emitente_cnpj=${DATA.xmlCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=10`, 'nfe_analise_compras', [200, 400, 404]);
      get(`/nfe/analise/fiscal/cfop?emitente_cnpj=${DATA.xmlCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=100`, 'nfe_fiscal_cfop', [200, 400, 404]);
      get(`/nfe/analise/vendas/dashboard?emitente_cnpj=${DATA.xmlCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=5`, 'nfe_dashboard_vendas', [200, 400, 404], DASHBOARD_MAX_DURATION_MS);
    });
  }

  if (RUN_MODE === 'both' || RUN_MODE === 'sped') {
    group('consultas SPED', () => {
      get(`/sped/kpis?emitente_cnpj=${DATA.spedCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=50`, 'sped_kpis', [200, 400, 404]);
      get(`/sped/analise/vendas?emitente_cnpj=${DATA.spedCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=10`, 'sped_analise_vendas', [200, 400, 404]);
      get(`/sped/analise/compras?emitente_cnpj=${DATA.spedCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=10`, 'sped_analise_compras', [200, 400, 404]);
      get(`/sped/analise/fiscal/ncm?emitente_cnpj=${DATA.spedCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=100`, 'sped_fiscal_ncm', [200, 400, 404]);
      get(`/sped/analise/vendas/dashboard?emitente_cnpj=${DATA.spedCnpj}&periodo_ano=${DATA.ano}&periodo_mes=${DATA.mes}&limite=5`, 'sped_dashboard_vendas', [200, 400, 404], DASHBOARD_MAX_DURATION_MS);
    });
  }

  think(0.3, 1.5);
}
