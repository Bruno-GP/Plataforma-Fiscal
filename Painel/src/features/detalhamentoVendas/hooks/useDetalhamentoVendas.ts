import { useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, RefObject, SetStateAction } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { Percent, TrendingDown, TrendingUp, Users } from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';
import { useFiscalYears } from '@/hooks/useFiscalYears';
import { usePeriodFilter } from '@/hooks/usePeriodFilter';
import { useDashboardVendasQueries } from '@/hooks/useDashboardQueries';
import { fetchNfeNotasDetalhadas } from '@/services/nfe';
import {
  fetchSpedAnaliseFiscalHierarquica,
  type AnaliseFiscalHierarquicaResponse as SpedFiscalHierarchyResponse,
} from '@/services/sped';
import { createFiscalSourceApi } from '@/services/fiscalSource';
import { createFiscalPeriod, createFiscalQueryKey } from '@/utils/fiscalPeriod';
import {
  calculateChange,
  formatCurrency,
  formatPercent,
  hasValidEmitenteCnpj,
  monthLabels,
  parseDecimal,
} from '@/utils/formatters';

import type { DetailLevelButton, DetailMode, DetailModeOption, DetailStat } from '../types';
import {
  buildLevelButtons,
  buildRegionHierarchy,
  buildSpedFiscalHierarchyState,
  buildSpedFiscalNcmHierarchy,
  filterNotasBySearch,
  filterRegionHierarchyBySearch,
  filterSpedHierarchyRows,
  getDetailModeOptions,
  getDetailSummaryText,
  getDetailScopeLabel,
  getEmptyDetailMessage,
  getSearchPlaceholder,
} from '../helpers/detalhamentoVendasHelpers';

const NOTAS_PAGE_SIZE = 100;

export type UseDetalhamentoVendasResult = {
  selectedMonth: string;
  setSelectedMonth: (value: string) => void;
  selectedYear: string;
  setSelectedYear: (value: string) => void;
  availableYears: number[];
  monthLabels: string[];
  viewMode: 'grafica' | 'detalhada';
  setViewMode: (value: 'grafica' | 'detalhada') => void;
  detailMode: DetailMode;
  setDetailMode: (value: DetailMode) => void;
  isSped: boolean;
  modeOptions?: DetailModeOption[];
  stats: readonly DetailStat[];
  dashboardQuery: ReturnType<typeof useDashboardVendasQueries>['dashboardQuery'];
  mapQuery: ReturnType<typeof useDashboardVendasQueries>['mapQuery'];
  searchTerm: string;
  setSearchTerm: (value: string) => void;
  searchPlaceholder: string;
  levelButtons: DetailLevelButton[];
  activeHasResults: boolean;
  isDetalhamentoLoading: boolean;
  detalhamentoError: unknown;
  notasTotal: number;
  detailScopeLabel: string;
  detailSummaryText: string;
  emptyDetailMessage: string;
  notasInfiniteQuery: ReturnType<typeof useInfiniteQuery>;
  loadMoreRef: RefObject<HTMLDivElement | null>;
  filteredNotas: ReturnType<typeof filterNotasBySearch>;
  filteredRegionHierarchy: ReturnType<typeof filterRegionHierarchyBySearch>;
  spedFiscalHierarchy: ReturnType<typeof buildSpedFiscalNcmHierarchy>;
  spedRegionHierarchy: ReturnType<typeof buildSpedFiscalHierarchyState>;
  filteredSpedRows: ReturnType<typeof filterSpedHierarchyRows>;
  openNoteValues: string[];
  setOpenNoteValues: Dispatch<SetStateAction<string[]>>;
  openNoteClientValues: string[];
  setOpenNoteClientValues: Dispatch<SetStateAction<string[]>>;
  openNcmValues: string[];
  setOpenNcmValues: Dispatch<SetStateAction<string[]>>;
  openRegionStateValues: string[];
  setOpenRegionStateValues: Dispatch<SetStateAction<string[]>>;
  openRegionCityValues: string[];
  setOpenRegionCityValues: Dispatch<SetStateAction<string[]>>;
  openRegionClientValues: string[];
  setOpenRegionClientValues: Dispatch<SetStateAction<string[]>>;
  openSpedRegionStateValues: string[];
  setOpenSpedRegionStateValues: Dispatch<SetStateAction<string[]>>;
  openSpedRegionCityValues: string[];
  setOpenSpedRegionCityValues: Dispatch<SetStateAction<string[]>>;
  openSpedRegionNcmValues: string[];
  setOpenSpedRegionNcmValues: Dispatch<SetStateAction<string[]>>;
  openFiscalNcmValues: string[];
  setOpenFiscalNcmValues: Dispatch<SetStateAction<string[]>>;
};

export function useDetalhamentoVendas(): UseDetalhamentoVendasResult {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const isSped = Boolean(user?.tem_sped);
  const fiscalApi = createFiscalSourceApi(user);

  const { selectedMonth, setSelectedMonth, selectedYear, setSelectedYear, monthNumber, year: yearNumber } = usePeriodFilter();
  const fiscalPeriod = useMemo(
    () => createFiscalPeriod(selectedYear, selectedMonth),
    [selectedMonth, selectedYear],
  );
  const [viewMode, setViewMode] = useState<'grafica' | 'detalhada'>('grafica');
  const [detailMode, setDetailMode] = useState<DetailMode>(isSped ? 'regiao' : 'nota');

  const yearsQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'detalhamento-vendas-anos',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
    }),
    queryFn: () => fiscalApi.kpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const dashboardSelectedMonth = viewMode === 'grafica' ? 'all' : selectedMonth;
  const { dashboardQuery, mapQuery } = useDashboardVendasQueries({
    emitenteCnpj,
    email: user?.email,
    temSped: user,
    year: yearNumber,
    selectedMonth: dashboardSelectedMonth,
    monthNumber,
    hasEmitenteCnpj,
  });

  const [openNoteValues, setOpenNoteValues] = useState<string[]>([]);
  const [openNoteClientValues, setOpenNoteClientValues] = useState<string[]>([]);
  const [openNcmValues, setOpenNcmValues] = useState<string[]>([]);
  const [openRegionStateValues, setOpenRegionStateValues] = useState<string[]>([]);
  const [openRegionCityValues, setOpenRegionCityValues] = useState<string[]>([]);
  const [openRegionClientValues, setOpenRegionClientValues] = useState<string[]>([]);
  const [openSpedRegionStateValues, setOpenSpedRegionStateValues] = useState<string[]>([]);
  const [openSpedRegionCityValues, setOpenSpedRegionCityValues] = useState<string[]>([]);
  const [openSpedRegionNcmValues, setOpenSpedRegionNcmValues] = useState<string[]>([]);
  const [openFiscalNcmValues, setOpenFiscalNcmValues] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isSped && detailMode === 'nota') setDetailMode('regiao');
  }, [detailMode, isSped]);

  const notasInfiniteQuery = useInfiniteQuery({
    queryKey: createFiscalQueryKey({
      scope: 'detalhamento-vendas-notas',
      emitenteCnpj,
      sourceKey: 'nfe',
      period: fiscalPeriod,
    }),
    queryFn: ({ pageParam = 0 }) =>
      fetchNfeNotasDetalhadas({
        emitente_cnpj: emitenteCnpj,
        email: user?.email,
        ...fiscalPeriod.params,
        tipo_operacao: 'vendas',
        limite: NOTAS_PAGE_SIZE,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loadedCount = allPages.reduce((total, page) => total + page.notas.length, 0);
      return loadedCount < lastPage.total ? loadedCount : undefined;
    },
    enabled: hasEmitenteCnpj && !isSped && viewMode === 'detalhada' && detailMode === 'nota',
    staleTime: 5 * 60 * 1000,
  });

  const notasRegionQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'detalhamento-vendas-notas-regiao',
      emitenteCnpj,
      sourceKey: 'nfe',
      period: fiscalPeriod,
    }),
    queryFn: () =>
      fetchNfeNotasDetalhadas({
        emitente_cnpj: emitenteCnpj,
        email: user?.email,
        ...fiscalPeriod.params,
        tipo_operacao: 'vendas',
        limite: 500,
        offset: 0,
      }).then(async (firstPage) => {
        if (firstPage.total <= firstPage.notas.length) return firstPage;

        let offset = firstPage.notas.length;
        const notas = [...firstPage.notas];
        while (offset < firstPage.total) {
          const nextPage = await fetchNfeNotasDetalhadas({
            emitente_cnpj: emitenteCnpj,
            email: user?.email,
            ...fiscalPeriod.params,
            tipo_operacao: 'vendas',
            limite: 500,
            offset,
          });
          notas.push(...nextPage.notas);
          offset += nextPage.notas.length;
          if (nextPage.notas.length === 0) break;
        }

        return { status: firstPage.status, total: firstPage.total, notas };
      }),
    enabled: hasEmitenteCnpj && !isSped && viewMode === 'detalhada' && detailMode === 'regiao',
    staleTime: 5 * 60 * 1000,
  });

  const spedHierarchyQuery = useQuery<SpedFiscalHierarchyResponse>({
    queryKey: createFiscalQueryKey({
      scope: 'detalhamento-vendas-sped-hierarquia',
      emitenteCnpj,
      sourceKey: 'sped',
      period: fiscalPeriod,
    }),
    queryFn: () => fetchSpedAnaliseFiscalHierarquica({ emitente_cnpj: emitenteCnpj, ...fiscalPeriod.params, limite: 5000 }),
    enabled: hasEmitenteCnpj && isSped && viewMode === 'detalhada',
    staleTime: 5 * 60 * 1000,
  });

  const { availableYears } = useFiscalYears({
    entries: yearsQuery.data?.resultados ?? [],
    selectedYear,
    setSelectedYear,
  });

  const currentData = dashboardQuery.data?.resumo_atual;
  const previousData = dashboardQuery.data?.resumo_anterior;
  const totalFaturamento = parseDecimal(currentData?.total_vendido ?? 0);
  const totalSalesChange = calculateChange(totalFaturamento, previousData?.total_vendido ?? 0);
  const ticketChange = calculateChange(currentData?.ticket_medio ?? 0, previousData?.ticket_medio ?? 0);
  const totalTaxesChange = calculateChange(currentData?.total_impostos ?? 0, previousData?.total_impostos ?? 0);

  const stats: readonly DetailStat[] = [
    {
      title: `Faturamento Mensal${selectedYear ? ` (Periodo ${selectedYear})` : ''}`,
      value: formatCurrency(totalFaturamento),
      description: formatPercent(totalSalesChange),
      icon: TrendingUp,
      trend: totalSalesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Comparativo anual',
      value: `${totalSalesChange >= 0 ? '+' : ''}${totalSalesChange.toFixed(1)}%`,
      description: selectedMonth === 'all' ? `vs. mesmo periodo de ${yearNumber - 1}` : 'vs. periodo anterior',
      icon: totalSalesChange >= 0 ? TrendingUp : TrendingDown,
      trend: totalSalesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-emerald-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Ticket Medio',
      value: formatCurrency(parseDecimal(currentData?.ticket_medio ?? 0)),
      description: formatPercent(ticketChange),
      icon: Users,
      trend: ticketChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Impostos sobre vendas',
      value: formatCurrency(parseDecimal(currentData?.total_impostos ?? 0)),
      description: formatPercent(totalTaxesChange),
      icon: Percent,
      trend: totalTaxesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ] as const;

  useEffect(() => {
    if (detailMode !== 'nota' || !notasInfiniteQuery.hasNextPage || notasInfiniteQuery.isFetchingNextPage) return;
    const sentinel = loadMoreRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) notasInfiniteQuery.fetchNextPage();
    }, { rootMargin: '240px 0px' });

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [detailMode, notasInfiniteQuery.fetchNextPage, notasInfiniteQuery.hasNextPage, notasInfiniteQuery.isFetchingNextPage]);

  const notas = useMemo(
    () => (detailMode === 'regiao' ? notasRegionQuery.data?.notas ?? [] : notasInfiniteQuery.data?.pages.flatMap((page) => page.notas) ?? []),
    [detailMode, notasInfiniteQuery.data?.pages, notasRegionQuery.data?.notas],
  );
  const filteredNotas = useMemo(() => filterNotasBySearch(notas, searchTerm), [notas, searchTerm]);
  const regionHierarchy = useMemo(() => buildRegionHierarchy(notas), [notas]);
  const filteredRegionHierarchy = useMemo(() => filterRegionHierarchyBySearch(regionHierarchy, searchTerm), [regionHierarchy, searchTerm]);
  const spedRows = useMemo(() => spedHierarchyQuery.data?.hierarquia ?? [], [spedHierarchyQuery.data?.hierarquia]);
  const filteredSpedRows = useMemo(() => filterSpedHierarchyRows(spedRows, searchTerm), [spedRows, searchTerm]);
  const spedRegionHierarchy = useMemo(() => buildSpedFiscalHierarchyState(filteredSpedRows), [filteredSpedRows]);
  const spedFiscalHierarchy = useMemo(() => buildSpedFiscalNcmHierarchy(filteredSpedRows), [filteredSpedRows]);

  const noteAccordionValues = useMemo(() => filteredNotas.map((nota) => `${nota.numero_nf}-${nota.data_emissao}`), [filteredNotas]);
  const noteClientAccordionValues = useMemo(() => filteredNotas.map((nota) => `cliente-${nota.numero_nf}-${nota.data_emissao}`), [filteredNotas]);
  const ncmAccordionValues = useMemo(
    () =>
      filteredNotas.flatMap((nota) =>
        Array.from(new Set(nota.itens.map((item) => item.ncm || 'sem-ncm'))).map(
          (ncm) => `ncm-${nota.numero_nf}-${nota.data_emissao}-${ncm}`,
        ),
      ),
    [filteredNotas],
  );
  const regionStateAccordionValues = useMemo(() => filteredRegionHierarchy.map((stateEntry) => stateEntry.key), [filteredRegionHierarchy]);
  const regionCityAccordionValues = useMemo(() => filteredRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.map((cityEntry) => cityEntry.key)), [filteredRegionHierarchy]);
  const regionClientAccordionValues = useMemo(
    () => filteredRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.flatMap((cityEntry) => cityEntry.clients.map((clientEntry) => clientEntry.key))),
    [filteredRegionHierarchy],
  );
  const spedRegionStateAccordionValues = useMemo(() => spedRegionHierarchy.map((stateEntry) => stateEntry.key), [spedRegionHierarchy]);
  const spedRegionCityAccordionValues = useMemo(() => spedRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.map((cityEntry) => cityEntry.key)), [spedRegionHierarchy]);
  const spedRegionNcmAccordionValues = useMemo(
    () => spedRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.flatMap((cityEntry) => cityEntry.ncms.map((ncmEntry) => ncmEntry.key))),
    [spedRegionHierarchy],
  );
  const fiscalNcmAccordionValues = useMemo(() => spedFiscalHierarchy.map((ncmEntry) => ncmEntry.key), [spedFiscalHierarchy]);

  useEffect(() => {
    setOpenNoteValues((current) => current.filter((value) => noteAccordionValues.includes(value)));
  }, [noteAccordionValues]);
  useEffect(() => {
    setOpenNoteClientValues((current) => current.filter((value) => noteClientAccordionValues.includes(value)));
  }, [noteClientAccordionValues]);
  useEffect(() => {
    setOpenNcmValues((current) => current.filter((value) => ncmAccordionValues.includes(value)));
  }, [ncmAccordionValues]);
  useEffect(() => {
    setOpenRegionStateValues((current) => current.filter((value) => regionStateAccordionValues.includes(value)));
  }, [regionStateAccordionValues]);
  useEffect(() => {
    setOpenRegionCityValues((current) => current.filter((value) => regionCityAccordionValues.includes(value)));
  }, [regionCityAccordionValues]);
  useEffect(() => {
    setOpenRegionClientValues((current) => current.filter((value) => regionClientAccordionValues.includes(value)));
  }, [regionClientAccordionValues]);
  useEffect(() => {
    setOpenSpedRegionStateValues((current) => current.filter((value) => spedRegionStateAccordionValues.includes(value)));
  }, [spedRegionStateAccordionValues]);
  useEffect(() => {
    setOpenSpedRegionCityValues((current) => current.filter((value) => spedRegionCityAccordionValues.includes(value)));
  }, [spedRegionCityAccordionValues]);
  useEffect(() => {
    setOpenSpedRegionNcmValues((current) => current.filter((value) => spedRegionNcmAccordionValues.includes(value)));
  }, [spedRegionNcmAccordionValues]);
  useEffect(() => {
    setOpenFiscalNcmValues((current) => current.filter((value) => fiscalNcmAccordionValues.includes(value)));
  }, [fiscalNcmAccordionValues]);

  const allNotesOpen = noteAccordionValues.length > 0 && noteAccordionValues.every((value) => openNoteValues.includes(value));
  const allNoteClientsOpen = noteClientAccordionValues.length > 0 && noteClientAccordionValues.every((value) => openNoteClientValues.includes(value));
  const allNcmsOpen = ncmAccordionValues.length > 0 && ncmAccordionValues.every((value) => openNcmValues.includes(value));
  const allRegionStatesOpen = regionStateAccordionValues.length > 0 && regionStateAccordionValues.every((value) => openRegionStateValues.includes(value));
  const allRegionCitiesOpen = regionCityAccordionValues.length > 0 && regionCityAccordionValues.every((value) => openRegionCityValues.includes(value));
  const allRegionClientsOpen = regionClientAccordionValues.length > 0 && regionClientAccordionValues.every((value) => openRegionClientValues.includes(value));
  const allSpedRegionStatesOpen = spedRegionStateAccordionValues.length > 0 && spedRegionStateAccordionValues.every((value) => openSpedRegionStateValues.includes(value));
  const allSpedRegionCitiesOpen = spedRegionCityAccordionValues.length > 0 && spedRegionCityAccordionValues.every((value) => openSpedRegionCityValues.includes(value));
  const allSpedRegionNcmsOpen = spedRegionNcmAccordionValues.length > 0 && spedRegionNcmAccordionValues.every((value) => openSpedRegionNcmValues.includes(value));
  const allFiscalNcmsOpen = fiscalNcmAccordionValues.length > 0 && fiscalNcmAccordionValues.every((value) => openFiscalNcmValues.includes(value));

  const levelButtons = useMemo(
    () =>
      buildLevelButtons({
        isSped,
        detailMode,
        allNotesOpen,
        allNoteClientsOpen,
        allNcmsOpen,
        allRegionStatesOpen,
        allRegionCitiesOpen,
        allRegionClientsOpen,
        allSpedRegionStatesOpen,
        allSpedRegionCitiesOpen,
        allSpedRegionNcmsOpen,
        allFiscalNcmsOpen,
        noteAccordionValues,
        noteClientAccordionValues,
        ncmAccordionValues,
        regionStateAccordionValues,
        regionCityAccordionValues,
        regionClientAccordionValues,
        spedRegionStateAccordionValues,
        spedRegionCityAccordionValues,
        spedRegionNcmAccordionValues,
        fiscalNcmAccordionValues,
        setOpenNoteValues,
        setOpenNoteClientValues,
        setOpenNcmValues,
        setOpenRegionStateValues,
        setOpenRegionCityValues,
        setOpenRegionClientValues,
        setOpenSpedRegionStateValues,
        setOpenSpedRegionCityValues,
        setOpenSpedRegionNcmValues,
        setOpenFiscalNcmValues,
      }),
    [
      allFiscalNcmsOpen,
      allNcmsOpen,
      allNoteClientsOpen,
      allNotesOpen,
      allRegionCitiesOpen,
      allRegionClientsOpen,
      allRegionStatesOpen,
      allSpedRegionCitiesOpen,
      allSpedRegionNcmsOpen,
      allSpedRegionStatesOpen,
      detailMode,
      fiscalNcmAccordionValues,
      isSped,
      ncmAccordionValues,
      noteAccordionValues,
      noteClientAccordionValues,
      regionCityAccordionValues,
      regionClientAccordionValues,
      regionStateAccordionValues,
      spedRegionCityAccordionValues,
      spedRegionNcmAccordionValues,
      spedRegionStateAccordionValues,
    ],
  );

  const searchPlaceholder = useMemo(() => getSearchPlaceholder(isSped, detailMode), [detailMode, isSped]);
  const modeOptions = useMemo(() => getDetailModeOptions(isSped), [isSped]);
  const detailScopeLabel = useMemo(() => getDetailScopeLabel(isSped, detailMode), [detailMode, isSped]);
  const detailSummaryText = useMemo(
    () =>
      getDetailSummaryText({
        isSped,
        detailMode,
        filteredNotasCount: filteredNotas.length,
        notasTotal: isSped
          ? spedRows.length
          : detailMode === 'regiao'
            ? notasRegionQuery.data?.total ?? notas.length
            : notasInfiniteQuery.data?.pages[0]?.total ?? notas.length,
        filteredSpedRowsCount: filteredSpedRows.length,
      }),
    [detailMode, filteredNotas.length, filteredSpedRows.length, isSped, notas.length, notasInfiniteQuery.data?.pages, notasRegionQuery.data?.total, spedRows.length],
  );
  const emptyDetailMessage = useMemo(
    () =>
      getEmptyDetailMessage({
        isLoading: isSped
          ? spedHierarchyQuery.isLoading
          : detailMode === 'regiao'
            ? notasRegionQuery.isLoading
            : notasInfiniteQuery.isLoading,
        searchTerm,
      }),
    [detailMode, isSped, notasInfiniteQuery.isLoading, notasRegionQuery.isLoading, searchTerm, spedHierarchyQuery.isLoading],
  );

  const activeHasResults = isSped
    ? (detailMode === 'fiscal' ? spedFiscalHierarchy.length > 0 : spedRegionHierarchy.length > 0)
    : (detailMode === 'nota' ? filteredNotas.length > 0 : filteredRegionHierarchy.length > 0);
  const isDetalhamentoLoading = isSped ? spedHierarchyQuery.isLoading : (detailMode === 'regiao' ? notasRegionQuery.isLoading : notasInfiniteQuery.isLoading);
  const detalhamentoError = isSped ? spedHierarchyQuery.error : (detailMode === 'regiao' ? notasRegionQuery.error : notasInfiniteQuery.error);
  const notasTotal = isSped ? spedRows.length : (detailMode === 'regiao' ? notasRegionQuery.data?.total ?? notas.length : notasInfiniteQuery.data?.pages[0]?.total ?? notas.length);

  return {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    availableYears,
    monthLabels,
    viewMode,
    setViewMode,
    detailMode,
    setDetailMode,
    isSped,
    modeOptions,
    stats,
    dashboardQuery,
    mapQuery,
    searchTerm,
    setSearchTerm,
    searchPlaceholder,
    levelButtons,
    activeHasResults,
    isDetalhamentoLoading,
    detalhamentoError,
    notasTotal,
    detailScopeLabel,
    detailSummaryText,
    emptyDetailMessage,
    notasInfiniteQuery,
    loadMoreRef,
    filteredNotas,
    filteredRegionHierarchy,
    spedFiscalHierarchy,
    spedRegionHierarchy,
    filteredSpedRows,
    openNoteValues,
    setOpenNoteValues,
    openNoteClientValues,
    setOpenNoteClientValues,
    openNcmValues,
    setOpenNcmValues,
    openRegionStateValues,
    setOpenRegionStateValues,
    openRegionCityValues,
    setOpenRegionCityValues,
    openRegionClientValues,
    setOpenRegionClientValues,
    openSpedRegionStateValues,
    setOpenSpedRegionStateValues,
    openSpedRegionCityValues,
    setOpenSpedRegionCityValues,
    openSpedRegionNcmValues,
    setOpenSpedRegionNcmValues,
    openFiscalNcmValues,
    setOpenFiscalNcmValues,
  };
}
