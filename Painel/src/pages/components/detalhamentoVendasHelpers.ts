import type { NfeItemDetalhado, NfeNotaDetalhada } from '@/services/nfe';
import { parseDecimal } from '@/services/nfe';

export const hierarchyLabelClass = 'text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400';

export type DetailMode = 'nota' | 'regiao' | 'fiscal';

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

export type FiscalHierarchyProduct = {
  key: string;
  code: string;
  description: string;
  totalValue: number;
  taxValue: number;
  taxPercent: number;
};

export type FiscalHierarchyNcm = {
  key: string;
  ncm: string;
  description: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  products: FiscalHierarchyProduct[];
};

export type FiscalHierarchyCity = {
  key: string;
  city: string;
  uf: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  ncms: FiscalHierarchyNcm[];
};

export type FiscalHierarchyState = {
  key: string;
  uf: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  cities: FiscalHierarchyCity[];
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

type SpedHierarchyRow = {
  estado?: string | null;
  cidade?: string | null;
  uf?: string | null;
  ncm?: string | null;
  descricao_ncm?: string | null;
  produto_codigo?: string | null;
  produto?: string | null;
  faturamento?: string | number | null;
  imposto_valor?: string | number | null;
};

const normalizeSpedCityName = (city?: string | null, uf?: string | null) => {
  const cityLabel = String(city ?? '').trim();
  const ufLabel = String(uf ?? '').trim().toUpperCase();

  if (!cityLabel) return 'Cidade nao identificada';
  if (!ufLabel) return cityLabel;

  const suffixPattern = new RegExp(`\\s[-/]\\s${ufLabel}$`, 'i');
  return cityLabel.replace(suffixPattern, '').trim() || cityLabel;
};

export const buildSpedFiscalHierarchyState = <TRow extends SpedHierarchyRow>(rows: TRow[]): FiscalHierarchyState[] => {
  const stateMap = new Map<string, FiscalHierarchyState>();

  rows.forEach((row) => {
    const uf = String(row.uf ?? row.estado ?? 'Sem UF').trim() || 'Sem UF';
    const city = normalizeSpedCityName(row.cidade, uf);
    const ncm = String(row.ncm ?? '00000000').trim() || '00000000';
    const description = String(row.descricao_ncm ?? 'NCM sem descricao').trim() || 'NCM sem descricao';
    const productCode = String(row.produto_codigo ?? 'SEM-CODIGO').trim() || 'SEM-CODIGO';
    const productDescription = String(row.produto ?? 'Produto sem descricao').trim() || 'Produto sem descricao';
    const total = parseDecimal(row.faturamento ?? 0);
    const taxValue = parseDecimal(row.imposto_valor ?? 0);

    let stateEntry = stateMap.get(uf);
    if (!stateEntry) {
      stateEntry = { key: `uf-${uf}`, uf, total: 0, taxValue: 0, taxPercent: 0, cities: [] };
      stateMap.set(uf, stateEntry);
    }
    stateEntry.total += total;
    stateEntry.taxValue += taxValue;

    let cityEntry = stateEntry.cities.find((item) => item.key === `city-${uf}-${city}`);
    if (!cityEntry) {
      cityEntry = { key: `city-${uf}-${city}`, city, uf, total: 0, taxValue: 0, taxPercent: 0, ncms: [] };
      stateEntry.cities.push(cityEntry);
    }
    cityEntry.total += total;
    cityEntry.taxValue += taxValue;

    let ncmEntry = cityEntry.ncms.find((item) => item.key === `ncm-${uf}-${city}-${ncm}`);
    if (!ncmEntry) {
      ncmEntry = { key: `ncm-${uf}-${city}-${ncm}`, ncm, description, total: 0, taxValue: 0, taxPercent: 0, products: [] };
      cityEntry.ncms.push(ncmEntry);
    }
    ncmEntry.total += total;
    ncmEntry.taxValue += taxValue;

    let productEntry = ncmEntry.products.find((item) => item.code === productCode);
    if (!productEntry) {
      productEntry = { key: `product-${uf}-${city}-${ncm}-${productCode}`, code: productCode, description: productDescription, totalValue: 0, taxValue: 0, taxPercent: 0 };
      ncmEntry.products.push(productEntry);
    }

    productEntry.totalValue += total;
    productEntry.taxValue += taxValue;
  });

  return [...stateMap.values()].map((stateEntry) => ({
    ...stateEntry,
    taxPercent: stateEntry.total ? (stateEntry.taxValue / stateEntry.total) * 100 : 0,
    cities: stateEntry.cities.map((cityEntry) => ({
      ...cityEntry,
      taxPercent: cityEntry.total ? (cityEntry.taxValue / cityEntry.total) * 100 : 0,
      ncms: cityEntry.ncms.map((ncmEntry) => ({
        ...ncmEntry,
        taxPercent: ncmEntry.total ? (ncmEntry.taxValue / ncmEntry.total) * 100 : 0,
        products: [...ncmEntry.products].map((productEntry) => ({
          ...productEntry,
          taxPercent: productEntry.totalValue ? (productEntry.taxValue / productEntry.totalValue) * 100 : 0,
        })).sort((a, b) => b.totalValue - a.totalValue),
      })).sort((a, b) => b.total - a.total),
    })).sort((a, b) => b.total - a.total),
  })).sort((a, b) => b.total - a.total);
};

const normalizeSearchValue = (value: string | number | null | undefined) =>
  String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();

const includesSearch = (values: Array<string | number | null | undefined>, query: string) =>
  values.some((value) => normalizeSearchValue(value).includes(query));

const noteMatchesSearch = (nota: NfeNotaDetalhada, query: string) =>
  includesSearch(
    [
      nota.numero_nf,
      nota.data_emissao,
      nota.modelo,
      nota.natureza_operacao,
      nota.destinatario_nome,
      nota.destinatario_documento,
      nota.destinatario_cidade,
      nota.destinatario_uf,
      getRegionByUf(nota.destinatario_uf || ''),
    ],
    query,
  );

const itemMatchesSearch = (item: NfeItemDetalhado, query: string) =>
  includesSearch(
    [
      item.produto_codigo,
      item.descricao,
      item.ncm,
      item.descricao_ncm,
      item.cfop,
      item.quantidade,
      item.valor_total,
    ],
    query,
  );

export const filterNotasBySearch = (notas: NfeNotaDetalhada[], search: string) => {
  const query = normalizeSearchValue(search);
  if (!query) return notas;

  return notas.reduce<NfeNotaDetalhada[]>((filtered, nota) => {
    if (noteMatchesSearch(nota, query)) {
      filtered.push(nota);
      return filtered;
    }

    const filteredItems = nota.itens.filter((item) => itemMatchesSearch(item, query));
    if (filteredItems.length > 0) {
      filtered.push({ ...nota, itens: filteredItems });
    }

    return filtered;
  }, []);
};

const buildFilteredClient = (client: RegionClient, products: RegionProduct[]): RegionClient => {
  const total = products.reduce((sum, product) => sum + product.totalValue, 0);
  const noteCount = new Set(products.flatMap((product) => product.noteNumbers)).size;

  return {
    ...client,
    total,
    noteCount,
    products,
  };
};

const buildFilteredCity = (city: RegionCity, clients: RegionClient[]): RegionCity => ({
  ...city,
  total: clients.reduce((sum, client) => sum + client.total, 0),
  noteCount: clients.reduce((sum, client) => sum + client.noteCount, 0),
  clients,
});

const buildFilteredState = (state: RegionState, cities: RegionCity[]): RegionState => ({
  ...state,
  total: cities.reduce((sum, city) => sum + city.total, 0),
  noteCount: cities.reduce((sum, city) => sum + city.noteCount, 0),
  cities,
});

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

export const filterRegionHierarchyBySearch = (regionHierarchy: RegionState[], search: string) => {
  const query = normalizeSearchValue(search);
  if (!query) return regionHierarchy;

  return regionHierarchy.reduce<RegionState[]>((filteredStates, stateEntry) => {
    const stateMatches = includesSearch([stateEntry.uf, getRegionByUf(stateEntry.uf)], query);

    if (stateMatches) {
      filteredStates.push(stateEntry);
      return filteredStates;
    }

    const filteredCities = stateEntry.cities.reduce<RegionCity[]>((cities, cityEntry) => {
      const cityMatches = includesSearch([cityEntry.city, stateEntry.uf, getRegionByUf(stateEntry.uf)], query);

      if (cityMatches) {
        cities.push(cityEntry);
        return cities;
      }

      const filteredClients = cityEntry.clients.reduce<RegionClient[]>((clients, clientEntry) => {
        const clientMatches = includesSearch([clientEntry.name, clientEntry.document], query);

        if (clientMatches) {
          clients.push(clientEntry);
          return clients;
        }

        const filteredProducts = clientEntry.products.filter((productEntry) =>
          includesSearch(
            [productEntry.code, productEntry.description, productEntry.noteNumbers.join(', '), productEntry.totalQuantity],
            query,
          ),
        );

        if (filteredProducts.length > 0) {
          clients.push(buildFilteredClient(clientEntry, filteredProducts));
        }

        return clients;
      }, []);

      if (filteredClients.length > 0) {
        cities.push(buildFilteredCity(cityEntry, filteredClients));
      }

      return cities;
    }, []);

    if (filteredCities.length > 0) {
      filteredStates.push(buildFilteredState(stateEntry, filteredCities));
    }

    return filteredStates;
  }, []);
};
