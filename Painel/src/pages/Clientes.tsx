import { useMemo, useState } from 'react';
import { Receipt, ShieldAlert, TrendingUp } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
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

      <div className="space-y-3">
        <Input
          placeholder="Buscar clientes..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="max-w-sm"
        />

        <RankingCard
          title="Ranking de Clientes"
          description="Lista de clientes por participacao no faturamento com indicacao simples de risco"
          items={topClientesItems}
          isLoading={kpisQuery.isLoading}
          loadingMessage="Carregando clientes..."
          emptyMessage="Nenhum cliente encontrado."
          totalValue={formatCurrency(totalReceita)}
          listClassName="max-h-[420px] overflow-y-auto pr-1"
          showAbcReport={false}
          showAbcClassification={false}
        />
      </div>
    </div>
  );
}
