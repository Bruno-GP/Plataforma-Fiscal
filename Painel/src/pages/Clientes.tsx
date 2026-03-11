import { useMemo, useState } from 'react';
import { Percent, TrendingUp, Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/contexts/AuthContext';
import { fetchNfeKpis, parseDecimal } from '@/services/nfe';
import { fetchSpedKpis } from '@/services/sped';

import { RankingCard } from './components/RankingCard';
import { StatCard } from './components/StatCard';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);

const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? "").replace(/\D/g, "");
  return digits.length === 14 && ![...digits].every((digit) => digit === "0");
};

export default function Clientes() {
  const [search, setSearch] = useState("");
  const { user } = useAuth();
  const usaSped = Boolean(user?.tem_sped);
  
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const kpisQuery = useQuery({
    queryKey: ["kpis-clientes", usaSped ? "sped" : "xml", emitenteCnpj],
    queryFn: () =>
      usaSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 12 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 12 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const latestKpi = useMemo(() => {
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

  const totalReceita = parseDecimal(latestKpi?.kpis.total_vendas ?? 0);
  const totalImpostos =
    parseDecimal(latestKpi?.kpis.total_icms ?? 0) +
    parseDecimal(latestKpi?.kpis.total_ipi ?? 0) +
    parseDecimal(latestKpi?.kpis.total_pis ?? 0) +
    parseDecimal(latestKpi?.kpis.total_cofins ?? 0);
  const margem =
    totalReceita > 0
      ? ((totalReceita - totalImpostos) / totalReceita) * 100
      : 0;
  
  const topClientes = latestKpi?.kpis.top_clientes ?? [];
  const filteredClientes = useMemo(
    () =>
      topClientes.filter((client) =>
        (client.cliente ?? '').toLowerCase().includes(search.toLowerCase()),
      ),
    [search, topClientes],
  );

  const topClientesItems = filteredClientes.map((cliente, index) => {
    const valorTotal = parseDecimal(cliente.valor_total ?? 0);
    const percentual =
      cliente.percentual !== undefined && cliente.percentual !== null
        ? parseDecimal(cliente.percentual)
        : totalReceita > 0
          ? (valorTotal / totalReceita) * 100
          : null;

    return {
      key: `${cliente.cliente}-${index}`,
      title: cliente.cliente ?? 'Cliente não identificado',
      subtitle:
        percentual !== null
          ? `${percentual.toFixed(1)}% do faturamento`
          : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const stats = [
    {
      title: 'Faturamento por Cliente',
      value: formatCurrency(totalReceita),
      description: 'Total no último período',
      icon: TrendingUp,
      trend: 'up',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Total de Clientes no Ranking',
      value: String(topClientes.length),
      description: `${filteredClientes.length} após filtro`,
      icon: Users,
      trend: 'up',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Margem',
      value: `${margem.toFixed(1)}%`,
      description: formatPercent(margem),
      icon: Percent,
      trend: margem >= 0 ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ] as const;

  return (
    <div className="space-y-6 py-6">
      <div>
        <h1 className="text-3xl font-bold">Análise de Clientes</h1>
        <p className="text-muted-foreground">
          Visão consolidada de faturamento e desempenho
        </p>
      </div>

      {kpisQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar clientes</AlertTitle>
          <AlertDescription>
            Não foi possível buscar o ranking de clientes na API.
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
          description="Lista de clientes por participação no faturamento"
          items={topClientesItems}
          isLoading={kpisQuery.isLoading}
          loadingMessage="Carregando clientes..."
          emptyMessage="Nenhum cliente encontrado."
          totalValue={formatCurrency(totalReceita)}
          listClassName="max-h-[420px] overflow-y-auto pr-1"
        />
      </div>
    </div>
  );
}