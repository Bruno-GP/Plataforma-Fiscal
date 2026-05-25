import { useMemo, useState } from 'react';
import { Search, Receipt, ShieldAlert, TrendingUp, Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

import { useAuth } from '@/contexts/AuthContext';
import { getLatestFiscalEntry, useFiscalYears } from '@/hooks/useFiscalYears';
import { parseDecimal } from '@/services/nfe';
import { createFiscalSourceApi } from '@/services/fiscalSource';
import { createFiscalQueryKey } from '@/utils/fiscalPeriod';
import { formatCurrency, hasValidEmitenteCnpj, monthLabels } from '@/utils/formatters';
import { aggregateClientKpis, buildClientRiskItems } from '@/utils/rankingUtils';

import { Header } from './components/Header';
import { RankingCard } from './components/RankingCard';
import { StatCard } from './components/StatCard';

export default function Clientes() {
  const [search, setSearch] = useState('');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');
  const { user } = useAuth();
  const fiscalApi = createFiscalSourceApi(user?.tem_sped);

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const kpisQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'kpis-clientes',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
    }),
    queryFn: () => fiscalApi.kpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const resultados = kpisQuery.data?.resultados ?? [];
  const latestResult = useMemo(() => getLatestFiscalEntry(resultados), [resultados]);
  const fallbackYear = latestResult?.periodo_ano ?? new Date().getFullYear();
  const { availableYears, selectedYearNumber } = useFiscalYears({
    entries: resultados,
    selectedYear,
    setSelectedYear,
    fallbackYear,
  });

  const safeYear = selectedYearNumber;

  const selectedPeriodKpis = useMemo(() => {
    const filteredByYear = resultados.filter((item) => item.periodo_ano === safeYear);

    if (selectedMonth !== 'all') {
      const selectedMonthNumber = Number.parseInt(selectedMonth, 10);
      return filteredByYear.find((item) => item.periodo_mes === selectedMonthNumber)?.kpis;
    }

    if (!filteredByYear.length) {
      return undefined;
    }

    return aggregateClientKpis(filteredByYear);
  }, [resultados, safeYear, selectedMonth]);

  const totalReceita = parseDecimal(selectedPeriodKpis?.total_vendas ?? 0);
  const topClientes = useMemo(() => selectedPeriodKpis?.top_clientes ?? [], [selectedPeriodKpis]);
  const ticketMedioPorCliente = topClientes.length > 0 ? totalReceita / topClientes.length : 0;

  const clientesComRisco = useMemo(
    () =>
    buildClientRiskItems({
      resultados,
      topClientes,
      totalReceita,
    }),
    [resultados, topClientes, totalReceita],
  );

  const filteredClientes = useMemo(
    () =>
      clientesComRisco.filter((client) =>
        client.cliente.toLowerCase().includes(search.toLowerCase()),
      ),
    [clientesComRisco, search],
  );

  const topClientesItems = filteredClientes.map((cliente, index) => ({
    key: `${cliente.cliente}-${index}`,
    title: cliente.cliente,
    subtitle:
      cliente.percentual !== null
        ? `${cliente.percentual.toFixed(1)}% do faturamento`
        : 'Participacao nao informada',
    value: formatCurrency(cliente.valorTotal),
    rawValue: cliente.valorTotal,
    percent: cliente.percentual,
    badgeLabel: cliente.temRisco ? 'Com risco de perda' : 'Sem risco de perda',
    badgeClassName: cliente.temRisco
      ? 'border-rose-500/40 bg-rose-500/15 text-rose-300'
      : 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300',
  }));

  const clientesEmRisco = filteredClientes.filter((cliente) => cliente.temRisco).length;
  const clientesSemRisco = filteredClientes.filter((cliente) => !cliente.temRisco).length;

  const stats = [
    {
      title: 'Faturamento por Cliente',
      value: formatCurrency(totalReceita),
      description: 'Total no periodo selecionado',
      icon: TrendingUp,
      trend: 'up',
      accentClass: 'border-l-sky-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Clientes com Risco',
      value: String(clientesEmRisco),
      description: `${clientesSemRisco} sem risco`,
      icon: ShieldAlert,
      trend: clientesEmRisco > 0 ? 'down' : 'up',
      accentClass: 'border-l-rose-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Ticket Medio por Cliente',
      value: formatCurrency(ticketMedioPorCliente),
      description: `${topClientes.length} clientes no ranking`,
      icon: Receipt,
      trend: 'up',
      accentClass: 'border-l-amber-400',
      appendPreviousMonthLabel: false,
    },
  ] as const;

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Clientes"
        subtitle="Visao consolidada de faturamento e risco de perda"
        selectedMonth={selectedMonth}
        selectedYear={String(safeYear)}
        availableYears={availableYears.length ? availableYears : [safeYear]}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      {kpisQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar clientes</AlertTitle>
          <AlertDescription>
            Nao foi possivel buscar o ranking de clientes na API.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={kpisQuery.isLoading} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.8fr)]">
        <div className="space-y-4">
          <div className="flex flex-col gap-3 rounded-lg border border-slate-700/80 bg-slate-950/25 p-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-100">Listagem de clientes</p>
              <p className="text-xs text-slate-400">{filteredClientes.length} clientes no recorte atual</p>
            </div>
            <div className="relative w-full md:max-w-sm">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <Input
                placeholder="Buscar clientes..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          <RankingCard
            title="Ranking de Clientes"
            description="Clientes por participacao no faturamento e indicacao de risco"
            items={topClientesItems}
            isLoading={kpisQuery.isLoading}
            loadingMessage="Carregando clientes..."
            emptyMessage="Nenhum cliente encontrado."
            totalValue={formatCurrency(totalReceita)}
            listClassName="max-h-[520px] overflow-y-auto pr-1"
            showAbcReport={false}
            showAbcClassification={false}
          />
        </div>

        <div className="space-y-6">
          <Card className="overflow-hidden">
            <CardHeader className="tv-panel-header">
              <CardTitle>Distribuicao de risco</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 p-5">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-300">Baixo</p>
                  <p className="mt-2 text-3xl font-bold text-slate-50">{clientesSemRisco}</p>
                </div>
                <div className="rounded-md border border-rose-400/25 bg-rose-400/10 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-rose-300">Critico</p>
                  <p className="mt-2 text-3xl font-bold text-slate-50">{clientesEmRisco}</p>
                </div>
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="text-slate-300">Conformidade geral</span>
                  <span className="font-semibold text-emerald-300">
                    {filteredClientes.length
                      ? `${Math.round((clientesSemRisco / filteredClientes.length) * 100)}%`
                      : '0%'}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-950">
                  <div
                    className="h-full rounded-full bg-emerald-400"
                    style={{
                      width: filteredClientes.length
                        ? `${Math.round((clientesSemRisco / filteredClientes.length) * 100)}%`
                        : '0%',
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader className="tv-panel-header">
              <CardTitle>Maiores contribuintes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-5">
              {topClientesItems.slice(0, 4).map((cliente, index) => (
                <div key={cliente.key} className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-1 py-2">
                  <span className="font-mono text-sm font-semibold text-sky-300">{String(index + 1).padStart(2, '0')}</span>
                  <span className="min-w-0">
                    <span className="block truncate font-semibold text-slate-100">{cliente.title}</span>
                    <span className="text-xs text-slate-400">{cliente.subtitle}</span>
                  </span>
                  <span className="text-sm font-semibold text-slate-50">{cliente.percent?.toFixed(1) ?? '0.0'}%</span>
                </div>
              ))}

              {!topClientesItems.length && (
                <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/30 px-4 py-8 text-center text-sm text-slate-400">
                  <Users className="mx-auto mb-2 h-5 w-5" />
                  Nenhum cliente no recorte atual.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
