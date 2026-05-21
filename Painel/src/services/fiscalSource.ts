import {
  fetchNfeAnaliseClientes,
  fetchNfeAnaliseCompras,
  fetchNfeAnaliseFiscalCfop,
  fetchNfeAnaliseFiscalHierarquica,
  fetchNfeAnaliseVendas,
  fetchNfeDashboardCompras,
  fetchNfeDashboardVendas,
  fetchNfeKpis,
} from './nfe';
import {
  fetchSpedAnaliseClientes,
  fetchSpedAnaliseCompras,
  fetchSpedAnaliseFiscalCfop,
  fetchSpedAnaliseFiscalHierarquica,
  fetchSpedAnaliseVendas,
  fetchSpedDashboardCompras,
  fetchSpedDashboardVendas,
  fetchSpedKpis,
} from './sped';

export type FiscalSource = 'nfe' | 'sped';

type FiscalRequestParams = Record<string, unknown>;
type RequestOptions = { signal?: AbortSignal };

export const getFiscalSource = (temSped?: boolean): FiscalSource => (temSped ? 'sped' : 'nfe');

export const getFiscalSourceKey = (temSped?: boolean) => getFiscalSource(temSped);

export const getFiscalSourceLabel = (temSped?: boolean) => (temSped ? 'SPED Fiscal' : 'XML / NFe');

export const createFiscalSourceApi = (temSped?: boolean) => {
  const isSped = getFiscalSource(temSped) === 'sped';

  return {
    source: getFiscalSource(temSped),
    sourceKey: getFiscalSourceKey(temSped),
    sourceLabel: getFiscalSourceLabel(temSped),
    isSped,
    kpis: (params: FiscalRequestParams = {}) =>
      isSped ? fetchSpedKpis(params) : fetchNfeKpis(params),
    dashboardCompras: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isSped ? fetchSpedDashboardCompras(params, options) : fetchNfeDashboardCompras(params, options),
    dashboardVendas: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isSped ? fetchSpedDashboardVendas(params, options) : fetchNfeDashboardVendas(params, options),
    analiseCompras: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isSped ? fetchSpedAnaliseCompras(params, options) : fetchNfeAnaliseCompras(params, options),
    analiseVendas: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isSped ? fetchSpedAnaliseVendas(params, options) : fetchNfeAnaliseVendas(params, options),
    analiseClientes: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isSped ? fetchSpedAnaliseClientes(params, options) : fetchNfeAnaliseClientes(params, options),
    analiseFiscalCfop: (params: FiscalRequestParams = {}) =>
      isSped ? fetchSpedAnaliseFiscalCfop(params) : fetchNfeAnaliseFiscalCfop(params),
    analiseFiscalHierarquica: (params: FiscalRequestParams = {}) =>
      isSped ? fetchSpedAnaliseFiscalHierarquica(params) : fetchNfeAnaliseFiscalHierarquica(params),
  };
};
