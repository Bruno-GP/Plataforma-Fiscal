import { useEffect, useMemo, useState } from 'react';
import { TrendingUp, Users, Receipt, Percent } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
// import { Button } from '@/components/ui/button';

import { Header } from '../components/Header';
import { RankingCard } from '../components/RankingCard';
import { StatCard } from '../components/StatCard';

import { fetchNfeKpis, fetchNfeKpisComparativoAtual, parseDecimal } from '@/services/nfe';
import { useAuth } from '@/contexts/AuthContext'
import { fetchSpedKpis } from '@/services/sped';
// import { useChat } from '@/contexts/ChatContext';
import { monthLabels } from '../faturamento/utils/utils';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);

const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

const ufToRegion: Record<string, string> = {
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
  MT: 'Centro-Oeste',
  MS: 'Centro-Oeste',
  MG: 'Sudeste',
  PA: 'Norte',
  PB: 'Nordeste',
  PR: 'Sul',
  PE: 'Nordeste',
  PI: 'Nordeste',
  RJ: 'Sudeste',
  RN: 'Nordeste',
  RS: 'Sul',
  RO: 'Norte',
  RR: 'Norte',
  SC: 'Sul',
  SP: 'Sudeste',
  SE: 'Nordeste',
  TO: 'Norte',
};

const extractUfFromCity = (cityLabel?: string) => {
  if (!cityLabel) {
    return null;
  }

  const normalized = cityLabel.toUpperCase();
  const match = normalized.match(/(?:-|\/|\(|\s)([A-Z]{2})(?:\)|$)/);

  if (!match) {
    return null;
  }

  const uf = match[1];
  return ufToRegion[uf] ? uf : null;
};


const regionMapAreas: Array<{ regiao: string; path: string; labelX: number; labelY: number }> = [
  {
    regiao: 'Norte',
    path: 'M48 42 L116 18 L196 36 L182 92 L126 112 L74 94 Z',
    labelX: 128,
    labelY: 60,
  },
  {
    regiao: 'Nordeste',
    path: 'M196 36 L254 48 L280 94 L244 138 L196 122 L182 92 Z',
    labelX: 238,
    labelY: 92,
  },
  {
    regiao: 'Centro-Oeste',
    path: 'M74 94 L126 112 L148 178 L104 212 L62 170 Z',
    labelX: 108,
    labelY: 154,
  },
  {
    regiao: 'Sudeste',
    path: 'M148 178 L208 162 L236 204 L198 236 L154 224 Z',
    labelX: 193,
    labelY: 201,
  },
  {
    regiao: 'Sul',
    path: 'M154 224 L198 236 L186 292 L146 312 L124 266 Z',
    labelX: 162,
    labelY: 270,
  },
];

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

interface DashboardProps {
  title?: string;
  subtitle?: string;
}

export default function Dashboard({ 
  title = 'Dashboard', 
  subtitle = 'Visão geral do seu negócio' 
}: DashboardProps) {
  const { user } = useAuth();
  // const { toggleChat, sendMessage, isOpen } = useChat();

  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const usaSped = Boolean(user?.tem_sped);

  const monthNumber = Number.parseInt(selectedMonth, 10);
  const year = Number.parseInt(selectedYear, 10);

  const yearsQuery = useQuery({
    queryKey: ['kpis-years', usaSped ? 'sped' : 'xml', emitenteCnpj],
    queryFn: () => (usaSped ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }) : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const kpisQuery = useQuery({
    queryKey: ['kpis', usaSped ? 'sped' : 'xml', emitenteCnpj, year],
    queryFn: () => (usaSped ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year }) : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year })),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const previousYearQuery = useQuery({
    queryKey: ['kpis', usaSped ? 'sped' : 'xml', emitenteCnpj, year - 1],
    queryFn: () => (usaSped ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year - 1 }) : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, periodo_ano: year - 1 })),
    enabled: hasEmitenteCnpj && year > 2000,
    staleTime: 5 * 60 * 1000,
  });

  const isAllMonths = selectedMonth === 'all';

  const filteredResultados = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    if (isAllMonths) {
      return resultados;
    }
    return resultados.filter((item) => item.periodo_mes === monthNumber);
  }, [isAllMonths, kpisQuery.data, monthNumber]);

  const aggregatedData = useMemo(() => {
    const totals = {
      totalSales: 0,
      totalNotes: 0,
      totalTaxes: 0,
    };
    const topClientesMap = new Map<string, number>();
    const topProdutosMap = new Map<string, number>();
    const topCidadesMap = new Map<string, number>();

    filteredResultados.forEach((item) => {
      const kpis = item.kpis;
      totals.totalSales += parseDecimal(kpis.total_vendas ?? 0);
      totals.totalNotes += kpis.quantidade_notas ?? 0;
      totals.totalTaxes += parseDecimal(kpis.total_icms ?? 0)
        + parseDecimal(kpis.total_ipi ?? 0)
        + parseDecimal(kpis.total_pis ?? 0)
        + parseDecimal(kpis.total_cofins ?? 0);

      (kpis.top_clientes ?? []).forEach((cliente, index) => {
        const nome = cliente.cliente ?? `Cliente não identificado ${index + 1}`;
        const atual = topClientesMap.get(nome) ?? 0;
        topClientesMap.set(nome, atual + parseDecimal(cliente.valor_total ?? 0));
      });

      (kpis.top_produtos ?? []).forEach((produto, index) => {
        const nome = produto.produto ?? `Produto não identificado ${index + 1}`;
        const atual = topProdutosMap.get(nome) ?? 0;
        topProdutosMap.set(nome, atual + parseDecimal(produto.valor_total ?? 0));
      });

      (kpis.top_cidades ?? []).forEach((cidade, index) => {
        const nome = cidade.cidade ?? `Cidade não identificada ${index + 1}`;
        const atual = topCidadesMap.get(nome) ?? 0;
        topCidadesMap.set(nome, atual + parseDecimal(cidade.valor_total ?? 0));
      });
    });

    return {
      totals,
      topClientesMap,
      topProdutosMap,
      topCidadesMap,
    };
  }, [filteredResultados]);

  const latestKpi = useMemo(() => {
    return [...filteredResultados].sort((a, b) => {
      const anoA = a.periodo_ano ?? 0;
      const anoB = b.periodo_ano ?? 0;
      if (anoA !== anoB) {
        return anoB - anoA;
      }
      return (b.periodo_mes ?? 0) - (a.periodo_mes ?? 0);
    })[0];
  }, [filteredResultados]);

  const previousPeriodKpi = useMemo(() => {
    if (!latestKpi?.periodo_mes || !latestKpi?.periodo_ano) {
      return null;
    }

    const currentMonth = latestKpi.periodo_mes;
    const currentYear = latestKpi.periodo_ano;
    const previousMonth = currentMonth - 1;

    if (previousMonth >= 1) {
      return (
        (kpisQuery.data?.resultados ?? []).find(
          (item) => item.periodo_mes === previousMonth && item.periodo_ano === currentYear
        ) ?? null
      );
    }

    return (
      (previousYearQuery.data?.resultados ?? []).find(
        (item) => item.periodo_mes === 12 && item.periodo_ano === currentYear - 1
      ) ?? null
    );
  }, [kpisQuery.data, latestKpi, previousYearQuery.data]);

  const faturamentoPeriodo = useMemo(() => {
    if (isAllMonths) {
      const months = filteredResultados
        .map((item) => item.periodo_mes)
        .filter((item): item is number => Boolean(item));
      if (!months.length) {
        return null;
      }
      const minMonth = Math.min(...months);
      const maxMonth = Math.max(...months);
      return `${String(minMonth).padStart(2, '0')}/${selectedYear} a ${String(maxMonth).padStart(2, '0')}/${selectedYear}`;
    }

    const mes = latestKpi?.periodo_mes;
    const ano = latestKpi?.periodo_ano;

    if (!mes || !ano) {
      return null;
    }

    return `${String(mes).padStart(2, '0')}/${ano}`;
  }, [filteredResultados, isAllMonths, latestKpi?.periodo_mes, latestKpi?.periodo_ano, selectedYear]);

  const stats = useMemo(() => {
    const currentKpis = latestKpi?.kpis;
    const previousKpis = previousPeriodKpi?.kpis;

    const previousYearResultados = previousYearQuery.data?.resultados ?? [];

    const totals = isAllMonths
      ? aggregatedData.totals
      : {
        totalSales: parseDecimal(currentKpis?.total_vendas ?? 0),
        totalNotes: currentKpis?.quantidade_notas ?? 0,
        totalTaxes: parseDecimal(currentKpis?.total_icms ?? 0)
          + parseDecimal(currentKpis?.total_ipi ?? 0)
          + parseDecimal(currentKpis?.total_pis ?? 0)
          + parseDecimal(currentKpis?.total_cofins ?? 0),
      };

    const previousTotals = isAllMonths
      ? previousYearResultados.reduce(
        (acc, item) => {
          acc.totalSales += parseDecimal(item.kpis.total_vendas ?? 0);
          acc.totalNotes += item.kpis.quantidade_notas ?? 0;
          acc.totalTaxes += parseDecimal(item.kpis.total_icms ?? 0)
            + parseDecimal(item.kpis.total_ipi ?? 0)
            + parseDecimal(item.kpis.total_pis ?? 0)
            + parseDecimal(item.kpis.total_cofins ?? 0);
          return acc;
        },
        { totalSales: 0, totalNotes: 0, totalTaxes: 0 }
      )
      : {
        totalSales: parseDecimal(previousKpis?.total_vendas ?? 0),
        totalNotes: previousKpis?.quantidade_notas ?? 0,
        totalTaxes: parseDecimal(previousKpis?.total_icms ?? 0)
          + parseDecimal(previousKpis?.total_ipi ?? 0)
          + parseDecimal(previousKpis?.total_pis ?? 0)
          + parseDecimal(previousKpis?.total_cofins ?? 0),
      };

    const totalSalesChange = previousTotals.totalSales
      ? ((totals.totalSales - previousTotals.totalSales) / previousTotals.totalSales) * 100
      : 0;
    const totalNotesChange = previousTotals.totalNotes
      ? ((totals.totalNotes - previousTotals.totalNotes) / previousTotals.totalNotes) * 100
      : 0;
    const ticketMedio = totals.totalNotes ? totals.totalSales / totals.totalNotes : 0;
    const previousTicketMedio = previousTotals.totalNotes
      ? previousTotals.totalSales / previousTotals.totalNotes
      : 0;
    const ticketChange = previousTicketMedio
      ? ((ticketMedio - previousTicketMedio) / previousTicketMedio) * 100
      : 0;
    const totalTaxesChange = previousTotals.totalTaxes
      ? ((totals.totalTaxes - previousTotals.totalTaxes) / previousTotals.totalTaxes) * 100
      : 0;

    return [
      {
        title: `Faturamento Mensal${faturamentoPeriodo ? ` (Período ${faturamentoPeriodo})` : ''}`,
        value: formatCurrency(totals.totalSales),
        description: formatPercent(totalSalesChange),
        icon: TrendingUp,
        trend: totalSalesChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-sky-500',
      },
      {
        title: 'Notas Emitidas',
        value: totals.totalNotes.toString(),
        description: formatPercent(totalNotesChange),
        icon: Receipt,
        trend: totalNotesChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-emerald-500',
      },
      {
        title: 'Ticket Médio',
        value: formatCurrency(ticketMedio),
        description: formatPercent(ticketChange),
        icon: Users,
        trend: ticketChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-amber-400',
      },
      {
        title: 'Impostos sobre vendas',
        value: formatCurrency(totals.totalTaxes),
        description: formatPercent(totalTaxesChange),
        icon: Percent,
        trend: totalTaxesChange >= 0 ? 'up' : 'down',
        accentClass: 'border-l-violet-500',
      },
    ];
    }, [aggregatedData.totals, faturamentoPeriodo, isAllMonths, latestKpi, previousPeriodKpi, previousYearQuery.data]);

  const aggregatedTopClientes = useMemo(() => {
    return [...aggregatedData.topClientesMap.entries()]
      .map(([cliente, valor_total]) => ({ cliente, valor_total }))
      .sort((a, b) => b.valor_total - a.valor_total)
      .slice(0, 5);
  }, [aggregatedData.topClientesMap]);

  const aggregatedTopProdutos = useMemo(() => {
    return [...aggregatedData.topProdutosMap.entries()]
      .map(([produto, valor_total]) => ({ produto, valor_total }))
      .sort((a, b) => b.valor_total - a.valor_total)
      .slice(0, 5);
  }, [aggregatedData.topProdutosMap]);

  const aggregatedTopCidades = useMemo(() => {
    return [...aggregatedData.topCidadesMap.entries()]
      .map(([cidade, valor_total]) => ({ cidade, valor_total }))
      .sort((a, b) => b.valor_total - a.valor_total)
      .slice(0, 5);
  }, [aggregatedData.topCidadesMap]);

  const totalFaturamento = isAllMonths
    ? aggregatedData.totals.totalSales
    : parseDecimal(latestKpi?.kpis.total_vendas ?? 0);
  const topClientes = useMemo(
    () => (isAllMonths ? aggregatedTopClientes : (latestKpi?.kpis.top_clientes ?? [])),
    [aggregatedTopClientes, isAllMonths, latestKpi?.kpis.top_clientes],
  );
  const topProdutos = useMemo(
    () => (isAllMonths ? aggregatedTopProdutos : (latestKpi?.kpis.top_produtos ?? [])),
    [aggregatedTopProdutos, isAllMonths, latestKpi?.kpis.top_produtos],
  );
  const topCidades = useMemo(
    () => (isAllMonths ? aggregatedTopCidades : (latestKpi?.kpis.top_cidades ?? [])),
    [aggregatedTopCidades, isAllMonths, latestKpi?.kpis.top_cidades],
  );

  const resolvePercentual = (percentual?: number | string, valorTotal?: number | string) => {
    if (percentual !== undefined && percentual !== null) {
      return parseDecimal(percentual);
    }

    const valor = parseDecimal(valorTotal ?? 0);
    if (!totalFaturamento || !valor) {
      return null;
    }

    return (valor / totalFaturamento) * 100;
  };

  const isLoading = kpisQuery.isLoading || previousYearQuery.isLoading;
  const hasError = kpisQuery.isError || previousYearQuery.isError;

  const topClientesItems = topClientes.map((cliente, index) => {
    const percentual = resolvePercentual(cliente.percentual, cliente.valor_total);
    const valorTotal = parseDecimal(cliente.valor_total ?? 0);

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

  const topProdutosItems = topProdutos.map((produto, index) => {
    const percentual = resolvePercentual(produto.percentual, produto.valor_total);
    const valorTotal = parseDecimal(produto.valor_total ?? 0);

    return {
      key: `${produto.produto}-${index}`,
      title: produto.produto ?? 'Produto não identificado',
      subtitle:
        percentual !== null
          ? `${percentual.toFixed(1)}% do faturamento`
          : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const topCidadesItems = topCidades.map((cidade, index) => {
    const percentual = resolvePercentual(cidade.percentual, cidade.valor_total);
    const valorTotal = parseDecimal(cidade.valor_total ?? 0);

    return {
      key: `${cidade.cidade}-${index}`,
      title: cidade.cidade ?? 'Cidade não identificada',
      subtitle:
        percentual !== null
          ? `${percentual.toFixed(1)}% do faturamento`
          : 'Participação não informada',
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const vendasPorRegiao = useMemo(() => {
    const regiaoMap = new Map<string, number>([
      ['Norte', 0],
      ['Nordeste', 0],
      ['Centro-Oeste', 0],
      ['Sudeste', 0],
      ['Sul', 0],
      ['Não identificado', 0],
    ]);

    topCidades.forEach((cidade) => {
      const valor = parseDecimal(cidade.valor_total ?? 0);
      const uf = extractUfFromCity(cidade.cidade);
      const regiao = uf ? ufToRegion[uf] : 'Não identificado';
      regiaoMap.set(regiao, (regiaoMap.get(regiao) ?? 0) + valor);
    });

    const totalRegional = [...regiaoMap.values()].reduce((acc, current) => acc + current, 0);

    return [...regiaoMap.entries()]
      .map(([regiao, valor]) => ({
        regiao,
        valor,
        percentual: totalRegional > 0 ? (valor / totalRegional) * 100 : 0,
      }))
      .sort((a, b) => b.valor - a.valor);
  }, [topCidades]);

  const dadosRegiaoMapa = useMemo(() => {
    const mapa = new Map(vendasPorRegiao.map((item) => [item.regiao, item]));
    return regionMapAreas.map((area) => {
      const valorRegiao = mapa.get(area.regiao);
      return {
        ...area,
        valor: valorRegiao?.valor ?? 0,
        percentual: valorRegiao?.percentual ?? 0,
      };
    });
  }, [vendasPorRegiao]);

  const maiorPercentualRegiao = useMemo(
    () => Math.max(...dadosRegiaoMapa.map((item) => item.percentual), 0),
    [dadosRegiaoMapa],
  );

  const getRegionFill = (percentual: number) => {
    if (percentual <= 0) {
      return 'hsl(var(--muted))';
    }

    const intensidade = maiorPercentualRegiao > 0 ? percentual / maiorPercentualRegiao : 0;
    const alpha = 0.25 + intensidade * 0.75;
    return `hsl(var(--primary) / ${Math.min(alpha, 1).toFixed(2)})`;
  };

  const naoIdentificado = vendasPorRegiao.find((item) => item.regiao === 'Não identificado');

  const yearOptions = useMemo(() => {
    const resultados = yearsQuery.data?.resultados ?? [];
    const uniqueYears = new Set<number>();

    resultados.forEach((item) => {
      if (item.periodo_ano) {
        uniqueYears.add(item.periodo_ano);
      }
    });

    return [...uniqueYears].sort((a, b) => b - a);
  }, [yearsQuery.data]);

  const availableYears = yearOptions.length ? yearOptions : [year];

  useEffect(() => {
    if (!yearOptions.length) {
      return;
    }

    if (!yearOptions.includes(year)) {
      setSelectedYear(String(yearOptions[0]));
    }
  }, [year, yearOptions]);

  return (
    <div className="space-y-6">
      <Header
        title={title}
        subtitle={subtitle}
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      {/* <Button onClick={handleAIPlanAction} className="w-fit gap-2">
        <Sparkles className="h-4 w-4" />
        Gerar Plano de Ação com IA
      </Button> */}

      {hasError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar indicadores</AlertTitle>
          <AlertDescription>
            Não foi possível buscar os KPIs mais recentes na API.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={isLoading} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <RankingCard
          title="Top Clientes"
          description="Clientes com maior faturamento no último período"
          items={topClientesItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum cliente registrado."
          totalValue={formatCurrency(totalFaturamento)}
        />
        <RankingCard
          title="Top Produtos"
          description="Itens com maior faturamento no último período"
          items={topProdutosItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhum produto registrado."
          totalValue={formatCurrency(totalFaturamento)}
        />
        <RankingCard
          title="Top Cidades"
          description="Cidades com maior faturamento no último período"
          items={topCidadesItems}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage="Nenhuma cidade registrada."
          totalValue={formatCurrency(totalFaturamento)}
        />
      </div>

      <section className="rounded-xl border bg-background p-4 md:p-6">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-foreground">Mapa de vendas por região</h2>
          <p className="text-sm text-muted-foreground">
            Intensidade do mapa representa a participação de faturamento por região.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <div className="overflow-hidden rounded-lg border bg-muted/20 p-2">
            <svg viewBox="0 0 320 340" className="h-auto w-full" role="img" aria-label="Mapa das regiões do Brasil">
              {dadosRegiaoMapa.map((area) => (
                <g key={area.regiao}>
                  <path
                    d={area.path}
                    fill={getRegionFill(area.percentual)}
                    stroke="hsl(var(--border))"
                    strokeWidth="2"
                  >
                    <title>
                      {`${area.regiao}: ${formatCurrency(area.valor)} (${area.percentual.toFixed(1)}%)`}
                    </title>
                  </path>
                  <text
                    x={area.labelX}
                    y={area.labelY}
                    textAnchor="middle"
                    className="fill-foreground text-[10px] font-medium"
                  >
                    {area.regiao}
                  </text>
                </g>
              ))}
            </svg>
          </div>

          <div className="space-y-3">
            {vendasPorRegiao.filter((item) => item.regiao !== 'Não identificado').map((item) => (
              <div key={item.regiao} className="rounded-md border bg-background p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{item.regiao}</span>
                  <span className="text-muted-foreground">{item.percentual.toFixed(1)}%</span>
                </div>
                <p className="text-sm text-muted-foreground">{formatCurrency(item.valor)}</p>
              </div>
            ))}

            {naoIdentificado && naoIdentificado.valor > 0 && (
              <div className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
                Não identificado: {formatCurrency(naoIdentificado.valor)} ({naoIdentificado.percentual.toFixed(1)}%)
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
