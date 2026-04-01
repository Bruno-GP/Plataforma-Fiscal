import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Percent, Search, TrendingDown, TrendingUp, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/contexts/AuthContext';
import { DetalhamentoVendasModeSelector } from '@/pages/components/DetalhamentoVendasModeSelector';
import { DetalhamentoVendasNotaMode } from '@/pages/components/DetalhamentoVendasNotaMode';
import { DetalhamentoVendasRegiaoMode } from '@/pages/components/DetalhamentoVendasRegiaoMode';
import {
  buildRegionHierarchy,
  type DetailMode,
  filterNotasBySearch,
  filterRegionHierarchyBySearch,
} from '@/pages/components/detalhamentoVendasHelpers';
import { Header } from '@/pages/components/Header';
import { StatCard } from '@/pages/components/StatCard';
import {
  fetchAllNfeNotasDetalhadas,
  fetchNfeDashboardVendas,
  fetchNfeKpis,
  parseDecimal,
} from '@/services/nfe';
import { fetchSpedDashboardVendas, fetchSpedKpis } from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

export default function DetalhamentoVendas() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [detailMode, setDetailMode] = useState<DetailMode>('nota');
  const [openNoteValues, setOpenNoteValues] = useState<string[]>([]);
  const [openNoteClientValues, setOpenNoteClientValues] = useState<string[]>([]);
  const [openNcmValues, setOpenNcmValues] = useState<string[]>([]);
  const [openRegionStateValues, setOpenRegionStateValues] = useState<string[]>([]);
  const [openRegionCityValues, setOpenRegionCityValues] = useState<string[]>([]);
  const [openRegionClientValues, setOpenRegionClientValues] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);
  const isSped = Boolean(user?.tem_sped);

  const yearsQuery = useQuery({
    queryKey: ['detalhamento-vendas-anos', emitenteCnpj, isSped],
    queryFn: () =>
      isSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const dashboardQuery = useQuery({
    queryKey: ['detalhamento-vendas-dashboard', emitenteCnpj, isSped, yearNumber, selectedMonth],
    queryFn: () =>
      isSped
        ? fetchSpedDashboardVendas({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          })
        : fetchNfeDashboardVendas({
            emitente_cnpj: emitenteCnpj,
            email: user?.email,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const notasQuery = useQuery({
    queryKey: ['detalhamento-vendas-notas', emitenteCnpj, selectedYear, selectedMonth],
    queryFn: () =>
      fetchAllNfeNotasDetalhadas({
        emitente_cnpj: emitenteCnpj,
        email: user?.email,
        periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
        periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
        tipo_operacao: 'vendas',
      }),
    enabled: hasEmitenteCnpj && !isSped,
    staleTime: 5 * 60 * 1000,
  });

  const availableYears = useMemo(() => {
    const years = new Set<number>();
    for (const item of yearsQuery.data?.resultados ?? []) {
      if (item.periodo_ano) years.add(item.periodo_ano);
    }
    return years.size ? [...years].sort((a, b) => b - a) : [new Date().getFullYear()];
  }, [yearsQuery.data]);

  useEffect(() => {
    if (!availableYears.length) return;
    if (!availableYears.includes(Number.parseInt(selectedYear, 10))) setSelectedYear(String(availableYears[0]));
  }, [availableYears, selectedYear]);

  const currentData = dashboardQuery.data?.resumo_atual;
  const previousData = dashboardQuery.data?.resumo_anterior;
  const totalFaturamento = parseDecimal(currentData?.total_vendido ?? 0);

  const totalSalesChange = parseDecimal(previousData?.total_vendido ?? 0)
    ? ((totalFaturamento - parseDecimal(previousData?.total_vendido ?? 0)) /
        parseDecimal(previousData?.total_vendido ?? 0)) *
      100
    : 0;
  const ticketChange = parseDecimal(previousData?.ticket_medio ?? 0)
    ? ((parseDecimal(currentData?.ticket_medio ?? 0) - parseDecimal(previousData?.ticket_medio ?? 0)) /
        parseDecimal(previousData?.ticket_medio ?? 0)) *
      100
    : 0;
  const totalTaxesChange = parseDecimal(previousData?.total_impostos ?? 0)
    ? ((parseDecimal(currentData?.total_impostos ?? 0) - parseDecimal(previousData?.total_impostos ?? 0)) /
        parseDecimal(previousData?.total_impostos ?? 0)) *
      100
    : 0;

  const stats = [
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

  const notas = useMemo(() => notasQuery.data?.notas ?? [], [notasQuery.data?.notas]);
  const totalDetalhado = useMemo(
    () => notas.reduce((total, nota) => total + parseDecimal(nota.valor_total_nf), 0),
    [notas],
  );
  const regionHierarchy = useMemo(() => buildRegionHierarchy(notas), [notas]);
  const filteredNotas = useMemo(() => filterNotasBySearch(notas, searchTerm), [notas, searchTerm]);
  const filteredRegionHierarchy = useMemo(
    () => filterRegionHierarchyBySearch(regionHierarchy, searchTerm),
    [regionHierarchy, searchTerm],
  );
  const activeHasResults = detailMode === 'nota' ? filteredNotas.length > 0 : filteredRegionHierarchy.length > 0;
  const searchPlaceholder =
    detailMode === 'nota'
      ? 'Pesquisar por nota, cliente, documento, NCM ou produto'
      : 'Pesquisar por estado, cidade, cliente ou produto';

  const noteAccordionValues = useMemo(
    () => filteredNotas.map((nota) => `${nota.numero_nf}-${nota.data_emissao}`),
    [filteredNotas],
  );
  const noteClientAccordionValues = useMemo(
    () => filteredNotas.map((nota) => `cliente-${nota.numero_nf}-${nota.data_emissao}`),
    [filteredNotas],
  );
  const ncmAccordionValues = useMemo(
    () =>
      filteredNotas.flatMap((nota) =>
        Array.from(new Set(nota.itens.map((item) => item.ncm || 'sem-ncm'))).map(
          (ncm) => `ncm-${nota.numero_nf}-${nota.data_emissao}-${ncm}`,
        ),
      ),
    [filteredNotas],
  );
  const regionStateAccordionValues = useMemo(
    () => filteredRegionHierarchy.map((stateEntry) => stateEntry.key),
    [filteredRegionHierarchy],
  );
  const regionCityAccordionValues = useMemo(
    () => filteredRegionHierarchy.flatMap((stateEntry) => stateEntry.cities.map((cityEntry) => cityEntry.key)),
    [filteredRegionHierarchy],
  );
  const regionClientAccordionValues = useMemo(
    () =>
      filteredRegionHierarchy.flatMap((stateEntry) =>
        stateEntry.cities.flatMap((cityEntry) => cityEntry.clients.map((clientEntry) => clientEntry.key)),
      ),
    [filteredRegionHierarchy],
  );

  useEffect(() => {
    setOpenNoteValues((current) => current.filter((value) => noteAccordionValues.includes(value)));
  }, [noteAccordionValues]);

  useEffect(() => {
    setOpenNoteClientValues((current) =>
      current.filter((value) => noteClientAccordionValues.includes(value)),
    );
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
    setOpenRegionClientValues((current) =>
      current.filter((value) => regionClientAccordionValues.includes(value)),
    );
  }, [regionClientAccordionValues]);

  const allNotesOpen =
    noteAccordionValues.length > 0 && noteAccordionValues.every((value) => openNoteValues.includes(value));
  const allNoteClientsOpen =
    noteClientAccordionValues.length > 0 &&
    noteClientAccordionValues.every((value) => openNoteClientValues.includes(value));
  const allNcmsOpen =
    ncmAccordionValues.length > 0 && ncmAccordionValues.every((value) => openNcmValues.includes(value));
  const allRegionStatesOpen =
    regionStateAccordionValues.length > 0 &&
    regionStateAccordionValues.every((value) => openRegionStateValues.includes(value));
  const allRegionCitiesOpen =
    regionCityAccordionValues.length > 0 &&
    regionCityAccordionValues.every((value) => openRegionCityValues.includes(value));
  const allRegionClientsOpen =
    regionClientAccordionValues.length > 0 &&
    regionClientAccordionValues.every((value) => openRegionClientValues.includes(value));

  const toggleLevelOne = () => {
    if (detailMode === 'regiao') {
      setOpenRegionStateValues(allRegionStatesOpen ? [] : regionStateAccordionValues);
      return;
    }
    setOpenNoteValues(allNotesOpen ? [] : noteAccordionValues);
  };

  const toggleLevelTwo = () => {
    if (detailMode === 'regiao') {
      if (allRegionCitiesOpen) {
        setOpenRegionCityValues([]);
        return;
      }
      setOpenRegionStateValues(regionStateAccordionValues);
      setOpenRegionCityValues(regionCityAccordionValues);
      return;
    }
    if (allNoteClientsOpen) {
      setOpenNoteClientValues([]);
      return;
    }
    setOpenNoteValues(noteAccordionValues);
    setOpenNoteClientValues(noteClientAccordionValues);
  };

  const toggleLevelThree = () => {
    if (detailMode === 'regiao') {
      if (allRegionClientsOpen) {
        setOpenRegionClientValues([]);
        return;
      }
      setOpenRegionStateValues(regionStateAccordionValues);
      setOpenRegionCityValues(regionCityAccordionValues);
      setOpenRegionClientValues(regionClientAccordionValues);
      return;
    }
    if (allNcmsOpen) {
      setOpenNcmValues([]);
      return;
    }
    setOpenNoteValues(noteAccordionValues);
    setOpenNoteClientValues(noteClientAccordionValues);
    setOpenNcmValues(ncmAccordionValues);
  };

  const levelButtons =
    detailMode === 'regiao'
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

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Detalhamento de vendas"
        subtitle="Expansao hierarquica por nota ou por regiao com visual alinhado a paleta azul-marinho."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />
        ))}
      </div>

      <Card className="border border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]">
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <Badge className="border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">
                Drill-down hierarquico
              </Badge>
              <h2 className="text-2xl font-semibold tracking-tight">Expansao em 4 niveis</h2>
              <p className="max-w-3xl text-sm text-slate-300">
                Alterne entre leitura por nota ou por regiao e abra a hierarquia em camadas ate chegar aos produtos.
              </p>
            </div>
            <Button asChild variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100">
              <Link to="/analise-vendas">
                Voltar ao dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>

          <DetalhamentoVendasModeSelector detailMode={detailMode} onChange={setDetailMode} />
        </CardContent>
      </Card>

      {isSped && (
        <Alert>
          <AlertTitle>Detalhamento por nota ainda nao disponivel para SPED</AlertTitle>
          <AlertDescription>
            Esta versao foi conectada a estrutura detalhada de NFe/XML. Se voce quiser, eu posso preparar a mesma
            experiencia para SPED no proximo passo.
          </AlertDescription>
        </Alert>
      )}

      {!isSped && notasQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar notas detalhadas</AlertTitle>
          <AlertDescription>
            {notasQuery.error instanceof Error
              ? notasQuery.error.message
              : 'Nao foi possivel consultar as notas detalhadas deste periodo.'}
          </AlertDescription>
        </Alert>
      )}

      {!isSped && (
        <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
          <CardContent className="p-0">
            <div className="border-b border-slate-800/80 px-6 py-4">
              <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="relative w-full max-w-xl">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder={searchPlaceholder}
                    className="border-slate-700 bg-slate-900/80 pl-10 text-slate-100 placeholder:text-slate-400 focus-visible:ring-sky-500"
                  />
                </div>
                <div className="text-xs uppercase tracking-[0.24em] text-slate-400">
                  Busca aplicada em: {detailMode === 'nota' ? 'detalhamento por nota' : 'detalhamento por regiao'}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {levelButtons.map((button) => (
                  <Button
                    key={button.key}
                    type="button"
                    variant="outline"
                    onClick={button.onClick}
                    className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800"
                  >
                    <span className="flex flex-col items-start gap-1">
                      <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                        {button.title}
                      </span>
                      <span className="text-sm font-medium text-slate-100">
                        {button.isOpen ? 'Fechar visualizacao detalhada' : 'Abrir visualizacao detalhada'}
                      </span>
                    </span>
                  </Button>
                ))}
              </div>
            </div>

            {activeHasResults ? (
              detailMode === 'nota' ? (
                <div className="max-h-[70vh] overflow-y-auto">
                  <DetalhamentoVendasNotaMode
                    notas={filteredNotas}
                    openNoteValues={openNoteValues}
                    onOpenNoteValuesChange={setOpenNoteValues}
                    openNoteClientValues={openNoteClientValues}
                    onOpenNoteClientValuesChange={setOpenNoteClientValues}
                    openNcmValues={openNcmValues}
                    onOpenNcmValuesChange={setOpenNcmValues}
                  />
                </div>
              ) : (
                <DetalhamentoVendasRegiaoMode
                  regionHierarchy={filteredRegionHierarchy}
                  openRegionStateValues={openRegionStateValues}
                  onOpenRegionStateValuesChange={setOpenRegionStateValues}
                  openRegionCityValues={openRegionCityValues}
                  onOpenRegionCityValuesChange={setOpenRegionCityValues}
                  openRegionClientValues={openRegionClientValues}
                  onOpenRegionClientValuesChange={setOpenRegionClientValues}
                />
              )
            ) : (
              <div className="p-6 text-sm text-slate-300">
                {searchTerm.trim()
                  ? 'Nenhum detalhamento encontrado para a pesquisa informada neste modo.'
                  : 'Nenhuma nota de venda encontrada para o periodo selecionado.'}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
