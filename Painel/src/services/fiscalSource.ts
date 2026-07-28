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
import {
  fetchContaAzulAnaliseClientes,
  fetchContaAzulAnaliseCompras,
  fetchContaAzulAnaliseFiscalCfop,
  fetchContaAzulAnaliseFiscalHierarquica,
  fetchContaAzulAnaliseVendas,
  fetchContaAzulDashboardCompras,
  fetchContaAzulDashboardVendas,
  fetchContaAzulKpis,
} from './contaAzul';
import type { SessionUser } from './api';

export type FiscalSource = 'nfe' | 'sped' | 'conta_azul';

type FiscalRequestParams = Record<string, unknown>;
type RequestOptions = { signal?: AbortSignal };
type FiscalSourceInput = boolean | Pick<SessionUser, 'tem_sped' | 'tem_conta_azul' | 'tem_xml'> | null | undefined;

const isFiscalSourceFlags = (
  value: FiscalSourceInput,
): value is Pick<SessionUser, 'tem_sped' | 'tem_conta_azul' | 'tem_xml'> =>
  typeof value === 'object' && value !== null;

export const getFiscalSource = (source?: FiscalSourceInput): FiscalSource => {
  if (typeof source === 'boolean') {
    return source ? 'sped' : 'nfe';
  }

  if (isFiscalSourceFlags(source)) {
    if (source.tem_conta_azul) {
      return 'conta_azul';
    }

    if (source.tem_sped) {
      return 'sped';
    }
  }

  return 'nfe';
};

export const getFiscalSourceKey = (source?: FiscalSourceInput) => getFiscalSource(source);

export const getFiscalSourceLabel = (source?: FiscalSourceInput) => {
  const fiscalSource = getFiscalSource(source);
  if (fiscalSource === 'sped') {
    return 'SPED Fiscal';
  }
  if (fiscalSource === 'conta_azul') {
    return 'Conta Azul';
  }
  return 'XML / NFe';
};

/**
 * Expõe APIs equivalentes por fonte fiscal; as páginas escolhem NFe/SPED sem duplicar chamadas.
 */
export const createFiscalSourceApi = (source?: FiscalSourceInput) => {
  const fiscalSource = getFiscalSource(source);
  const isSped = fiscalSource === 'sped';
  const isContaAzul = fiscalSource === 'conta_azul';

  return {
    source: fiscalSource,
    sourceKey: getFiscalSourceKey(source),
    sourceLabel: getFiscalSourceLabel(source),
    isSped,
    kpis: (params: FiscalRequestParams = {}) =>
      isContaAzul ? fetchContaAzulKpis(params) : isSped ? fetchSpedKpis(params) : fetchNfeKpis(params),
    dashboardCompras: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isContaAzul
        ? fetchContaAzulDashboardCompras(params, options)
        : isSped
          ? fetchSpedDashboardCompras(params, options)
          : fetchNfeDashboardCompras(params, options),
    dashboardVendas: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isContaAzul
        ? fetchContaAzulDashboardVendas(params, options)
        : isSped
          ? fetchSpedDashboardVendas(params, options)
          : fetchNfeDashboardVendas(params, options),
    analiseCompras: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isContaAzul
        ? fetchContaAzulAnaliseCompras(params, options)
        : isSped
          ? fetchSpedAnaliseCompras(params, options)
          : fetchNfeAnaliseCompras(params, options),
    analiseVendas: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isContaAzul
        ? fetchContaAzulAnaliseVendas(params, options)
        : isSped
          ? fetchSpedAnaliseVendas(params, options)
          : fetchNfeAnaliseVendas(params, options),
    analiseClientes: (params: FiscalRequestParams = {}, options: RequestOptions = {}) =>
      isContaAzul
        ? fetchContaAzulAnaliseClientes(params, options)
        : isSped
          ? fetchSpedAnaliseClientes(params, options)
          : fetchNfeAnaliseClientes(params, options),
    analiseFiscalCfop: (params: FiscalRequestParams = {}) =>
      isContaAzul
        ? fetchContaAzulAnaliseFiscalCfop(params)
        : isSped
          ? fetchSpedAnaliseFiscalCfop(params)
          : fetchNfeAnaliseFiscalCfop(params),
    analiseFiscalHierarquica: (params: FiscalRequestParams = {}) =>
      isContaAzul
        ? fetchContaAzulAnaliseFiscalHierarquica(params)
        : isSped
          ? fetchSpedAnaliseFiscalHierarquica(params)
          : fetchNfeAnaliseFiscalHierarquica(params),
  };
};
