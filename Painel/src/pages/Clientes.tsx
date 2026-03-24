import { useEffect, useMemo, useState } from 'react';
import { Receipt, ShieldAlert, TrendingUp } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';

import { useAuth } from '@/contexts/AuthContext';
import { fetchNfeKpis, parseDecimal } from '@/services/nfe';
import { fetchSpedKpis } from '@/services/sped';
import { monthLabels } from '@/services/utils';

import { Header } from './components/Header';
import { RankingCard } from './components/RankingCard';
import { StatCard } from './components/StatCard';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

interface ClienteComRisco {
  cliente: string;
  valorTotal: number;
  percentual: number | null;
  temRisco: boolean;
}

export default function Clientes() {
  const [search, setSearch] = useState('');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');
  const { user } = useAuth();
  const usaSped = Boolean(user?.tem_sped);

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const kpisQuery = useQuery({
    queryKey: ['kpis-clientes', usaSped ? 'sped' : 'xml', emitenteCnpj],
    queryFn: () =>
      usaSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const latestResult = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    return [...resultados].sort((a, b) => {
      const anoA = a.periodo_ano ?? 0;
      const anoB = b.periodo_ano ?? 0;
      if (anoA !== anoB) {
        return anoB - anoA;
      }
      return (b.periodo_mes ?? 0) - (a.periodo_mes ?? 0);
    })[0];
  }, [kpisQuery.data]);

  const availableYears = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    const years = new Set<number>();

    resultados.forEach((item) => {
      if (item.periodo_ano) {
        years.add(item.periodo_ano);
      }
    });

    return [...years].sort((a, b) => b - a);
  }, [kpisQuery.data]);

  useEffect(() => {
    if (!availableYears.length) {
      return;
    }

    const parsedYear = Number.parseInt(selectedYear, 10);
    if (!availableYears.includes(parsedYear)) {
      setSelectedYear(String(availableYears[0]));
    }
  }, [availableYears, selectedYear]);

  const safeYear = availableYears.length
    ? Number.parseInt(selectedYear, 10)
    : (latestResult?.periodo_ano ?? new Date().getFullYear());

  const selectedPeriodKpis = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    const filteredByYear = resultados.filter((item) => item.periodo_ano === safeYear);

    if (selectedMonth !== 'all') {
      const selectedMonthNumber = Number.parseInt(selectedMonth, 10);
      return filteredByYear.find((item) => item.periodo_mes === selectedMonthNumber)?.kpis;
    }

    if (!filteredByYear.length) {
      return undefined;
    }

    const topClientesMap = new Map<string, number>();

    const aggregated = filteredByYear.reduce(
      (acc, item) => {
        const kpi = item.kpis;
        acc.total_vendas += parseDecimal(kpi.total_vendas ?? 0);
        acc.total_icms += parseDecimal(kpi.total_icms ?? 0);
        acc.total_ipi += parseDecimal(kpi.total_ipi ?? 0);
        acc.total_pis += parseDecimal(kpi.total_pis ?? 0);
        acc.total_cofins += parseDecimal(kpi.total_cofins ?? 0);

        (kpi.top_clientes ?? []).forEach((cliente) => {
          const name = cliente.cliente ?? 'Cliente nao identificado';
          const value = parseDecimal(cliente.valor_total ?? 0);
          topClientesMap.set(name, (topClientesMap.get(name) ?? 0) + value);
        });

        return acc;
      },
      {
        total_vendas: 0,
        total_icms: 0,
        total_ipi: 0,
        total_pis: 0,
        total_cofins: 0,
      },
    );

    const topClientes = [...topClientesMap.entries()]
      .sort(([, valorA], [, valorB]) => valorB - valorA)
      .map(([cliente, valor_total]) => ({ cliente, valor_total, percentual: undefined }));

    return {
      ...aggregated,
      top_clientes: topClientes,
    };
  }, [kpisQuery.data, safeYear, selectedMonth]);

  const totalReceita = parseDecimal(selectedPeriodKpis?.total_vendas ?? 0);
  const topClientes = useMemo(() => selectedPeriodKpis?.top_clientes ?? [], [selectedPeriodKpis]);
  const ticketMedioPorCliente = topClientes.length > 0 ? totalReceita / topClientes.length : 0;

  const clientesComRisco = useMemo(() => {
    const resultados = (kpisQuery.data?.resultados ?? [])
      .filter((item) => item.periodo_ano && item.periodo_mes)
      .sort((a, b) => {
        const anoA = a.periodo_ano ?? 0;
        const anoB = b.periodo_ano ?? 0;
        if (anoA !== anoB) {
          return anoA - anoB;
        }
        return (a.periodo_mes ?? 0) - (b.periodo_mes ?? 0);
      });

    const latestPeriod = resultados[resultados.length - 1];
    const previousPeriod = resultados[resultados.length - 2];

    const previousMap = new Map<string, number>();
    (previousPeriod?.kpis.top_clientes ?? []).forEach((cliente, index) => {
      const nome = cliente.cliente ?? `Cliente nao identificado ${index + 1}`;
      previousMap.set(nome, parseDecimal(cliente.valor_total ?? 0));
    });

    return topClientes.map((cliente, index) => {
      const nome = cliente.cliente ?? `Cliente nao identificado ${index + 1}`;
      const valorTotal = parseDecimal(cliente.valor_total ?? 0);
      const percentual =
        cliente.percentual !== undefined && cliente.percentual !== null
          ? parseDecimal(cliente.percentual)
          : totalReceita > 0
            ? (valorTotal / totalReceita) * 100
            : null;

      const valorAnterior = previousMap.get(nome) ?? 0;
      const quedaForte = valorAnterior > 0 && valorTotal < valorAnterior * 0.7;
      const saiuDoRanking = valorAnterior > 0 && valorTotal === 0;
      const temRisco = quedaForte || saiuDoRanking;

      return {
        cliente: nome,
        valorTotal,
        percentual,
        temRisco,
      } satisfies ClienteComRisco;
    });
  }, [kpisQuery.data, topClientes, totalReceita]);

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