import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';

const BRAZIL_STATES_GEOJSON_URL =
  'https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson';

const IBGE_CITIES_GEOJSON_URL = (uf: string) =>
  `${import.meta.env.VITE_API_URL?.replace(/\/$/, '') ?? 'http://localhost:8000'}/api/geo/municipios/${uf}`;

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
  if (!cityLabel) return null;

  const normalized = cityLabel.toUpperCase().trim();
  if (/^[A-Z]{2}$/.test(normalized)) {
    return ufToRegion[normalized] ? normalized : null;
  }

  const match = normalized.match(/(?:-|\/|\(|\s)([A-Z]{2})(?:\)|$)/);
  if (!match) return null;

  const uf = match[1];
  return ufToRegion[uf] ? uf : null;
};

const extractCityName = (cityLabel?: string) => {
  if (!cityLabel) return 'Cidade não identificada';

  return cityLabel
    .replace(/\s*[-/()]\s*[A-Z]{2}\)?\s*$/u, '')
    .trim();
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

type CityGeoJsonFeature = {
  type: 'Feature';
  properties: {
    nome?: string;
    name?: string;
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

type CityGeoJsonFeatureCollection = {
  type: 'FeatureCollection';
  features: CityGeoJsonFeature[];
};

const getFeatureRings = (feature: GeoJsonFeature) => {
  if (feature.geometry.type === 'Polygon') {
    return [feature.geometry.coordinates[0]];
  }

  return feature.geometry.coordinates
    .map((polygon) => polygon[0])
    .filter((ring) => ring.length > 0);
};

interface TopCityItem {
  key: string;
  title: string;
  value: string;
  rawValue: number;
  percent: number | null;
}

interface SalesRegionCityMapProps {
  topCidadesItems: TopCityItem[];
  totalFaturamento: number;
  formatCurrency: (value: number) => string;
}

export function SalesRegionCityMap({
  topCidadesItems,
  totalFaturamento,
  formatCurrency,
}: SalesRegionCityMapProps) {
  const [mapViewMode, setMapViewMode] = useState<'regiao' | 'cidade'>('regiao');
  const [selectedCity, setSelectedCity] = useState<string | null>(null);

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

  const topCidades = useMemo(
    () => topCidadesItems.map((item) => ({ cidade: item.title, valor_total: item.rawValue })),
    [topCidadesItems],
  );

  const vendasPorRegiao = useMemo(() => {
    const regiaoMap = new Map<string, number>([
      ['Norte', 0],
      ['Nordeste', 0],
      ['Centro-Oeste', 0],
      ['Sudeste', 0],
      ['Sul', 0],
      ['Outras localidades', 0],
      ['Não identificado', 0],
    ]);

    topCidades.forEach((cidade) => {
      const uf = extractUfFromCity(cidade.cidade);
      const regiao = uf ? ufToRegion[uf] : 'Não identificado';
      regiaoMap.set(regiao, (regiaoMap.get(regiao) ?? 0) + cidade.valor_total);
    });

    const totalRegional = Math.max(totalFaturamento, 0);

    const totalMapeado = [...regiaoMap.values()].reduce((acc, valor) => acc + valor, 0);
    const complementoOutrasLocalidades = Math.max(totalRegional - totalMapeado, 0);

    if (complementoOutrasLocalidades > 0) {
      regiaoMap.set(
        'Outras localidades',
        (regiaoMap.get('Outras localidades') ?? 0) + complementoOutrasLocalidades,
      );
    }

    return [...regiaoMap.entries()]
      .map(([regiao, valor]) => ({
        regiao,
        valor,
        percentual: totalRegional > 0 ? (valor / totalRegional) * 100 : 0,
      }))
      .sort((a, b) => b.valor - a.valor);
  }, [topCidades, totalFaturamento]);

  const geoJsonPorEstado = useMemo(() => {
    const data = brazilMapQuery.data;
    if (!data?.features?.length) {
      return [];
    }

    const salesByState = new Map<string, number>();

    topCidades.forEach((cidade) => {
      const uf = extractUfFromCity(cidade.cidade);
      if (!uf) return;
      salesByState.set(uf, (salesByState.get(uf) ?? 0) + cidade.valor_total);
    });

    return data.features
      .map((feature) => {
        const stateName = normalizeLabel(feature.properties.name ?? '');
        const uf = feature.properties.sigla ?? stateNameToUf[stateName];

        if (!uf || !ufToRegion[uf]) return null;

        const rings = getFeatureRings(feature);
        if (!rings.length) return null;

        return { uf, regiao: ufToRegion[uf], rings, valor: salesByState.get(uf) ?? 0 };
      })
      .filter((item): item is { uf: string; regiao: string; rings: number[][][]; valor: number } => Boolean(item));
  }, [brazilMapQuery.data, topCidades]);

  const estadoFocoCidade = useMemo(() => {
    if (mapViewMode !== 'cidade' || !geoJsonPorEstado.length) return null;
    return [...geoJsonPorEstado].sort((a, b) => b.valor - a.valor)[0]?.uf ?? null;
  }, [geoJsonPorEstado, mapViewMode]);

  const cidadesGeoJsonQuery = useQuery<CityGeoJsonFeatureCollection>({
    queryKey: ['ibge-cities-geojson', estadoFocoCidade],
    queryFn: async () => {
      if (!estadoFocoCidade) {
        throw new Error('UF foco não disponível para carregar cidades.');
      }

      const response = await fetch(IBGE_CITIES_GEOJSON_URL(estadoFocoCidade));
      if (!response.ok) {
        return { type: 'FeatureCollection', features: [] };
      }
      return response.json();
    },
    enabled: mapViewMode === 'cidade' && Boolean(estadoFocoCidade),
    staleTime: 24 * 60 * 60 * 1000,
  });

  const projectionConfig = useMemo(() => {
    if (!geoJsonPorEstado.length) return null;

    const boundsTotal = geoJsonPorEstado.reduce(
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

    let bounds = boundsTotal;

    if (mapViewMode === 'cidade' && estadoFocoCidade) {
      const estadoFoco = geoJsonPorEstado.find((item) => item.uf === estadoFocoCidade);
      if (estadoFoco) {
        const focusBounds = estadoFoco.rings.reduce(
          (acc, ring) => {
            ring.forEach(([lon, lat]) => {
              acc.minLon = Math.min(acc.minLon, lon);
              acc.maxLon = Math.max(acc.maxLon, lon);
              acc.minLat = Math.min(acc.minLat, lat);
              acc.maxLat = Math.max(acc.maxLat, lat);
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

        const lonPadding = Math.max((focusBounds.maxLon - focusBounds.minLon) * 0.2, 0.8);
        const latPadding = Math.max((focusBounds.maxLat - focusBounds.minLat) * 0.2, 0.8);

        bounds = {
          minLon: focusBounds.minLon - lonPadding,
          maxLon: focusBounds.maxLon + lonPadding,
          minLat: focusBounds.minLat - latPadding,
          maxLat: focusBounds.maxLat + latPadding,
        };
      }
    }

    if (!Number.isFinite(bounds.minLon) || !Number.isFinite(bounds.minLat)) return null;

    const padding = 3;
    const width = 100;
    const height = 100;
    const lonSpan = Math.max(bounds.maxLon - bounds.minLon, 1);
    const latSpan = Math.max(bounds.maxLat - bounds.minLat, 1);
    const scale = Math.min((width - padding * 2) / lonSpan, (height - padding * 2) / latSpan);
    const projectedWidth = lonSpan * scale;
    const projectedHeight = latSpan * scale;

    return {
      bounds,
      scale,
      offsetX: (width - projectedWidth) / 2,
      offsetY: (height - projectedHeight) / 2,
    };
  }, [estadoFocoCidade, geoJsonPorEstado, mapViewMode]);

  const geoJsonProjetado = useMemo(() => {
    if (!projectionConfig) return [];

    const totalMapSales = Math.max(totalFaturamento, 0);

    return geoJsonPorEstado.map((item) => {
      const projectedRings = item.rings.map((ring) =>
        ring.map(([lon, lat]) => [
          projectionConfig.offsetX + (lon - projectionConfig.bounds.minLon) * projectionConfig.scale,
          projectionConfig.offsetY + (projectionConfig.bounds.maxLat - lat) * projectionConfig.scale,
        ]),
      );

      const centroid = projectedRings.flat().reduce(
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
  }, [geoJsonPorEstado, projectionConfig, totalFaturamento]);

  const focoProjetado = useMemo(() => {
    if (mapViewMode !== 'cidade' || !estadoFocoCidade || !geoJsonProjetado.length) return null;

    const estado = geoJsonProjetado.find((item) => item.uf === estadoFocoCidade);
    if (!estado) return null;

    return { x: estado.centroidX, y: estado.centroidY, uf: estado.uf };
  }, [estadoFocoCidade, geoJsonProjetado, mapViewMode]);

  const cidadesPorEstado = useMemo(() => {
    const agrupado = new Map<string, { key: string; nome: string; valor: number; percentual: number }[]>();

    topCidadesItems.forEach((cidade) => {
      const uf = extractUfFromCity(cidade.title);
      if (!uf) return;

      const cidades = agrupado.get(uf) ?? [];
      cidades.push({
        key: cidade.key,
        nome: extractCityName(cidade.title),
        valor: cidade.rawValue,
        percentual: cidade.percent ?? 0,
      });
      agrupado.set(uf, cidades);
    });

    return agrupado;
  }, [topCidadesItems]);

  const mapTransitionStyle = useMemo(() => {
    if (mapViewMode !== 'cidade' || !focoProjetado) {
      return { transform: 'translate(0px, 0px) scale(1)' };
    }

    const scale = 1.65;
    const translateX = 50 - focoProjetado.x;
    const translateY = 50 - focoProjetado.y;

    return { transform: `translate(${translateX}px, ${translateY}px) scale(${scale})` };
  }, [focoProjetado, mapViewMode]);

  const cidadeMarkerData = useMemo(() => {
    const maxPercentualCidade = Math.max(...topCidadesItems.map((item) => item.percent ?? 0), 0);

    return geoJsonProjetado.flatMap((estado) => {
      const cidadesEstado = cidadesPorEstado.get(estado.uf) ?? [];

      return cidadesEstado.map((cidade, index) => {
        const angle = (index / Math.max(cidadesEstado.length, 1)) * Math.PI * 2;
        const distance = 0.9 + index * 0.35;
        const x = estado.centroidX + Math.cos(angle) * distance;
        const y = estado.centroidY + Math.sin(angle) * distance;
        const intensidade = maxPercentualCidade > 0 ? cidade.percentual / maxPercentualCidade : 0;
        const alpha = 0.25 + intensidade * 0.75;
        const radius = 0.25 + intensidade * 0.55;

        return {
          ...cidade,
          uf: estado.uf,
          x,
          y,
          radius,
          color: `hsl(var(--primary) / ${Math.min(alpha, 1).toFixed(2)})`,
        };
      });
    });
  }, [cidadesPorEstado, geoJsonProjetado, topCidadesItems]);

  const cityGeoJsonProjetado = useMemo(() => {
    if (mapViewMode !== 'cidade' || !projectionConfig || !cidadesGeoJsonQuery.data?.features?.length) {
      return [];
    }

    const topCitySalesByName = new Map<string, number>();
    topCidadesItems.forEach((cidade) => {
      topCitySalesByName.set(normalizeLabel(extractCityName(cidade.title)), cidade.rawValue);
    });

    return cidadesGeoJsonQuery.data.features
      .map((feature) => {
        const rings = getFeatureRings(feature as GeoJsonFeature);
        if (!rings.length) return null;

        const cityName = feature.properties.nome ?? feature.properties.name ?? 'Cidade não identificada';

        const projectedRings = rings.map((ring) =>
          ring.map(([lon, lat]) => [
            projectionConfig.offsetX + (lon - projectionConfig.bounds.minLon) * projectionConfig.scale,
            projectionConfig.offsetY + (projectionConfig.bounds.maxLat - lat) * projectionConfig.scale,
          ]),
        );

        const centroid = projectedRings.flat().reduce(
          (acc, [x, y], _, arr) => {
            acc[0] += x / arr.length;
            acc[1] += y / arr.length;
            return acc;
          },
          [0, 0],
        );

        return {
          name: cityName,
          value: topCitySalesByName.get(normalizeLabel(cityName)) ?? 0,
          percentual: totalFaturamento > 0
            ? ((topCitySalesByName.get(normalizeLabel(cityName)) ?? 0) / totalFaturamento) * 100
            : 0,
          centroidX: centroid[0],
          centroidY: centroid[1],
          projectedRings,
        };
      })
      .filter((item): item is {
        name: string;
        value: number;
        percentual: number;
        centroidX: number;
        centroidY: number;
        projectedRings: number[][][];
      } => Boolean(item));
  }, [cidadesGeoJsonQuery.data, mapViewMode, projectionConfig, topCidadesItems, totalFaturamento]);

  const cidadesComVendasOrdenadas = useMemo(
    () => [...cityGeoJsonProjetado].filter((city) => city.value > 0).sort((a, b) => b.value - a.value),
    [cityGeoJsonProjetado],
  );

  const cityLabelData = useMemo(
    () => cidadesComVendasOrdenadas.slice(0, 12),
    [cidadesComVendasOrdenadas],
  );

  useEffect(() => {
    if (mapViewMode !== 'cidade') {
      setSelectedCity(null);
      return;
    }

    if (!cidadesComVendasOrdenadas.length) {
      setSelectedCity(null);
      return;
    }

    if (!selectedCity || !cidadesComVendasOrdenadas.some((city) => city.name === selectedCity)) {
      setSelectedCity(cidadesComVendasOrdenadas[0].name);
    }
  }, [cidadesComVendasOrdenadas, mapViewMode, selectedCity]);

  const selectedCityData = useMemo(
    () => cityGeoJsonProjetado.find((cidade) => cidade.name === selectedCity) ?? null,
    [cityGeoJsonProjetado, selectedCity],
  );

  const dadosRegiaoMapa = useMemo(() => {
    const ordemRegioes = [
      'Norte',
      'Nordeste',
      'Centro-Oeste',
      'Sudeste',
      'Sul',
      'Outras localidades',
      'Não identificado',
    ];

    const dadosOrdenados = ordemRegioes
      .map((regiao) => vendasPorRegiao.find((item) => item.regiao === regiao) ?? {
        regiao,
        valor: 0,
        percentual: 0,
      })
      .filter((item) => item.valor > 0 || item.regiao !== 'Não identificado');

    return dadosOrdenados.sort((a, b) => b.percentual - a.percentual);
  }, [vendasPorRegiao]);

  const diagnosticoRegioes = useMemo(() => {
    const totalTopCidades = topCidadesItems.reduce((acc, item) => acc + item.rawValue, 0);

    const cidadesSemUf = topCidadesItems
      .filter((item) => !extractUfFromCity(item.title))
      .map((item) => ({
        key: item.key,
        title: item.title,
        rawValue: item.rawValue,
      }))
      .sort((a, b) => b.rawValue - a.rawValue);

    const totalSemUf = cidadesSemUf.reduce((acc, item) => acc + item.rawValue, 0);
    const totalOutrasLocalidades = Math.max(totalFaturamento - totalTopCidades, 0);

    return {
      totalTopCidades,
      totalOutrasLocalidades,
      totalSemUf,
      cidadesSemUf,
    };
  }, [topCidadesItems, totalFaturamento]);

  const maiorPercentualRegiao = useMemo(
    () => Math.max(...dadosRegiaoMapa.map((item) => item.percentual), 0),
    [dadosRegiaoMapa],
  );

  const getRegionHeat = (percentual: number) => {
    if (percentual <= 0) return 'hsl(var(--muted) / 0.5)';
    const intensidade = maiorPercentualRegiao > 0 ? percentual / maiorPercentualRegiao : 0;
    const alpha = 0.2 + intensidade * 0.7;
    return `hsl(var(--primary) / ${Math.min(alpha, 1).toFixed(2)})`;
  };

  const getCityHeat = (percentual: number) => {
    if (percentual <= 0) return 'hsl(var(--muted) / 0.35)';

    const maxPercentualCidade = Math.max(...topCidadesItems.map((item) => item.percent ?? 0), 0);
    const intensidade = maxPercentualCidade > 0 ? percentual / maxPercentualCidade : 0;
    const alpha = 0.2 + intensidade * 0.75;

    return `hsl(var(--primary) / ${Math.min(alpha, 1).toFixed(2)})`;
  };

  const isCityView = mapViewMode === 'cidade';
  const isMapLoading = brazilMapQuery.isLoading || (isCityView && cidadesGeoJsonQuery.isLoading);

  return (
    <section className="rounded-xl border bg-background p-4 md:p-6">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            {isCityView ? 'Mapa de vendas por cidade' : 'Mapa de vendas por região'}
          </h2>
          <p className="text-sm text-muted-foreground">
            {isCityView
              ? 'Visualização focada no estado com maior faturamento, exibindo as cidades com seus respectivos valores.'
              : 'Intensidade no GeoJSON geográfico real representa a participação de faturamento por estado e região.'}
          </p>
        </div>
        <div className="inline-flex rounded-lg border bg-muted/40 p-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setMapViewMode('regiao')}
            className={`rounded-md px-3 transition-all duration-200 ${!isCityView ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 hover:text-primary-foreground' : 'text-muted-foreground hover:bg-background/70 hover:text-foreground'}`}
          >
            Por Região
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setMapViewMode('cidade')}
            className={`rounded-md px-3 transition-all duration-200 ${isCityView ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 hover:text-primary-foreground' : 'text-muted-foreground hover:bg-background/70 hover:text-foreground'}`}
          >
            Por Cidade
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
        <div className="relative h-[420px] overflow-hidden rounded-lg border bg-slate-100 dark:bg-slate-950">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(148,163,184,0.20)_1px,transparent_1px),linear-gradient(to_bottom,rgba(148,163,184,0.20)_1px,transparent_1px)] bg-[size:32px_32px]" />
          <div className="absolute left-4 top-4 z-20 rounded-md border bg-background/95 px-3 py-2 text-xs shadow-sm backdrop-blur">
            {isCityView ? 'Brasil • Visão de vendas por cidade' : 'Brasil • Visão de vendas por região'}
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
              aria-label={isCityView
                ? 'Mapa GeoJSON dos estados brasileiros com foco em vendas por cidade'
                : 'Mapa GeoJSON dos estados brasileiros com participação de vendas'}
            >
              <g
                style={{
                  ...mapTransitionStyle,
                  transformOrigin: '50px 50px',
                  transition: 'transform 550ms cubic-bezier(0.22, 1, 0.36, 1)',
                }}
              >

                {geoJsonProjetado.map((estado) => {
                  const isFocusedState = estado.uf === estadoFocoCidade;
                  const cidadesEstado = cidadesPorEstado.get(estado.uf) ?? [];

                  return (
                    <g key={estado.uf}>
                      {estado.projectedRings.map((ring, index) => (
                        <polygon
                          key={`${estado.uf}-${index}`}
                          points={ring.map(([x, y]) => `${x},${y}`).join(' ')}
                          fill={isCityView
                            ? isFocusedState
                              ? 'hsl(var(--muted) / 0.1)'
                              : 'transparent'
                            : getRegionHeat(estado.percentual)}
                          stroke={isCityView && !isFocusedState ? 'hsl(var(--border) / 0.45)' : 'hsl(var(--border))'}
                          strokeWidth={isCityView && !isFocusedState ? 0.14 : 0.25}
                        >
                          <title>
                            {`${estado.uf} (${estado.regiao}): ${formatCurrency(estado.valor)} (${estado.percentual.toFixed(1)}%)`}
                          </title>
                        </polygon>
                      ))}
                      {!isCityView && (
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
                      )}

                      {isCityView && cidadesEstado.length > 0 && (
                        <text
                          x={estado.centroidX}
                          y={estado.centroidY - 1.6}
                          textAnchor="middle"
                          className="fill-foreground"
                          fontSize="1.25"
                          fontWeight="600"
                        >
                          {cidadesEstado.slice(0, 2).map((cidade, index) => (
                            <tspan
                              key={`${estado.uf}-${cidade.nome}`}
                              x={estado.centroidX}
                              dy={index === 0 ? 0 : 1.6}
                            >
                              {cidade.nome}
                            </tspan>
                          ))}
                        </text>
                      )}
                    </g>
                  );
                })}

                {isCityView && cityGeoJsonProjetado.map((cidade) => (
                  <g key={`cidade-shape-${cidade.name}`}>
                    {cidade.projectedRings.map((ring, index) => (
                      <polygon
                        key={`cidade-${cidade.name}-${index}`}
                        points={ring.map(([x, y]) => `${x},${y}`).join(' ')}
                        fill={cidade.value > 0 ? getCityHeat((cidade.value / Math.max(totalFaturamento, 1)) * 100) : 'hsl(var(--muted) / 0.08)'}
                        stroke={selectedCity === cidade.name ? 'hsl(var(--primary))' : 'hsl(var(--border) / 0.65)'}
                        strokeWidth={selectedCity === cidade.name ? 0.3 : 0.12}
                        className="cursor-pointer transition-all duration-200"
                        onClick={() => setSelectedCity(cidade.name)}
                      >
                        <title>{`${cidade.name}: ${formatCurrency(cidade.value)}`}</title>
                      </polygon>
                    ))}
                  </g>
                ))}

                {isCityView && cityLabelData.map((cidade) => (
                  <text
                    key={`cidade-label-${cidade.name}`}
                    x={cidade.centroidX}
                    y={cidade.centroidY}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="white"
                    stroke="hsl(var(--foreground) / 0.55)"
                    strokeWidth={0.08}
                    paintOrder="stroke"
                    fontSize="1.05"
                    fontWeight="600"
                    className="pointer-events-none"
                  >
                    {cidade.name}
                  </text>
                ))}

                {isCityView && cidadeMarkerData.map((cidade) => (
                  <g key={`marker-${cidade.key}`}>
                    <circle
                      cx={cidade.x}
                      cy={cidade.y}
                      r={cidade.radius}
                      fill={getCityHeat(cidade.percentual)}
                      stroke="hsl(var(--background))"
                      strokeWidth={0.12}
                    >
                      <title>
                        {`${cidade.nome} - ${cidade.uf}: ${cidade.percentual.toFixed(1)}% (${formatCurrency(cidade.valor)})`}
                      </title>
                    </circle>
                  </g>
                ))}
              </g>
            </svg>
          )}

          <div className="absolute bottom-3 right-3 z-20 rounded-md border bg-background/95 px-3 py-2 text-xs text-muted-foreground shadow-sm backdrop-blur">
            Tons mais fortes = maior participação
          </div>
        </div>

        <div className="space-y-3">
          {isCityView
            ? topCidadesItems.map((item) => (
              <div key={item.key} className="rounded-md border bg-background p-3">
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium">{item.title}</span>
                  <span className="text-muted-foreground">{item.percent?.toFixed(1) ?? '0.0'}%</span>
                </div>

                <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(item.percent ?? 0, 100)}%`,
                      backgroundColor: getCityHeat(item.percent ?? 0),
                    }}
                  />
                </div>
                <p className="text-sm text-muted-foreground">{item.value}</p>
              </div>
            ))
            : dadosRegiaoMapa.map((item) => (
              <div key={item.regiao} className="rounded-md border bg-background p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{item.regiao}</span>
                  <span className="text-muted-foreground">{item.percentual.toFixed(1)}%</span>
                </div>
                <p className="text-sm text-muted-foreground">{formatCurrency(item.valor)}</p>
              </div>
            ))}

          {isCityView && selectedCityData && (
            <div className="rounded-md border border-primary/40 bg-primary/5 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Cidade selecionada no mapa</p>
              <p className="text-sm font-semibold text-foreground">{selectedCityData.name}</p>
              <p className="text-sm text-muted-foreground">
                {formatCurrency(selectedCityData.value)} • {selectedCityData.percentual.toFixed(1)}% do total
              </p>
            </div>
          )}

          {!isCityView && (diagnosticoRegioes.totalOutrasLocalidades > 0 || diagnosticoRegioes.totalSemUf > 0) && (
            <div className="rounded-md border border-amber-300/40 bg-amber-500/5 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Como identificar os valores fora do mapa por UF</p>

              {diagnosticoRegioes.totalOutrasLocalidades > 0 && (
                <p className="mt-1 text-sm text-foreground">
                  <span className="font-semibold">Outras localidades:</span> {formatCurrency(diagnosticoRegioes.totalOutrasLocalidades)}
                  {' '}não está detalhado por cidade/UF no payload de top cidades.
                </p>
              )}

              {diagnosticoRegioes.totalSemUf > 0 && (
                <div className="mt-2">
                  <p className="text-sm text-foreground">
                    <span className="font-semibold">Não identificado:</span> {formatCurrency(diagnosticoRegioes.totalSemUf)}
                    {' '}vem de cidades sem UF reconhecível no nome.
                  </p>

                  <div className="mt-2 space-y-1">
                    {diagnosticoRegioes.cidadesSemUf.slice(0, 5).map((cidade) => (
                      <div key={cidade.key} className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                        <span className="truncate">{cidade.title}</span>
                        <span className="whitespace-nowrap">{formatCurrency(cidade.rawValue)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
        </div>
      </div>
    </section>
  );
}