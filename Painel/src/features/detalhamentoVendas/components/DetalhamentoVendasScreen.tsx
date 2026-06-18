import { ArrowRight, Search } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

import { Header } from '@/pages/components/Header';
import { StatCard } from '@/pages/components/StatCard';
import {
  DetalhamentoFiscalHierarquiaMode,
} from '@/pages/components/Detalhamento/DetalhamentoFiscalHierarquiaMode';
import { DetalhamentoVendasDashboardMode } from '@/pages/components/Detalhamento/DetalhamentoVendasDashboardMode';
import { DetalhamentoVendasFiscalMode } from '@/pages/components/Detalhamento/DetalhamentoVendasFiscalMode';
import { DetalhamentoVendasModeSelector } from '@/pages/components/Detalhamento/DetalhamentoVendasModeSelector';
import { DetalhamentoVendasNotaMode } from '@/pages/components/Detalhamento/DetalhamentoVendasNotaMode';
import { DetalhamentoVendasRegiaoMode } from '@/pages/components/Detalhamento/DetalhamentoVendasRegiaoMode';

import { useDetalhamentoVendas } from '../hooks/useDetalhamentoVendas';

export function DetalhamentoVendasScreen() {
  const {
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
    detailScopeLabel,
    detailSummaryText,
    emptyDetailMessage,
    notasInfiniteQuery,
    loadMoreRef,
    filteredNotas,
    filteredRegionHierarchy,
    spedFiscalHierarchy,
    spedRegionHierarchy,
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
  } = useDetalhamentoVendas();

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Detalhamento de vendas"
        subtitle="Visao de dashboard e expansao hierarquica por nota, regiao ou leitura fiscal."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="stat-card-grid">
        {stats.map((stat) => <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />)}
      </div>

      <div className="flex flex-wrap gap-3 border-y border-slate-800/80 py-4">
        {[{ key: 'grafica' as const, title: 'Visao grafica' }, { key: 'detalhada' as const, title: 'Visao detalhada' }].map((button) => {
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
                <h2 className="text-2xl font-semibold tracking-tight">
                  {isSped ? (detailMode === 'fiscal' ? 'Expansao fiscal em 2 niveis' : 'Expansao em 4 niveis para SPED') : 'Expansao em 4 niveis'}
                </h2>
                <p className="max-w-3xl text-sm text-slate-300">
                  {isSped
                    ? 'No SPED, o detalhamento usa a hierarquia fiscal existente para leitura por regiao ou por NCM.'
                    : 'Alterne entre leitura por nota ou por regiao e abra a hierarquia em camadas ate chegar aos produtos.'}
                </p>
              </div>
              <Button asChild variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100">
                <Link to="/analise-vendas">
                  Voltar a Analise de Vendas
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
            <DetalhamentoVendasModeSelector detailMode={detailMode} onChange={setDetailMode} options={modeOptions} />
          </CardContent>
        </Card>
      )}

      {detalhamentoError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar o detalhamento</AlertTitle>
          <AlertDescription>
            {detalhamentoError instanceof Error ? detalhamentoError.message : 'Nao foi possivel consultar o detalhamento deste periodo.'}
          </AlertDescription>
        </Alert>
      )}

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
                  <Input
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder={searchPlaceholder}
                    className="border-slate-700 bg-slate-900/80 pl-10 text-slate-100 placeholder:text-slate-400 focus-visible:ring-sky-500"
                  />
                </div>
                <div className="text-xs uppercase tracking-[0.24em] text-slate-400">Busca aplicada em: {detailScopeLabel}</div>
              </div>

              <div className="mb-4 text-xs text-slate-400">{detailSummaryText}</div>

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
                      <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">{button.title}</span>
                      <span className="text-sm font-medium text-slate-100">{button.isOpen ? 'Fechar visualizacao detalhada' : 'Abrir visualizacao detalhada'}</span>
                    </span>
                  </Button>
                ))}
              </div>
            </div>

            {activeHasResults ? (
              !isSped ? (
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
                    <div ref={loadMoreRef} className="px-6 py-4 text-center text-sm text-slate-400">
                      {notasInfiniteQuery.isFetchingNextPage
                        ? 'Carregando mais notas...'
                        : notasInfiniteQuery.hasNextPage
                          ? 'Role para baixo para carregar mais 100 notas.'
                          : filteredNotas.length > 0
                            ? 'Todas as notas carregadas.'
                            : null}
                    </div>
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
              ) : detailMode === 'fiscal' ? (
                <DetalhamentoVendasFiscalMode
                  hierarchy={spedFiscalHierarchy}
                  openNcmValues={openFiscalNcmValues}
                  onOpenNcmValuesChange={setOpenFiscalNcmValues}
                />
              ) : (
                <DetalhamentoFiscalHierarquiaMode
                  hierarchy={spedRegionHierarchy}
                  openStateValues={openSpedRegionStateValues}
                  onOpenStateValuesChange={setOpenSpedRegionStateValues}
                  openCityValues={openSpedRegionCityValues}
                  onOpenCityValuesChange={setOpenSpedRegionCityValues}
                  openNcmValues={openSpedRegionNcmValues}
                  onOpenNcmValuesChange={setOpenSpedRegionNcmValues}
                />
              )
            ) : (
              <div className="p-6 text-sm text-slate-300">{emptyDetailMessage}</div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
