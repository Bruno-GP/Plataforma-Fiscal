import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Percent, Search, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/contexts/AuthContext';
import { Header } from '@/pages/components/Header';
import {
  DetalhamentoFiscalHierarquiaMode,
  type FiscalHierarchyState,
} from '@/pages/components/DetalhamentoFiscalHierarquiaMode';
import { StatCard } from '@/pages/components/StatCard';
import {
  fetchNfeAnaliseFiscalHierarquica,
  fetchNfeKpis,
  parseDecimal,
  type AnaliseFiscalHierarquicaResponse as AnaliseFiscalHierarquicaNfeResponse,
} from '@/services/nfe';
import {
  fetchSpedAnaliseFiscalHierarquica,
  fetchSpedKpis,
  type AnaliseFiscalHierarquicaResponse as AnaliseFiscalHierarquicaSpedResponse,
} from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

type HierarquiaResponse =
  | AnaliseFiscalHierarquicaNfeResponse
  | AnaliseFiscalHierarquicaSpedResponse;

type DrillState = {
  estado?: string;
  cidade?: string;
  ncm?: string;
};

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

export default function AnaliseFiscalCfop() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [searchTerm, setSearchTerm] = useState('');
  const [openStateValues, setOpenStateValues] = useState<string[]>([]);
  const [openCityValues, setOpenCityValues] = useState<string[]>([]);
  const [openNcmValues, setOpenNcmValues] = useState<string[]>([]);

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);
  const isSped = Boolean(user?.tem_sped);

  const yearsQuery = useQuery({
    queryKey: ['analise-fiscal-anos', emitenteCnpj, isSped],
    queryFn: () =>
      isSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const analiseQuery = useQuery<HierarquiaResponse>({
    queryKey: ['analise-fiscal-drilldown', emitenteCnpj, isSped, selectedYear, selectedMonth],
    queryFn: () =>
      isSped
        ? fetchSpedAnaliseFiscalHierarquica({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5000,
          })
        : fetchNfeAnaliseFiscalHierarquica({
            emitente_cnpj: emitenteCnpj,
            email: user?.email,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5000,
          }),
    enabled: hasEmitenteCnpj,
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
    if (!availableYears.includes(Number.parseInt(selectedYear, 10))) {
      setSelectedYear(String(availableYears[0]));
    }
  }, [availableYears, selectedYear]);

  useEffect(() => {
    setSearchTerm('');
    setOpenStateValues([]);
    setOpenCityValues([]);
    setOpenNcmValues([]);
  }, [selectedMonth, selectedYear, emitenteCnpj, isSped]);

  const totalFaturamento = parseDecimal(analiseQuery.data?.total_faturamento ?? 0);
  const totalImpostos = parseDecimal(analiseQuery.data?.total_impostos ?? 0);
  const percentualTotal = parseDecimal(analiseQuery.data?.percentual_impostos_sobre_faturamento ?? 0);

  const stats = [
    {
      title: 'Faturamento',
      value: formatCurrency(totalFaturamento),
      description: 'Base total do periodo filtrado',
      icon: TrendingUp,
      trend: 'up' as const,
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Impostos',
      value: formatCurrency(totalImpostos),
      description: 'Valor total sobre o faturamento',
      icon: Percent,
      trend: 'up' as const,
      accentClass: 'border-l-violet-500',
    },
    {
      title: 'Percentual',
      value: `${percentualTotal.toFixed(2)}%`,
      description: 'Impostos sobre faturamento',
      icon: Percent,
      trend: 'up' as const,
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Documentos',
      value: String(analiseQuery.data?.quantidade_documentos ?? 0),
      description: 'Documentos considerados',
      icon: TrendingUp,
      trend: 'up' as const,
      accentClass: 'border-l-emerald-500',
    },
  ] as const;

  const hierarchyRows = useMemo(() => {
    const baseItems = analiseQuery.data?.hierarquia ?? [];
    const query = searchTerm.trim().toLowerCase();
    if (!query) return baseItems;

    return baseItems.filter((item) =>
      Object.values(item).some((value) => String(value ?? '').toLowerCase().includes(query)),
    );
  }, [analiseQuery.data?.hierarquia, searchTerm]);

  const hierarchy = useMemo<FiscalHierarchyState[]>(() => {
    const states = new Map<string, FiscalHierarchyState>();

    for (const row of hierarchyRows) {
      const uf = String(row.estado ?? 'Sem UF');
      const city = String(row.cidade ?? 'Cidade nao identificada');
      const ncm = String(row.ncm ?? '00000000');
      const ncmDescription = String(row.descricao_ncm ?? 'NCM sem descricao');
      const productCode = String(row.produto_codigo ?? 'SEM-CODIGO');
      const productName = String(row.produto ?? 'Produto sem descricao');
      const faturamento = parseDecimal(row.faturamento ?? 0);
      const impostoValor = parseDecimal(row.imposto_valor ?? 0);
      const impostoPercentual = parseDecimal(row.imposto_percentual ?? 0);

      let stateEntry = states.get(uf);
      if (!stateEntry) {
        stateEntry = { key: `uf-${uf}`, uf, total: 0, taxValue: 0, taxPercent: 0, cities: [] };
        states.set(uf, stateEntry);
      }
      stateEntry.total += faturamento;
      stateEntry.taxValue += impostoValor;

      let cityEntry = stateEntry.cities.find((item) => item.city === city);
      if (!cityEntry) {
        cityEntry = { key: `city-${uf}-${city}`, city, uf, total: 0, taxValue: 0, taxPercent: 0, ncms: [] };
        stateEntry.cities.push(cityEntry);
      }
      cityEntry.total += faturamento;
      cityEntry.taxValue += impostoValor;

      let ncmEntry = cityEntry.ncms.find((item) => item.ncm === ncm);
      if (!ncmEntry) {
        ncmEntry = {
          key: `ncm-${uf}-${city}-${ncm}`,
          ncm,
          description: ncmDescription,
          total: 0,
          taxValue: 0,
          taxPercent: 0,
          products: [],
        };
        cityEntry.ncms.push(ncmEntry);
      }
      ncmEntry.total += faturamento;
      ncmEntry.taxValue += impostoValor;

      ncmEntry.products.push({
        key: `product-${uf}-${city}-${ncm}-${productCode}-${productName}`,
        code: productCode,
        description: productName,
        totalValue: faturamento,
        taxValue: impostoValor,
        taxPercent: impostoPercentual,
      });
    }

    const result = [...states.values()];
    for (const stateEntry of result) {
      stateEntry.taxPercent = stateEntry.total ? (stateEntry.taxValue / stateEntry.total) * 100 : 0;
      for (const cityEntry of stateEntry.cities) {
        cityEntry.taxPercent = cityEntry.total ? (cityEntry.taxValue / cityEntry.total) * 100 : 0;
        for (const ncmEntry of cityEntry.ncms) {
          ncmEntry.taxPercent = ncmEntry.total ? (ncmEntry.taxValue / ncmEntry.total) * 100 : 0;
          ncmEntry.products.sort((a, b) => b.totalValue - a.totalValue);
        }
        cityEntry.ncms.sort((a, b) => b.total - a.total);
      }
      stateEntry.cities.sort((a, b) => b.total - a.total);
    }
    return result.sort((a, b) => b.total - a.total);
  }, [hierarchyRows]);

  const stateAccordionValues = useMemo(() => hierarchy.map((item) => item.key), [hierarchy]);
  const cityAccordionValues = useMemo(
    () => hierarchy.flatMap((stateEntry) => stateEntry.cities.map((item) => item.key)),
    [hierarchy],
  );
  const ncmAccordionValues = useMemo(
    () => hierarchy.flatMap((stateEntry) => stateEntry.cities.flatMap((cityEntry) => cityEntry.ncms.map((item) => item.key))),
    [hierarchy],
  );

  useEffect(() => {
    setOpenStateValues((current) => current.filter((value) => stateAccordionValues.includes(value)));
  }, [stateAccordionValues]);

  useEffect(() => {
    setOpenCityValues((current) => current.filter((value) => cityAccordionValues.includes(value)));
  }, [cityAccordionValues]);

  useEffect(() => {
    setOpenNcmValues((current) => current.filter((value) => ncmAccordionValues.includes(value)));
  }, [ncmAccordionValues]);

  const allStatesOpen = stateAccordionValues.length > 0 && stateAccordionValues.every((value) => openStateValues.includes(value));
  const allCitiesOpen = cityAccordionValues.length > 0 && cityAccordionValues.every((value) => openCityValues.includes(value));
  const allNcmsOpen = ncmAccordionValues.length > 0 && ncmAccordionValues.every((value) => openNcmValues.includes(value));

  const toggleStates = () => setOpenStateValues(allStatesOpen ? [] : stateAccordionValues);
  const toggleCities = () => {
    if (allCitiesOpen) {
      setOpenCityValues([]);
      return;
    }
    setOpenStateValues(stateAccordionValues);
    setOpenCityValues(cityAccordionValues);
  };
  const toggleNcms = () => {
    if (allNcmsOpen) {
      setOpenNcmValues([]);
      return;
    }
    setOpenStateValues(stateAccordionValues);
    setOpenCityValues(cityAccordionValues);
    setOpenNcmValues(ncmAccordionValues);
  };

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Analise fiscal"
        subtitle="Drill-down hierarquico no mesmo padrao visual do detalhamento de vendas."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={analiseQuery.isLoading} />
        ))}
      </div>

      <Card className="border border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]">
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <Badge className="border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">
                Drill-down hierarquico
              </Badge>
              <h2 className="text-2xl font-semibold tracking-tight">Estado {'>'} Cidade {'>'} NCM {'>'} Produto</h2>
              <p className="max-w-3xl text-sm text-slate-300">
                Estrutura igual ao detalhamento de vendas, mas aplicada ao faturamento e imposto sobre faturamento.
              </p>
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100" asChild>
                <Link to="/detalhamento-vendas">
                  Abrir detalhamento de vendas
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {analiseQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar analise fiscal</AlertTitle>
          <AlertDescription>
            {analiseQuery.error instanceof Error
              ? analiseQuery.error.message
              : 'Nao foi possivel consultar o drill-down fiscal.'}
          </AlertDescription>
        </Alert>
      )}

      <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
        <CardContent className="p-0">
          <div className="border-b border-slate-800/80 px-6 py-4">
            <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="relative w-full max-w-xl">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Pesquisar no nivel atual"
                  className="border-slate-700 bg-slate-900/80 pl-10 text-slate-100 placeholder:text-slate-400 focus-visible:ring-sky-500"
                />
              </div>
              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={toggleStates}
                  className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800"
                >
                  Estado
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={toggleCities}
                  className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800"
                >
                  Cidade
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={toggleNcms}
                  className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800"
                >
                  NCM
                </Button>
              </div>
            </div>

            <div className="text-xs text-slate-400">
              Exibindo {hierarchyRows.length} produtos agregados na hierarquia.
            </div>
          </div>
          <DetalhamentoFiscalHierarquiaMode
            hierarchy={hierarchy}
            openStateValues={openStateValues}
            onOpenStateValuesChange={setOpenStateValues}
            openCityValues={openCityValues}
            onOpenCityValuesChange={setOpenCityValues}
            openNcmValues={openNcmValues}
            onOpenNcmValuesChange={setOpenNcmValues}
          />
        </CardContent>
      </Card>
    </div>
  );
}
