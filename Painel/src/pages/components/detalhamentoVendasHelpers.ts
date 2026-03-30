import type { NfeNotaDetalhada } from '@/services/nfe';
import { parseDecimal } from '@/services/nfe';

export const hierarchyLabelClass = 'text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400';

export type DetailMode = 'nota' | 'regiao';

export type RegionProduct = {
  key: string;
  code: string;
  description: string;
  totalQuantity: number;
  totalValue: number;
  notesCount: number;
  noteNumbers: string[];
};

export type RegionClient = {
  key: string;
  name: string;
  document: string;
  total: number;
  noteCount: number;
  products: RegionProduct[];
};

export type RegionCity = {
  key: string;
  city: string;
  total: number;
  noteCount: number;
  clients: RegionClient[];
};

export type RegionState = {
  key: string;
  uf: string;
  total: number;
  noteCount: number;
  cities: RegionCity[];
};

export const getRegionByUf = (uf: string) => {
  const regions: Record<string, string> = {
    AC: 'Norte',
    AL: 'Nordeste',
    AP: 'Norte',
    AM: 'Norte',
    BA: 'Nordeste',
    CE: 'Nordeste',
    DF: 'Centro-Oeste',
    ES: 'Sudeste',
    GO: 'Centro-Oeste',
    MA: 'Nordeste',
    MG: 'Sudeste',
    MS: 'Centro-Oeste',
    MT: 'Centro-Oeste',
    PA: 'Norte',
    PB: 'Nordeste',
    PE: 'Nordeste',
    PI: 'Nordeste',
    PR: 'Sul',
    RJ: 'Sudeste',
    RN: 'Nordeste',
    RO: 'Norte',
    RR: 'Norte',
    RS: 'Sul',
    SC: 'Sul',
    SE: 'Nordeste',
    SP: 'Sudeste',
    TO: 'Norte',
  };

  return regions[uf.trim().toUpperCase()] ?? 'Nao definida';
};

export const getNcmDescription = (descricaoNcm?: string | null) =>
  (descricaoNcm ?? '').trim() || 'Descricao NCM nao informada';

export const buildRegionHierarchy = (notas: NfeNotaDetalhada[]): RegionState[] => {
  const stateMap = new Map<string, RegionState>();

  for (const nota of notas) {
    const uf = (nota.destinatario_uf || 'Sem UF').trim() || 'Sem UF';
    const city = (nota.destinatario_cidade || 'Sem cidade').trim() || 'Sem cidade';
    const clientName = (nota.destinatario_nome || 'Cliente nao identificado').trim() || 'Cliente nao identificado';
    const clientDocument = (nota.destinatario_documento || 'Nao informado').trim() || 'Nao informado';
    const noteTotal = parseDecimal(nota.valor_total_nf);
    const stateKey = `estado-${uf}`;
    const cityKey = `${stateKey}-cidade-${city.toLowerCase()}`;
    const clientKey = `${cityKey}-cliente-${clientDocument}-${clientName.toLowerCase()}`;

    let stateEntry = stateMap.get(stateKey);
    if (!stateEntry) {
      stateEntry = { key: stateKey, uf, total: 0, noteCount: 0, cities: [] };
      stateMap.set(stateKey, stateEntry);
    }
    stateEntry.total += noteTotal;
    stateEntry.noteCount += 1;

    let cityEntry = stateEntry.cities.find((entry) => entry.key === cityKey);
    if (!cityEntry) {
      cityEntry = { key: cityKey, city, total: 0, noteCount: 0, clients: [] };
      stateEntry.cities.push(cityEntry);
    }
    cityEntry.total += noteTotal;
    cityEntry.noteCount += 1;

    let clientEntry = cityEntry.clients.find((entry) => entry.key === clientKey);
    if (!clientEntry) {
      clientEntry = {
        key: clientKey,
        name: clientName,
        document: clientDocument,
        total: 0,
        noteCount: 0,
        products: [],
      };
      cityEntry.clients.push(clientEntry);
    }
    clientEntry.total += noteTotal;
    clientEntry.noteCount += 1;

    for (const item of nota.itens) {
      const productDescription = (item.descricao || 'Produto nao identificado').trim() || 'Produto nao identificado';
      const productCode = (item.produto_codigo || '-').trim() || '-';
      const productKey = `${clientKey}-produto-${productCode}-${productDescription.toLowerCase()}`;

      let productEntry = clientEntry.products.find((entry) => entry.key === productKey);
        if (!productEntry) {
          productEntry = {
            key: productKey,
            code: productCode,
            description: productDescription,
            totalQuantity: 0,
            totalValue: 0,
            notesCount: 0,
            noteNumbers: [],
          };
          clientEntry.products.push(productEntry);
        }

        productEntry.totalQuantity += parseDecimal(item.quantidade);
        productEntry.totalValue += parseDecimal(item.valor_total);
        productEntry.notesCount += 1;
        if (!productEntry.noteNumbers.includes(nota.numero_nf)) {
          productEntry.noteNumbers.push(nota.numero_nf);
        }
    }
  }

  return Array.from(stateMap.values())
    .map((stateEntry) => ({
      ...stateEntry,
      cities: stateEntry.cities
        .map((cityEntry) => ({
          ...cityEntry,
          clients: cityEntry.clients
            .map((clientEntry) => ({
              ...clientEntry,
              products: [...clientEntry.products].sort((a, b) => b.totalValue - a.totalValue),
            }))
            .sort((a, b) => b.total - a.total),
        }))
        .sort((a, b) => b.total - a.total),
    }))
    .sort((a, b) => b.total - a.total);
};
