import { useEffect, useMemo, useRef, useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { parseDecimal, type AnaliseFiscalHierarquicaResponse as NfeAnaliseFiscalHierarquicaResponse } from '@/services/nfe';
import { type AnaliseFiscalHierarquicaResponse as SpedAnaliseFiscalHierarquicaResponse } from '@/services/sped';
import { formatCurrency } from '@/services/utils';
import { getRegionByUf, hierarchyLabelClass } from './detalhamentoVendasHelpers';

type HierarquiaResponse = NfeAnaliseFiscalHierarquicaResponse | SpedAnaliseFiscalHierarquicaResponse;
type FiscalHierarchyFetcher = (
  params: {
    emitente_cnpj?: string;
    email?: string;
    periodo_ano?: number;
    periodo_mes?: number;
    nivel_atual?: string;
    estado?: string;
    cidade?: string;
    ncm?: string;
    produto_codigo?: string;
    limite?: number;
    offset?: number;
  },
) => Promise<HierarquiaResponse>;

type EstadoItem = HierarquiaResponse['por_estado'][number];
type CidadeItem = HierarquiaResponse['por_cidade'][number];
type NcmItem = HierarquiaResponse['por_ncm'][number];
type ProdutoItem = HierarquiaResponse['por_produto'][number];

type BaseParams = {
  emitente_cnpj?: string;
  email?: string;
  periodo_ano?: number;
  periodo_mes?: number;
};

type LegacyFiscalHierarchyProduct = {
  key: string;
  code: string;
  description: string;
  totalValue: number;
  taxValue: number;
  taxPercent: number;
};

type LegacyFiscalHierarchyNcm = {
  key: string;
  ncm: string;
  description: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  products: LegacyFiscalHierarchyProduct[];
};

type LegacyFiscalHierarchyCity = {
  key: string;
  city: string;
  uf: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  ncms: LegacyFiscalHierarchyNcm[];
};

type LegacyFiscalHierarchyState = {
  key: string;
  uf: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  cities: LegacyFiscalHierarchyCity[];
};

type LazyProps = {
  fetchHierarchy: FiscalHierarchyFetcher;
  baseParams: BaseParams;
  states: EstadoItem[];
  searchTerm: string;
};

type LegacyProps = {
  hierarchy: LegacyFiscalHierarchyState[];
  openStateValues: string[];
  onOpenStateValuesChange: (values: string[]) => void;
  openCityValues: string[];
  onOpenCityValuesChange: (values: string[]) => void;
  openNcmValues: string[];
  onOpenNcmValuesChange: (values: string[]) => void;
};

type Props = LazyProps | LegacyProps;

const normalizeSearchValue = (value: string | number | null | undefined) =>
  String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();

const matchesSearch = (values: Array<string | number | null | undefined>, query: string) =>
  values.some((value) => normalizeSearchValue(value).includes(query));

function ProductSection({
  fetchHierarchy,
  baseParams,
  estado,
  cidade,
  ncm,
  searchTerm,
}: {
  fetchHierarchy: FiscalHierarchyFetcher;
  baseParams: BaseParams;
  estado: string;
  cidade: string;
  ncm: string;
  searchTerm: string;
}) {
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const productsQuery = useInfiniteQuery({
    queryKey: ['analise-fiscal-products', baseParams.emitente_cnpj, baseParams.email, baseParams.periodo_ano, baseParams.periodo_mes, estado, cidade, ncm],
    queryFn: ({ pageParam = 0 }) => fetchHierarchy({
        ...baseParams,
        nivel_atual: 'produto',
        estado,
        cidade,
        ncm,
        limite: 100,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.possui_mais_registros ? lastPage.offset + lastPage.limite : undefined,
    staleTime: 5 * 60 * 1000,
  });

  const allProducts = useMemo(
    () => productsQuery.data?.pages.flatMap((page) => page.por_produto) ?? [],
    [productsQuery.data?.pages],
  );
  const query = normalizeSearchValue(searchTerm);
  const products = query
    ? allProducts.filter((item) => matchesSearch([item.produto_codigo, item.produto, item.faturamento, item.imposto_valor], query))
    : allProducts;

  const totalProducts = productsQuery.data?.pages[0]?.total_registros_nivel ?? 0;
  const loadedProducts = allProducts.length;

  useEffect(() => {
    const sentinel = loadMoreRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver((entries) => {
      if (!entries[0]?.isIntersecting) return;

      if (productsQuery.hasNextPage && !productsQuery.isFetchingNextPage) {
        productsQuery.fetchNextPage();
      }
    }, { rootMargin: '220px 0px' });

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [productsQuery]);

  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/85">
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/70 px-4 py-3 text-xs text-slate-400">
          <span>Exibindo {products.length} de {loadedProducts} produtos carregados</span>
          <span>{totalProducts} produtos no total</span>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="border-slate-800 bg-slate-950/80 hover:bg-slate-950/80">
              <TableHead className="text-slate-300">Cod do produto</TableHead>
              <TableHead className="text-slate-300">Nome do produto</TableHead>
              <TableHead className="text-right text-slate-300">Faturamento</TableHead>
              <TableHead className="text-right text-slate-300">Imposto (R$)</TableHead>
              <TableHead className="text-right text-slate-300">Imposto (%)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {productsQuery.isLoading && (
              <TableRow className="border-slate-800">
                <TableCell colSpan={5} className="py-8 text-center text-slate-400">Carregando produtos...</TableCell>
              </TableRow>
            )}
            {!productsQuery.isLoading && products.length === 0 && (
              <TableRow className="border-slate-800">
                <TableCell colSpan={5} className="py-8 text-center text-slate-400">
                  {query ? 'Nenhum produto encontrado nos produtos carregados.' : 'Nenhum produto encontrado para este NCM.'}
                </TableCell>
              </TableRow>
            )}
            {products.map((productEntry) => (
              <TableRow key={`${productEntry.produto_codigo}-${productEntry.produto}`} id={`product-row-${estado}-${cidade}-${ncm}-${productEntry.produto_codigo}`} className="border-slate-800 hover:bg-slate-800/55">
                <TableCell className="font-medium text-slate-100">{productEntry.produto_codigo}</TableCell>
                <TableCell className="text-slate-200">{productEntry.produto}</TableCell>
                <TableCell className="text-right font-medium text-slate-100">{formatCurrency(parseDecimal(productEntry.faturamento))}</TableCell>
                <TableCell className="text-right text-slate-300">{formatCurrency(parseDecimal(productEntry.imposto_valor))}</TableCell>
                <TableCell className="text-right text-slate-300">{parseDecimal(productEntry.imposto_percentual).toFixed(2)}%</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-xs text-slate-400">
        <span>A lista carrega mais 100 produtos conforme a rolagem.</span>
        <span>{productsQuery.isFetchingNextPage ? 'Carregando mais 100 produtos...' : productsQuery.hasNextPage ? 'Role para baixo para carregar o proximo bloco.' : 'Todos os produtos carregados.'}</span>
      </div>

      <div ref={loadMoreRef} className="h-4 w-full" />
    </div>
  );
}

function NcmSection({
  fetchHierarchy,
  baseParams,
  estado,
  cidade,
  searchTerm,
  openNcmValues,
  onOpenNcmValuesChange,
  registerNcmKeys,
}: {
  fetchHierarchy: FiscalHierarchyFetcher;
  baseParams: BaseParams;
  estado: string;
  cidade: string;
  searchTerm: string;
  openNcmValues: string[];
  onOpenNcmValuesChange: (values: string[]) => void;
  registerNcmKeys: (ownerKey: string, keys: string[]) => void;
}) {
  const ownerKey = `${estado}::${cidade}`;
  const ncmQuery = useQuery({
    queryKey: ['analise-fiscal-ncms', baseParams.emitente_cnpj, baseParams.email, baseParams.periodo_ano, baseParams.periodo_mes, estado, cidade],
    queryFn: () => fetchHierarchy({ ...baseParams, nivel_atual: 'ncm', estado, cidade, limite: 500 }),
    staleTime: 5 * 60 * 1000,
  });

  const query = normalizeSearchValue(searchTerm);
  const ncms = useMemo(() => {
    const items = ncmQuery.data?.por_ncm ?? [];
    return query
      ? items.filter((item) => matchesSearch([item.ncm, item.descricao, item.faturamento, item.imposto_valor], query))
      : items;
  }, [ncmQuery.data?.por_ncm, query]);

  useEffect(() => {
    registerNcmKeys(ownerKey, ncms.map((item) => `ncm-${estado}-${cidade}-${item.ncm}`));
  }, [cidade, estado, ncms, ownerKey, registerNcmKeys]);

  if (ncmQuery.isLoading) {
    return <div className="py-4 text-sm text-slate-400">Carregando NCMs...</div>;
  }

  return (
    <Accordion type="multiple" value={openNcmValues} onValueChange={onOpenNcmValuesChange} className="w-full">
      {ncms.map((ncmEntry) => {
        const itemKey = `ncm-${estado}-${cidade}-${ncmEntry.ncm}`;
        return (
          <AccordionItem key={itemKey} value={itemKey} className="mt-3 rounded-2xl border border-slate-800 bg-slate-950/80 px-4">
            <AccordionTrigger className="py-4 hover:no-underline">
              <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-[minmax(0,1.1fr)_160px_180px_180px] md:items-start">
                <div className="min-w-0">
                  <p className={hierarchyLabelClass}>NCM</p>
                  <p className="mt-1 whitespace-normal break-words text-sm font-medium leading-relaxed text-slate-100">{ncmEntry.ncm}</p>
                  <p className="mt-1 text-xs text-slate-400">{ncmEntry.descricao}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Produtos</p>
                  <p className="mt-1 text-sm text-slate-300">{ncmEntry.quantidade_produtos ?? 0}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Imposto estimado</p>
                  <p className="mt-1 text-sm text-slate-300">{formatCurrency(parseDecimal(ncmEntry.imposto_valor))}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Faturamento</p>
                  <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(parseDecimal(ncmEntry.faturamento))}</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-4">
              <ProductSection fetchHierarchy={fetchHierarchy} baseParams={baseParams} estado={estado} cidade={cidade} ncm={ncmEntry.ncm} searchTerm={searchTerm} />
            </AccordionContent>
          </AccordionItem>
        );
      })}
      {!ncms.length && <div className="py-4 text-sm text-slate-400">{query ? 'Nenhum NCM encontrado para a busca aplicada.' : 'Nenhum NCM encontrado para esta cidade.'}</div>}
    </Accordion>
  );
}

function CitySection({
  fetchHierarchy,
  baseParams,
  estado,
  searchTerm,
  openCityValues,
  onOpenCityValuesChange,
  openNcmValues,
  onOpenNcmValuesChange,
  registerCityKeys,
  registerNcmKeys,
}: {
  fetchHierarchy: FiscalHierarchyFetcher;
  baseParams: BaseParams;
  estado: string;
  searchTerm: string;
  openCityValues: string[];
  onOpenCityValuesChange: (values: string[]) => void;
  openNcmValues: string[];
  onOpenNcmValuesChange: (values: string[]) => void;
  registerCityKeys: (ownerKey: string, keys: string[]) => void;
  registerNcmKeys: (ownerKey: string, keys: string[]) => void;
}) {
  const cityQuery = useQuery({
    queryKey: ['analise-fiscal-cidades', baseParams.emitente_cnpj, baseParams.email, baseParams.periodo_ano, baseParams.periodo_mes, estado],
    queryFn: () => fetchHierarchy({ ...baseParams, nivel_atual: 'cidade', estado, limite: 300 }),
    staleTime: 5 * 60 * 1000,
  });

  const query = normalizeSearchValue(searchTerm);
  const cities = useMemo(() => {
    const items = cityQuery.data?.por_cidade ?? [];
    return query
      ? items.filter((item) => matchesSearch([item.cidade, item.uf, item.faturamento, item.imposto_valor], query))
      : items;
  }, [cityQuery.data?.por_cidade, query]);

  useEffect(() => {
    registerCityKeys(estado, cities.map((item) => `city-${estado}-${item.cidade}`));
  }, [cities, estado, registerCityKeys]);

  if (cityQuery.isLoading) {
    return <div className="py-4 text-sm text-slate-400">Carregando cidades...</div>;
  }

  return (
    <Accordion type="multiple" value={openCityValues} onValueChange={onOpenCityValuesChange} className="w-full">
      {cities.map((cityEntry) => {
        const itemKey = `city-${estado}-${cityEntry.cidade}`;
        return (
          <AccordionItem key={itemKey} value={itemKey} className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/75 px-4">
            <AccordionTrigger className="py-4 hover:no-underline">
              <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-4">
                <div>
                  <p className={hierarchyLabelClass}>Cidade</p>
                  <p className="mt-1 text-sm font-medium text-slate-100">{cityEntry.cidade}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>UF</p>
                  <p className="mt-1 text-sm text-slate-300">{cityEntry.uf}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Imposto estimado</p>
                  <p className="mt-1 text-sm text-slate-300">{formatCurrency(parseDecimal(cityEntry.imposto_valor))}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Faturamento</p>
                  <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(parseDecimal(cityEntry.faturamento))}</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-4">
              <NcmSection
                fetchHierarchy={fetchHierarchy}
                baseParams={baseParams}
                estado={estado}
                cidade={cityEntry.cidade}
                searchTerm={searchTerm}
                openNcmValues={openNcmValues}
                onOpenNcmValuesChange={onOpenNcmValuesChange}
                registerNcmKeys={registerNcmKeys}
              />
            </AccordionContent>
          </AccordionItem>
        );
      })}
      {!cities.length && <div className="py-4 text-sm text-slate-400">{query ? 'Nenhuma cidade encontrada para a busca aplicada.' : 'Nenhuma cidade encontrada para este estado.'}</div>}
    </Accordion>
  );
}

export function DetalhamentoFiscalHierarquiaMode(props: Props) {
  if ('hierarchy' in props) {
    const {
      hierarchy,
      openStateValues,
      onOpenStateValuesChange,
      openCityValues,
      onOpenCityValuesChange,
      openNcmValues,
      onOpenNcmValuesChange,
    } = props;

    return (
      <Accordion type="multiple" value={openStateValues} onValueChange={onOpenStateValuesChange} className="w-full">
        {hierarchy.map((stateEntry) => (
          <AccordionItem key={stateEntry.key} value={stateEntry.key} className="border-b border-slate-800/80">
            <AccordionTrigger className="px-6 py-5 hover:no-underline">
              <div className="grid w-full gap-3 text-left md:grid-cols-4 md:items-center">
                <div>
                  <p className={hierarchyLabelClass}>Estado</p>
                  <p className="text-base font-semibold text-white">{stateEntry.uf}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Regiao</p>
                  <p className="text-sm text-slate-300">{getRegionByUf(stateEntry.uf)}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Imposto estimado</p>
                  <p className="text-sm text-slate-300">{formatCurrency(stateEntry.taxValue)}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Faturamento</p>
                  <p className="text-base font-semibold text-white">{formatCurrency(stateEntry.total)}</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-6 pb-6">
              <Accordion type="multiple" value={openCityValues} onValueChange={onOpenCityValuesChange} className="w-full">
                {stateEntry.cities.map((cityEntry) => (
                  <AccordionItem key={cityEntry.key} value={cityEntry.key} className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/75 px-4">
                    <AccordionTrigger className="py-4 hover:no-underline">
                      <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-4">
                        <div>
                          <p className={hierarchyLabelClass}>Cidade</p>
                          <p className="mt-1 text-sm font-medium text-slate-100">{cityEntry.city}</p>
                        </div>
                        <div>
                          <p className={hierarchyLabelClass}>NCMs</p>
                          <p className="mt-1 text-sm text-slate-300">{cityEntry.ncms.length}</p>
                        </div>
                        <div>
                          <p className={hierarchyLabelClass}>Imposto estimado</p>
                          <p className="mt-1 text-sm text-slate-300">{formatCurrency(cityEntry.taxValue)}</p>
                        </div>
                        <div>
                          <p className={hierarchyLabelClass}>Faturamento</p>
                          <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(cityEntry.total)}</p>
                        </div>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="pb-4">
                      <Accordion type="multiple" value={openNcmValues} onValueChange={onOpenNcmValuesChange} className="w-full">
                        {cityEntry.ncms.map((ncmEntry) => (
                          <AccordionItem key={ncmEntry.key} value={ncmEntry.key} className="mt-3 rounded-2xl border border-slate-800 bg-slate-950/80 px-4">
                            <AccordionTrigger className="py-4 hover:no-underline">
                              <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-[minmax(0,1.1fr)_160px_180px_180px] md:items-start">
                                <div className="min-w-0">
                                  <p className={hierarchyLabelClass}>NCM</p>
                                  <p className="mt-1 whitespace-normal break-words text-sm font-medium leading-relaxed text-slate-100">{ncmEntry.ncm}</p>
                                  <p className="mt-1 text-xs text-slate-400">{ncmEntry.description}</p>
                                </div>
                                <div>
                                  <p className={hierarchyLabelClass}>Produtos</p>
                                  <p className="mt-1 text-sm text-slate-300">{ncmEntry.products.length}</p>
                                </div>
                                <div>
                                  <p className={hierarchyLabelClass}>Imposto estimado</p>
                                  <p className="mt-1 text-sm text-slate-300">{formatCurrency(ncmEntry.taxValue)}</p>
                                </div>
                                <div>
                                  <p className={hierarchyLabelClass}>Faturamento</p>
                                  <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(ncmEntry.total)}</p>
                                </div>
                              </div>
                            </AccordionTrigger>
                            <AccordionContent className="pb-4">
                              <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/85">
                                <Table>
                                  <TableHeader>
                                    <TableRow className="border-slate-800 bg-slate-950/80 hover:bg-slate-950/80">
                                      <TableHead className="text-slate-300">Cod do produto</TableHead>
                                      <TableHead className="text-slate-300">Nome do produto</TableHead>
                                      <TableHead className="text-right text-slate-300">Faturamento</TableHead>
                                      <TableHead className="text-right text-slate-300">Imposto (R$)</TableHead>
                                      <TableHead className="text-right text-slate-300">Imposto (%)</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {ncmEntry.products.map((productEntry) => (
                                      <TableRow key={productEntry.key} className="border-slate-800 hover:bg-slate-800/55">
                                        <TableCell className="font-medium text-slate-100">{productEntry.code}</TableCell>
                                        <TableCell className="text-slate-200">{productEntry.description}</TableCell>
                                        <TableCell className="text-right font-medium text-slate-100">{formatCurrency(productEntry.totalValue)}</TableCell>
                                        <TableCell className="text-right text-slate-300">{formatCurrency(productEntry.taxValue)}</TableCell>
                                        <TableCell className="text-right text-slate-300">{productEntry.taxPercent.toFixed(2)}%</TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        ))}
                      </Accordion>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    );
  }

  const {
    fetchHierarchy,
    baseParams,
    states,
    searchTerm,
  } = props;

  const [openStateValues, setOpenStateValues] = useState<string[]>([]);
  const [openCityValues, setOpenCityValues] = useState<string[]>([]);
  const [openNcmValues, setOpenNcmValues] = useState<string[]>([]);
  const [cityKeysByState, setCityKeysByState] = useState<Record<string, string[]>>({});
  const [ncmKeysByCity, setNcmKeysByCity] = useState<Record<string, string[]>>({});

  useEffect(() => {
    setOpenStateValues([]);
    setOpenCityValues([]);
    setOpenNcmValues([]);
    setCityKeysByState({});
    setNcmKeysByCity({});
  }, [baseParams.emitente_cnpj, baseParams.email, baseParams.periodo_ano, baseParams.periodo_mes, searchTerm]);

  const query = normalizeSearchValue(searchTerm);
  const filteredStates = useMemo(() => (
    query
      ? states.filter((item) => matchesSearch([item.estado, item.faturamento, item.imposto_valor], query))
      : states
  ), [query, states]);

  const stateAccordionValues = useMemo(() => filteredStates.map((item) => `uf-${item.estado}`), [filteredStates]);
  const cityAccordionValues = useMemo(() => Object.values(cityKeysByState).flat(), [cityKeysByState]);
  const ncmAccordionValues = useMemo(() => Object.values(ncmKeysByCity).flat(), [ncmKeysByCity]);

  useEffect(() => {
    setOpenStateValues((current) => current.filter((value) => stateAccordionValues.includes(value)));
  }, [stateAccordionValues]);

  useEffect(() => {
    setOpenCityValues((current) => current.filter((value) => cityAccordionValues.includes(value)));
  }, [cityAccordionValues]);

  useEffect(() => {
    setOpenNcmValues((current) => current.filter((value) => ncmAccordionValues.includes(value)));
  }, [ncmAccordionValues]);

  const allStatesOpen = stateAccordionValues.length > 0 && stateAccordionValues.every((value) => openStateValues.includes(value));
  const allCitiesOpen = cityAccordionValues.length > 0 && cityAccordionValues.every((value) => openCityValues.includes(value));
  const allNcmsOpen = ncmAccordionValues.length > 0 && ncmAccordionValues.every((value) => openNcmValues.includes(value));

  const registerCityKeys = (ownerKey: string, keys: string[]) => {
    setCityKeysByState((current) => ({ ...current, [ownerKey]: keys }));
  };

  const registerNcmKeys = (ownerKey: string, keys: string[]) => {
    setNcmKeysByCity((current) => ({ ...current, [ownerKey]: keys }));
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3 px-6 pt-4">
        <Button type="button" variant="outline" onClick={() => setOpenStateValues(allStatesOpen ? [] : stateAccordionValues)} className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800">Estado</Button>
        <Button type="button" variant="outline" onClick={() => { if (allCitiesOpen) { setOpenCityValues([]); return; } setOpenStateValues(stateAccordionValues); setOpenCityValues(cityAccordionValues); }} className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800">Cidade</Button>
        <Button type="button" variant="outline" onClick={() => { if (allNcmsOpen) { setOpenNcmValues([]); return; } setOpenStateValues(stateAccordionValues); setOpenCityValues(cityAccordionValues); setOpenNcmValues(ncmAccordionValues); }} className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800">NCM</Button>
        <Button type="button" variant="outline" onClick={() => { setOpenStateValues(stateAccordionValues); setOpenCityValues(cityAccordionValues); setOpenNcmValues(ncmAccordionValues); }} className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800">Produto</Button>
      </div>

      <Accordion type="multiple" value={openStateValues} onValueChange={setOpenStateValues} className="w-full">
        {filteredStates.map((stateEntry) => {
          const itemKey = `uf-${stateEntry.estado}`;
          return (
            <AccordionItem key={itemKey} value={itemKey} className="border-b border-slate-800/80">
              <AccordionTrigger className="px-6 py-5 hover:no-underline">
                <div className="grid w-full gap-3 text-left md:grid-cols-4 md:items-center">
                  <div>
                    <p className={hierarchyLabelClass}>Estado</p>
                    <p className="text-base font-semibold text-white">{stateEntry.estado}</p>
                  </div>
                  <div>
                    <p className={hierarchyLabelClass}>Regiao</p>
                    <p className="text-sm text-slate-300">{getRegionByUf(stateEntry.estado)}</p>
                  </div>
                  <div>
                    <p className={hierarchyLabelClass}>Imposto estimado</p>
                    <p className="text-sm text-slate-300">{formatCurrency(parseDecimal(stateEntry.imposto_valor))}</p>
                  </div>
                  <div>
                    <p className={hierarchyLabelClass}>Faturamento</p>
                    <p className="text-base font-semibold text-white">{formatCurrency(parseDecimal(stateEntry.faturamento))}</p>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-6 pb-6">
                <CitySection
                  fetchHierarchy={fetchHierarchy}
                  baseParams={baseParams}
                  estado={stateEntry.estado}
                  searchTerm={searchTerm}
                  openCityValues={openCityValues}
                  onOpenCityValuesChange={setOpenCityValues}
                  openNcmValues={openNcmValues}
                  onOpenNcmValuesChange={setOpenNcmValues}
                  registerCityKeys={registerCityKeys}
                  registerNcmKeys={registerNcmKeys}
                />
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}
