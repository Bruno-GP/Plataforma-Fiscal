import { useEffect, useMemo, useRef, useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { ArrowRight, Percent, Search, TrendingDown, TrendingUp, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

import { useAuth } from '@/contexts/AuthContext';
import { useFiscalYears } from '@/hooks/useFiscalYears';
import {
  DetalhamentoFiscalHierarquiaMode,
} from '@/pages/components/DetalhamentoFiscalHierarquiaMode';
import { DetalhamentoVendasDashboardMode } from '@/pages/components/DetalhamentoVendasDashboardMode';
import { DetalhamentoVendasFiscalMode } from '@/pages/components/DetalhamentoVendasFiscalMode';
import { DetalhamentoVendasModeSelector } from '@/pages/components/DetalhamentoVendasModeSelector';
import { DetalhamentoVendasNotaMode } from '@/pages/components/DetalhamentoVendasNotaMode';
import { DetalhamentoVendasRegiaoMode } from '@/pages/components/DetalhamentoVendasRegiaoMode';
import {
  buildSpedFiscalNcmHierarchy,
  buildSpedFiscalHierarchyState,
  buildRegionHierarchy,
  type DetailMode,
  filterSpedHierarchyRows,
  filterNotasBySearch,
  filterRegionHierarchyBySearch,
} from '@/pages/components/detalhamentoVendasHelpers';
import { Header } from '@/pages/components/Header';
import { StatCard } from '@/pages/components/StatCard';

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

const NOTAS_PAGE_SIZE = 100;

export default function DetalhamentoVendas() {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const isSped = Boolean(user?.tem_sped);
  const fiscalApi = createFiscalSourceApi(user?.tem_sped);

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
  const { dashboardQuery, mapQuery } = useDashboardVendasQueries({ emitenteCnpj, email: user?.email, temSped: user?.tem_sped, year: yearNumber, selectedMonth: dashboardSelectedMonth, monthNumber, hasEmitenteCnpj });

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
    queryFn: ({ pageParam = 0 }) => fetchNfeNotasDetalhadas({ emitente_cnpj: emitenteCnpj, email: user?.email, ...fiscalPeriod.params, tipo_operacao: 'vendas', limite: NOTAS_PAGE_SIZE, offset: pageParam }),
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
    queryFn: () => fetchNfeNotasDetalhadas({ emitente_cnpj: emitenteCnpj, email: user?.email, ...fiscalPeriod.params, tipo_operacao: 'vendas', limite: 500, offset: 0 }).then(async (firstPage) => {
      if (firstPage.total <= firstPage.notas.length) return firstPage;
      let offset = firstPage.notas.length;
      const notas = [...firstPage.notas];
      while (offset < firstPage.total) {
        const nextPage = await fetchNfeNotasDetalhadas({ emitente_cnpj: emitenteCnpj, email: user?.email, ...fiscalPeriod.params, tipo_operacao: 'vendas', limite: 500, offset });
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
  const totalFaturamento = parseDecimal(mapQuery.data?.total_vendido ?? currentData?.total_vendido ?? 0);

  const totalSalesChange = calculateChange(totalFaturamento, previousData?.total_vendido ?? 0);
  const ticketChange = calculateChange(currentData?.ticket_medio ?? 0, previousData?.ticket_medio ?? 0);
  const totalTaxesChange = calculateChange(currentData?.total_impostos ?? 0, previousData?.total_impostos ?? 0);

  const stats = [
    { title: `Faturamento Mensal${selectedYear ? ` (Periodo ${selectedYear})` : ''}`, value: formatCurrency(totalFaturamento), description: formatPercent(totalSalesChange), icon: TrendingUp, trend: totalSalesChange >= 0 ? 'up' : 'down', accentClass: 'border-l-sky-500' },
    { title: 'Comparativo anual', value: `${totalSalesChange >= 0 ? '+' : ''}${totalSalesChange.toFixed(1)}%`, description: selectedMonth === 'all' ? `vs. mesmo periodo de ${yearNumber - 1}` : 'vs. periodo anterior', icon: totalSalesChange >= 0 ? TrendingUp : TrendingDown, trend: totalSalesChange >= 0 ? 'up' : 'down', accentClass: 'border-l-emerald-500', appendPreviousMonthLabel: false },
    { title: 'Ticket Medio', value: formatCurrency(parseDecimal(currentData?.ticket_medio ?? 0)), description: formatPercent(ticketChange), icon: Users, trend: ticketChange >= 0 ? 'up' : 'down', accentClass: 'border-l-amber-400' },
    { title: 'Impostos sobre vendas', value: formatCurrency(parseDecimal(currentData?.total_impostos ?? 0)), description: formatPercent(totalTaxesChange), icon: Percent, trend: totalTaxesChange >= 0 ? 'up' : 'down', accentClass: 'border-l-violet-500' },
  ] as const;

  useEffect(() => {
    if (detailMode !== 'nota' || !notasInfiniteQuery.hasNextPage || notasInfiniteQuery.isFetchingNextPage) return;
    const sentinel = loadMoreRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver((entries) => { if (entries[0]?.isIntersecting) notasInfiniteQuery.fetchNextPage(); }, { rootMargin: '240px 0px' });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [detailMode, notasInfiniteQuery.fetchNextPage, notasInfiniteQuery.hasNextPage, notasInfiniteQuery.isFetchingNextPage]);

  const notas = useMemo(() => (detailMode === 'regiao' ? notasRegionQuery.data?.notas ?? [] : notasInfiniteQuery.data?.pages.flatMap((page) => page.notas) ?? []), [detailMode, notasInfiniteQuery.data?.pages, notasRegionQuery.data?.notas]);
  const filteredNotas = useMemo(() => filterNotasBySearch(notas, searchTerm), [notas, searchTerm]);
  const regionHierarchy = useMemo(() => buildRegionHierarchy(notas), [notas]);
  const filteredRegionHierarchy = useMemo(() => filterRegionHierarchyBySearch(regionHierarchy, searchTerm), [regionHierarchy, searchTerm]);
  const spedRows = useMemo(() => spedHierarchyQuery.data?.hierarquia ?? [], [spedHierarchyQuery.data?.hierarquia]);
  const filteredSpedRows = useMemo(() => filterSpedHierarchyRows(spedRows, searchTerm), [spedRows, searchTerm]);
  const spedRegionHierarchy = useMemo(() => buildSpedFiscalHierarchyState(filteredSpedRows), [filteredSpedRows]);
  const spedFiscalHierarchy = useMemo(() => buildSpedFiscalNcmHierarchy(filteredSpedRows), [filteredSpedRows]);

  const noteAccordionValues = useMemo(() => filteredNotas.map((nota) => `${nota.numero_nf}-${nota.data_emissao}`), [filteredNotas]);
  const noteClientAccordionValues = useMemo(() => filteredNotas.map((nota) => `cliente-${nota.numero_nf}-${nota.data_emissao}`), [filteredNotas]);
  const ncmAccordionValues = useMemo(() => filteredNotas.flatMap((nota) => Array.from(new Set(nota.itens.map((item) => item.ncm || 'sem-ncm'))).map((ncm) => `ncm-${nota.numero_nf}-${nota.data_emissao}-${ncm}`)), [filteredNotas]);
  const regionStateAccordionValues = useMemo(() => filteredRegionHierarchy.map((stateEntry) => stateEntry.key), [filteredRegionHierarchy]);
  const regionCityAccordionValues = useMemo(() => filteredRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.map((cityEntry) => cityEntry.key)), [filteredRegionHierarchy]);
  const regionClientAccordionValues = useMemo(() => filteredRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.flatMap((cityEntry) => cityEntry.clients.map((clientEntry) => clientEntry.key))), [filteredRegionHierarchy]);
  const spedRegionStateAccordionValues = useMemo(() => spedRegionHierarchy.map((stateEntry) => stateEntry.key), [spedRegionHierarchy]);
  const spedRegionCityAccordionValues = useMemo(() => spedRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.map((cityEntry) => cityEntry.key)), [spedRegionHierarchy]);
  const spedRegionNcmAccordionValues = useMemo(() => spedRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.flatMap((cityEntry) => cityEntry.ncms.map((ncmEntry) => ncmEntry.key))), [spedRegionHierarchy]);
  const fiscalNcmAccordionValues = useMemo(() => spedFiscalHierarchy.map((ncmEntry) => ncmEntry.key), [spedFiscalHierarchy]);

  useEffect(() => { setOpenNoteValues((current) => current.filter((value) => noteAccordionValues.includes(value))); }, [noteAccordionValues]);
  useEffect(() => { setOpenNoteClientValues((current) => current.filter((value) => noteClientAccordionValues.includes(value))); }, [noteClientAccordionValues]);
  useEffect(() => { setOpenNcmValues((current) => current.filter((value) => ncmAccordionValues.includes(value))); }, [ncmAccordionValues]);
  useEffect(() => { setOpenRegionStateValues((current) => current.filter((value) => regionStateAccordionValues.includes(value))); }, [regionStateAccordionValues]);
  useEffect(() => { setOpenRegionCityValues((current) => current.filter((value) => regionCityAccordionValues.includes(value))); }, [regionCityAccordionValues]);
  useEffect(() => { setOpenRegionClientValues((current) => current.filter((value) => regionClientAccordionValues.includes(value))); }, [regionClientAccordionValues]);
  useEffect(() => { setOpenSpedRegionStateValues((current) => current.filter((value) => spedRegionStateAccordionValues.includes(value))); }, [spedRegionStateAccordionValues]);
  useEffect(() => { setOpenSpedRegionCityValues((current) => current.filter((value) => spedRegionCityAccordionValues.includes(value))); }, [spedRegionCityAccordionValues]);
  useEffect(() => { setOpenSpedRegionNcmValues((current) => current.filter((value) => spedRegionNcmAccordionValues.includes(value))); }, [spedRegionNcmAccordionValues]);
  useEffect(() => { setOpenFiscalNcmValues((current) => current.filter((value) => fiscalNcmAccordionValues.includes(value))); }, [fiscalNcmAccordionValues]);

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

  const levelButtons = useMemo(() => {
    if (!isSped) {
      const toggleLevelOne = () => { if (detailMode === 'regiao') { setOpenRegionStateValues(allRegionStatesOpen ? [] : regionStateAccordionValues); return; } setOpenNoteValues(allNotesOpen ? [] : noteAccordionValues); };
      const toggleLevelTwo = () => {
        if (detailMode === 'regiao') { if (allRegionCitiesOpen) { setOpenRegionCityValues([]); return; } setOpenRegionStateValues(regionStateAccordionValues); setOpenRegionCityValues(regionCityAccordionValues); return; }
        if (allNoteClientsOpen) { setOpenNoteClientValues([]); return; }
        setOpenNoteValues(noteAccordionValues); setOpenNoteClientValues(noteClientAccordionValues);
      };
      const toggleLevelThree = () => {
        if (detailMode === 'regiao') { if (allRegionClientsOpen) { setOpenRegionClientValues([]); return; } setOpenRegionStateValues(regionStateAccordionValues); setOpenRegionCityValues(regionCityAccordionValues); setOpenRegionClientValues(regionClientAccordionValues); return; }
        if (allNcmsOpen) { setOpenNcmValues([]); return; }
        setOpenNoteValues(noteAccordionValues); setOpenNoteClientValues(noteClientAccordionValues); setOpenNcmValues(ncmAccordionValues);
      };

      return detailMode === 'regiao'
        ? [
            { key: 'nivel-1', title: 'Estado', isOpen: allRegionStatesOpen, onClick: toggleLevelOne },
            { key: 'nivel-2', title: 'Cidade', isOpen: allRegionCitiesOpen, onClick: toggleLevelTwo },
            { key: 'nivel-3', title: 'Cliente', isOpen: allRegionClientsOpen, onClick: toggleLevelThree },
            { key: 'nivel-4', title: 'Produto', isOpen: allRegionClientsOpen, onClick: toggleLevelThree },
          ]
        : [
            { key: 'nivel-1', title: 'Nota', isOpen: allNotesOpen, onClick: toggleLevelOne },
            { key: 'nivel-2', title: 'Cliente', isOpen: allNoteClientsOpen, onClick: toggleLevelTwo },
            { key: 'nivel-3', title: 'NCM', isOpen: allNcmsOpen, onClick: toggleLevelThree },
            { key: 'nivel-4', title: 'Produto', isOpen: allNcmsOpen, onClick: toggleLevelThree },
          ];
    }

    if (detailMode === 'fiscal') {
      return [
        { key: 'nivel-fiscal-1', title: 'NCM', isOpen: allFiscalNcmsOpen, onClick: () => setOpenFiscalNcmValues(allFiscalNcmsOpen ? [] : fiscalNcmAccordionValues) },
        { key: 'nivel-fiscal-2', title: 'Produto', isOpen: allFiscalNcmsOpen, onClick: () => setOpenFiscalNcmValues(fiscalNcmAccordionValues) },
      ];
    }

    return [
      { key: 'nivel-sped-1', title: 'Estado', isOpen: allSpedRegionStatesOpen, onClick: () => setOpenSpedRegionStateValues(allSpedRegionStatesOpen ? [] : spedRegionStateAccordionValues) },
      { key: 'nivel-sped-2', title: 'Cidade', isOpen: allSpedRegionCitiesOpen, onClick: () => { if (allSpedRegionCitiesOpen) { setOpenSpedRegionCityValues([]); return; } setOpenSpedRegionStateValues(spedRegionStateAccordionValues); setOpenSpedRegionCityValues(spedRegionCityAccordionValues); } },
      { key: 'nivel-sped-3', title: 'NCM', isOpen: allSpedRegionNcmsOpen, onClick: () => { if (allSpedRegionNcmsOpen) { setOpenSpedRegionNcmValues([]); return; } setOpenSpedRegionStateValues(spedRegionStateAccordionValues); setOpenSpedRegionCityValues(spedRegionCityAccordionValues); setOpenSpedRegionNcmValues(spedRegionNcmAccordionValues); } },
      { key: 'nivel-sped-4', title: 'Produto', isOpen: allSpedRegionNcmsOpen, onClick: () => { setOpenSpedRegionStateValues(spedRegionStateAccordionValues); setOpenSpedRegionCityValues(spedRegionCityAccordionValues); setOpenSpedRegionNcmValues(spedRegionNcmAccordionValues); } },
    ];
  }, [allFiscalNcmsOpen, allNcmsOpen, allNoteClientsOpen, allNotesOpen, allRegionCitiesOpen, allRegionClientsOpen, allRegionStatesOpen, allSpedRegionCitiesOpen, allSpedRegionNcmsOpen, allSpedRegionStatesOpen, detailMode, fiscalNcmAccordionValues, isSped, ncmAccordionValues, noteAccordionValues, noteClientAccordionValues, regionCityAccordionValues, regionClientAccordionValues, regionStateAccordionValues, spedRegionCityAccordionValues, spedRegionNcmAccordionValues, spedRegionStateAccordionValues]);

  const searchPlaceholder = useMemo(() => {
    if (!isSped) return detailMode === 'nota' ? 'Pesquisar por nota, cliente, documento, NCM ou produto' : 'Pesquisar por estado, cidade, cliente ou produto';
    return detailMode === 'fiscal' ? 'Pesquisar por NCM ou produto' : 'Pesquisar por estado, cidade, NCM ou produto';
  }, [detailMode, isSped]);

  const modeOptions = useMemo(() => isSped ? [
    { key: 'regiao' as const, title: 'Detalhamento por regiao', description: 'Estado > cidade > NCM > produto' },
    { key: 'fiscal' as const, title: 'Detalhamento fiscal', description: 'NCM > produto' },
  ] : undefined, [isSped]);

  const activeHasResults = isSped ? (detailMode === 'fiscal' ? spedFiscalHierarchy.length > 0 : spedRegionHierarchy.length > 0) : (detailMode === 'nota' ? filteredNotas.length > 0 : filteredRegionHierarchy.length > 0);
  const isDetalhamentoLoading = isSped ? spedHierarchyQuery.isLoading : (detailMode === 'regiao' ? notasRegionQuery.isLoading : notasInfiniteQuery.isLoading);
  const detalhamentoError = isSped ? spedHierarchyQuery.error : (detailMode === 'regiao' ? notasRegionQuery.error : notasInfiniteQuery.error);
  const notasTotal = isSped ? spedRows.length : (detailMode === 'regiao' ? notasRegionQuery.data?.total ?? notas.length : notasInfiniteQuery.data?.pages[0]?.total ?? notas.length);

  return (
    <div className="space-y-6 py-6">
      <Header title="Detalhamento de vendas" subtitle="Visao de dashboard e expansao hierarquica por nota, regiao ou leitura fiscal." selectedMonth={selectedMonth} selectedYear={selectedYear} availableYears={availableYears} monthLabels={monthLabels} onMonthChange={setSelectedMonth} onYearChange={setSelectedYear} />

      <div className="stat-card-grid">
        {stats.map((stat) => <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />)}
      </div>

      <div className="flex flex-wrap gap-3 border-y border-slate-800/80 py-4">
        {[
          { key: 'grafica' as const, title: 'Visao grafica' },
          { key: 'detalhada' as const, title: 'Visao detalhada' },
        ].map((button) => {
          const isActive = viewMode === button.key;

          return (
            <Button
              key={button.key}
              type="button"
              variant={isActive ? 'secondary' : 'outline'}
              onClick={() => setViewMode(button.key)}
              className={isActive ? 'bg-white text-slate-900 hover:bg-slate-100' : 'border-slate-700 bg-slate-900/80 text-slate-100 hover:border-sky-500/60 hover:bg-slate-800'}
            >
              {button.title}
            </Button>
          );
        })}
      </div>

      {viewMode === 'detalhada' && (
      <Card className="border border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]">
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <Badge className="border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">Drill-down hierarquico</Badge>
              <h2 className="text-2xl font-semibold tracking-tight">{isSped ? (detailMode === 'fiscal' ? 'Expansao fiscal em 2 niveis' : 'Expansao em 4 niveis para SPED') : 'Expansao em 4 niveis'}</h2>
              <p className="max-w-3xl text-sm text-slate-300">{isSped ? 'No SPED, o detalhamento usa a hierarquia fiscal existente para leitura por regiao ou por NCM.' : 'Alterne entre leitura por nota ou por regiao e abra a hierarquia em camadas ate chegar aos produtos.'}</p>
            </div>
            <Button asChild variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100"><Link to="/analise-vendas">Voltar a Analise de Vendas<ArrowRight className="h-4 w-4" /></Link></Button>
          </div>
          <DetalhamentoVendasModeSelector detailMode={detailMode} onChange={setDetailMode} options={modeOptions} />
        </CardContent>
      </Card>
      )}

      {detalhamentoError && <Alert variant="destructive"><AlertTitle>Erro ao carregar o detalhamento</AlertTitle><AlertDescription>{detalhamentoError instanceof Error ? detalhamentoError.message : 'Nao foi possivel consultar o detalhamento deste periodo.'}</AlertDescription></Alert>}

      {viewMode === 'grafica' ? (
        <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
          <CardContent className="p-6">
            <DetalhamentoVendasDashboardMode
              dashboardData={dashboardQuery.data}
              isLoading={dashboardQuery.isLoading || mapQuery.isLoading}
              availableYears={availableYears}
              selectedYear={selectedYear}
              onYearChange={setSelectedYear}
            />
          </CardContent>
        </Card>
      ) : (
      <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
        <CardContent className="p-0">
          <div className="border-b border-slate-800/80 px-6 py-4">
            <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="relative w-full max-w-xl">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder={searchPlaceholder} className="border-slate-700 bg-slate-900/80 pl-10 text-slate-100 placeholder:text-slate-400 focus-visible:ring-sky-500" />
              </div>
              <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Busca aplicada em: {!isSped ? (detailMode === 'nota' ? 'detalhamento por nota' : 'detalhamento por regiao') : (detailMode === 'fiscal' ? 'detalhamento fiscal' : 'detalhamento por regiao')}</div>
            </div>

            <div className="mb-4 text-xs text-slate-400">{isSped ? `Exibindo ${filteredSpedRows.length} linhas agregadas da hierarquia fiscal.` : (detailMode === 'nota' ? `Exibindo ${filteredNotas.length} de ${notasTotal} notas carregadas em blocos de ${NOTAS_PAGE_SIZE}.` : `Exibindo ${notasTotal} notas consolidadas na hierarquia regional.`)}</div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {levelButtons.map((button) => (
                <Button key={button.key} type="button" variant="outline" onClick={button.onClick} className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800"><span className="flex flex-col items-start gap-1"><span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">{button.title}</span><span className="text-sm font-medium text-slate-100">{button.isOpen ? 'Fechar visualizacao detalhada' : 'Abrir visualizacao detalhada'}</span></span></Button>
              ))}
            </div>
          </div>

          {activeHasResults ? (!isSped ? (detailMode === 'nota' ? (
            <div className="max-h-[70vh] overflow-y-auto">
              <DetalhamentoVendasNotaMode notas={filteredNotas} openNoteValues={openNoteValues} onOpenNoteValuesChange={setOpenNoteValues} openNoteClientValues={openNoteClientValues} onOpenNoteClientValuesChange={setOpenNoteClientValues} openNcmValues={openNcmValues} onOpenNcmValuesChange={setOpenNcmValues} />
              <div ref={loadMoreRef} className="px-6 py-4 text-center text-sm text-slate-400">{notasInfiniteQuery.isFetchingNextPage ? 'Carregando mais notas...' : notasInfiniteQuery.hasNextPage ? 'Role para baixo para carregar mais 100 notas.' : notas.length > 0 ? 'Todas as notas carregadas.' : null}</div>
            </div>
          ) : <DetalhamentoVendasRegiaoMode regionHierarchy={filteredRegionHierarchy} openRegionStateValues={openRegionStateValues} onOpenRegionStateValuesChange={setOpenRegionStateValues} openRegionCityValues={openRegionCityValues} onOpenRegionCityValuesChange={setOpenRegionCityValues} openRegionClientValues={openRegionClientValues} onOpenRegionClientValuesChange={setOpenRegionClientValues} />) : (detailMode === 'fiscal' ? <DetalhamentoVendasFiscalMode hierarchy={spedFiscalHierarchy} openNcmValues={openFiscalNcmValues} onOpenNcmValuesChange={setOpenFiscalNcmValues} /> : <DetalhamentoFiscalHierarquiaMode hierarchy={spedRegionHierarchy} openStateValues={openSpedRegionStateValues} onOpenStateValuesChange={setOpenSpedRegionStateValues} openCityValues={openSpedRegionCityValues} onOpenCityValuesChange={setOpenSpedRegionCityValues} openNcmValues={openSpedRegionNcmValues} onOpenNcmValuesChange={setOpenSpedRegionNcmValues} />)) : (
            <div className="p-6 text-sm text-slate-300">{isDetalhamentoLoading ? 'Carregando detalhamento...' : searchTerm.trim() ? 'Nenhum detalhamento encontrado para a pesquisa informada neste modo.' : 'Nenhum dado de venda encontrado para o periodo selecionado.'}</div>
          )}
        </CardContent>
      </Card>
      )}
    </div>
  );
}
