import { useEffect, useMemo, useState } from 'react';
import { TrendingUp, Users, Receipt, Percent  } from 'lucide-react';
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

const BRAZIL_STATES_GEOJSON_URL =
  'https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson';

const stateNameToUf: Record<string, string> = {
  acre: 'AC',
  alagoas: 'AL',
  amapa: 'AP',
  amazonas: 'AM',
  bahia: 'BA',
  ceara: 'CE',
  'distrito federal': 'DF',
  'espirito santo': 'ES',
  goias: 'GO',
  maranhao: 'MA',
  'mato grosso': 'MT',
  'mato grosso do sul': 'MS',
  'minas gerais': 'MG',
  para: 'PA',
  paraiba: 'PB',
  parana: 'PR',
  pernambuco: 'PE',
  piaui: 'PI',
  'rio de janeiro': 'RJ',
  'rio grande do norte': 'RN',
  'rio grande do sul': 'RS',
  rondonia: 'RO',
  roraima: 'RR',
  'santa catarina': 'SC',
  'sao paulo': 'SP',
  sergipe: 'SE',
  tocantins: 'TO',
};

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

  const normalized = cityLabel.toUpperCase().trim();
  if (/^[A-Z]{2}$/.test(normalized)) {
    return ufToRegion[normalized] ? normalized : null;
  }
  const match = normalized.match(/(?:-|\/|\(|\s)([A-Z]{2})(?:\)|$)/);

  if (!match) {
    return null;
  }

  const uf = match[1];
  return ufToRegion[uf] ? uf : null;
};


type GeoJsonFeature = {
  type: 'Feature';
  properties: {
    name?: string;
    sigla?: string;
  };
  geometry: {
    type: 'Polygon' | 'MultiPolygon';
    coordinates: number[][][] | number[][][][];
  };
};

const normalizeLabel = (value: string) =>
  value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .trim();


type GeoJsonFeatureCollection = {
  type: 'FeatureCollection';
  features: GeoJsonFeature[];
};

const getFeatureRings = (feature: GeoJsonFeature) => {
  if (feature.geometry.type === 'Polygon') {
    return [feature.geometry.coordinates[0]];
  }

  return feature.geometry.coordinates
    .map((polygon) => polygon[0])
    .filter((ring) => ring.length > 0);
};

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

  const brazilMapQuery = useQuery<GeoJsonFeatureCollection>({
    queryKey: ['brazil-states-geojson'],
    queryFn: async () => {
      const response = await fetch(BRAZIL_STATES_GEOJSON_URL);
      if (!response.ok) {
        throw new Error('Não foi possível carregar o GeoJSON do Brasil.');
      }
      return response.json();
    },
    staleTime: 24 * 60 * 60 * 1000,
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

  const geoJsonPorEstado = useMemo(() => {
    const data = brazilMapQuery.data;
    if (!data?.features?.length) {
      return [];
    }

    const salesByState = new Map<string, number>();

    topCidades.forEach((cidade) => {
      const valor = parseDecimal(cidade.valor_total ?? 0);
      const uf = extractUfFromCity(cidade.cidade);
      if (!uf) {
        return;
      }
      salesByState.set(uf, (salesByState.get(uf) ?? 0) + valor);
    });

    const projectedFeatures = data.features
      .map((feature) => {
        const stateName = normalizeLabel(feature.properties.name ?? '');
        const uf = feature.properties.sigla ?? stateNameToUf[stateName];

        if (!uf || !ufToRegion[uf]) {
          return null;
        }

        const rings = getFeatureRings(feature);
        if (!rings.length) {
          return null;
        }

        return {
          uf,
          regiao: ufToRegion[uf],
          rings,
          valor: salesByState.get(uf) ?? 0,
        };
      })
      .filter((item): item is { uf: string; regiao: string; rings: number[][][]; valor: number } => Boolean(item));

    const bounds = projectedFeatures.reduce(
      (acc, item) => {
        item.rings.forEach((ring) => {
          ring.forEach(([lon, lat]) => {
            acc.minLon = Math.min(acc.minLon, lon);
            acc.maxLon = Math.max(acc.maxLon, lon);
            acc.minLat = Math.min(acc.minLat, lat);
            acc.maxLat = Math.max(acc.maxLat, lat);
          });
        });
        return acc;
      },
      {
        minLon: Number.POSITIVE_INFINITY,
        maxLon: Number.NEGATIVE_INFINITY,
        minLat: Number.POSITIVE_INFINITY,
        maxLat: Number.NEGATIVE_INFINITY,
      },
    );

    if (!Number.isFinite(bounds.minLon) || !Number.isFinite(bounds.minLat)) {
      return [];
    }

    const padding = 3;
    const width = 100;
    const height = 100;
    const lonSpan = Math.max(bounds.maxLon - bounds.minLon, 1);
    const latSpan = Math.max(bounds.maxLat - bounds.minLat, 1);
    const scale = Math.min((width - padding * 2) / lonSpan, (height - padding * 2) / latSpan);
    const projectedWidth = lonSpan * scale;
    const projectedHeight = latSpan * scale;
    const offsetX = (width - projectedWidth) / 2;
    const offsetY = (height - projectedHeight) / 2;

    const totalMapSales = projectedFeatures.reduce((acc, item) => acc + item.valor, 0);

    return projectedFeatures.map((item) => {
      const projectedRings = item.rings.map((ring) =>
        ring.map(([lon, lat]) => [
          offsetX + (lon - bounds.minLon) * scale,
          offsetY + (bounds.maxLat - lat) * scale,
        ]),
      );

      const centroid = projectedRings
        .flat()
        .reduce(
          (acc, [x, y], _, arr) => {
            acc[0] += x / arr.length;
            acc[1] += y / arr.length;
            return acc;
          },
          [0, 0],
        );

      return {
        ...item,
        projectedRings,
        centroidX: centroid[0],
        centroidY: centroid[1],
        percentual: totalMapSales > 0 ? (item.valor / totalMapSales) * 100 : 0,
      };
    });
  }, [brazilMapQuery.data, topCidades]);

  const dadosRegiaoMapa = useMemo(() => {
    const regionTotals = new Map<string, number>([
      ['Norte', 0],
      ['Nordeste', 0],
      ['Centro-Oeste', 0],
      ['Sudeste', 0],
      ['Sul', 0],
    ]);

    geoJsonPorEstado.forEach((estado) => {
      regionTotals.set(estado.regiao, (regionTotals.get(estado.regiao) ?? 0) + estado.valor);
    });

    const totalRegional = [...regionTotals.values()].reduce((acc, current) => acc + current, 0);

    return [...regionTotals.entries()]
      .map(([regiao, valor]) => ({
        regiao,
        valor,
        percentual: totalRegional > 0 ? (valor / totalRegional) * 100 : 0,
      }))

      .sort((a, b) => b.percentual - a.percentual);
  }, [geoJsonPorEstado]);

  const maiorPercentualRegiao = useMemo(
    () => Math.max(...dadosRegiaoMapa.map((item) => item.percentual), 0),
    [dadosRegiaoMapa],
  );

  const getRegionHeat = (percentual: number) => {
    if (percentual <= 0) {
      return 'hsl(var(--muted) / 0.5)';
    }

    const intensidade = maiorPercentualRegiao > 0 ? percentual / maiorPercentualRegiao : 0;
    const alpha = 0.2 + intensidade * 0.7;
    return `hsl(var(--primary) / ${Math.min(alpha, 1).toFixed(2)})`;
  };

  const naoIdentificado = vendasPorRegiao.find((item) => item.regiao === 'Não identificado');
  const isMapLoading = brazilMapQuery.isLoading;

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
            Intensidade no GeoJSON geográfico real representa a participação de faturamento por estado e região.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <div className="relative h-[420px] overflow-hidden rounded-lg border bg-slate-100 dark:bg-slate-950">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(148,163,184,0.20)_1px,transparent_1px),linear-gradient(to_bottom,rgba(148,163,184,0.20)_1px,transparent_1px)] bg-[size:32px_32px]" />
            <div className="absolute left-4 top-4 z-20 rounded-md border bg-background/95 px-3 py-2 text-xs shadow-sm backdrop-blur">
              Brasil • Visão de vendas por região
            </div>

            {isMapLoading ? (
              <div className="absolute inset-0 z-10 flex items-center justify-center text-sm text-muted-foreground">
                Carregando mapa geográfico do Brasil...
              </div>
            ) : (
              <svg
                viewBox="0 0 100 100"
                className="absolute inset-0 z-10 h-full w-full"
                role="img"
                aria-label="Mapa GeoJSON dos estados brasileiros com participação de vendas"
              >
                {geoJsonPorEstado.map((estado) => (
                  <g key={estado.uf}>
                    {estado.projectedRings.map((ring, index) => (
                      <polygon
                        key={`${estado.uf}-${index}`}
                        points={ring.map(([x, y]) => `${x},${y}`).join(' ')}
                        fill={getRegionHeat(estado.percentual)}
                        stroke="hsl(var(--border))"
                        strokeWidth={0.25}
                      >
                        <title>
                          {`${estado.uf} (${estado.regiao}): ${formatCurrency(estado.valor)} (${estado.percentual.toFixed(1)}%)`}
                        </title>
                      </polygon>
                    ))}
                    <text
                      x={estado.centroidX}
                      y={estado.centroidY}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize="1.6"
                      className="fill-foreground"
                    >
                      {estado.uf}
                    </text>
                  </g>
                ))}
              </svg>
            )}

            <div className="absolute bottom-3 right-3 z-20 rounded-md border bg-background/95 px-3 py-2 text-xs text-muted-foreground shadow-sm backdrop-blur">
              Tons mais fortes = maior participação
            </div>
          </div>

          <div className="space-y-3">
            {dadosRegiaoMapa.map((item) => (
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
