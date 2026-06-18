import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, BarChart3, Files, Percent, Search, Wallet } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/contexts/AuthContext';
import { useFiscalYears } from '@/hooks/useFiscalYears';
import { Header } from '@/pages/components/Header';
import {
  DetalhamentoFiscalHierarquiaMode,
} from '@/pages/components/Detalhamento/DetalhamentoFiscalHierarquiaMode';
import { StatCard } from '@/pages/components/StatCard';
import type {
  AnaliseFiscalCfopResponse as AnaliseFiscalCfopNfeResponse,
  AnaliseFiscalHierarquicaResponse as AnaliseFiscalHierarquicaNfeResponse,
} from '@/services/nfe';
import type {
  AnaliseFiscalCfopResponse as AnaliseFiscalCfopSpedResponse,
  AnaliseFiscalHierarquicaResponse as AnaliseFiscalHierarquicaSpedResponse,
} from '@/services/sped';
import { createFiscalSourceApi } from '@/services/fiscalSource';
import { createFiscalPeriod, createFiscalQueryKey } from '@/utils/fiscalPeriod';
import { formatCurrency, hasValidEmitenteCnpj, monthLabels, parseDecimal } from '@/utils/formatters';

type HierarquiaResponse = AnaliseFiscalHierarquicaNfeResponse | AnaliseFiscalHierarquicaSpedResponse;
type CfopResponse = AnaliseFiscalCfopNfeResponse | AnaliseFiscalCfopSpedResponse;

export default function AnaliseFiscalCfop() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [searchTerm, setSearchTerm] = useState('');

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const fiscalApi = createFiscalSourceApi(user?.tem_sped);
  const fiscalPeriod = useMemo(
    () => createFiscalPeriod(selectedYear, selectedMonth),
    [selectedMonth, selectedYear],
  );

  const yearsQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'analise-fiscal-anos',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
    }),
    queryFn: () => fiscalApi.kpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const cfopQuery = useQuery<CfopResponse>({
    queryKey: createFiscalQueryKey({
      scope: 'analise-fiscal-cfop-cards',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
      period: fiscalPeriod,
    }),
    queryFn: () => fiscalApi.analiseFiscalCfop({
      emitente_cnpj: emitenteCnpj,
      email: fiscalApi.isSped ? undefined : user?.email,
      ...fiscalPeriod.params,
      limite: 1000,
    }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const hierarchyQuery = useQuery<HierarquiaResponse>({
    queryKey: createFiscalQueryKey({
      scope: 'analise-fiscal-drilldown',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
      period: fiscalPeriod,
    }),
    queryFn: () => fiscalApi.analiseFiscalHierarquica({
      emitente_cnpj: emitenteCnpj,
      email: fiscalApi.isSped ? undefined : user?.email,
      ...fiscalPeriod.params,
      nivel_atual: 'estado',
      limite: 50,
    }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const { availableYears } = useFiscalYears({
    entries: yearsQuery.data?.resultados ?? [],
    selectedYear,
    setSelectedYear,
  });

  useEffect(() => {
    setSearchTerm('');
  }, [selectedMonth, selectedYear, emitenteCnpj, fiscalApi.sourceKey]);

  const stats = [
    { title: 'Total movimentado', value: formatCurrency(parseDecimal(cfopQuery.data?.total_movimentado ?? 0)), description: 'Base total analisada por CFOP', icon: Wallet, trend: 'neutral', accentClass: 'border-l-sky-500', appendPreviousMonthLabel: false },
    { title: 'Documentos', value: String(cfopQuery.data?.quantidade_documentos ?? 0), description: 'Documentos considerados', icon: Files, trend: 'neutral', accentClass: 'border-l-emerald-500', appendPreviousMonthLabel: false },
    { title: 'CFOPs', value: String(cfopQuery.data?.quantidade_cfops ?? 0), description: 'CFOPs identificados no periodo', icon: Percent, trend: 'neutral', accentClass: 'border-l-amber-400', appendPreviousMonthLabel: false },
    { title: 'Impostos', value: formatCurrency(parseDecimal(cfopQuery.data?.total_impostos_complementares ?? 0)), description: 'Total na camada fiscal complementar', icon: BarChart3, trend: 'neutral', accentClass: 'border-l-violet-500', appendPreviousMonthLabel: false },
  ] as const;

  return (
    <div className="space-y-6 py-6">
      <Header title="Analise fiscal" subtitle="KPIs por CFOP com drill-down hierarquico no mesmo padrao visual do detalhamento de vendas." selectedMonth={selectedMonth} selectedYear={selectedYear} availableYears={availableYears} monthLabels={monthLabels} onMonthChange={setSelectedMonth} onYearChange={setSelectedYear} />

      <div className="stat-card-grid">{stats.map((stat) => <StatCard key={stat.title} {...stat} isLoading={cfopQuery.isLoading} />)}</div>

      <Card className="border border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]"><CardContent className="space-y-5 p-6"><div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div className="space-y-2"><Badge className="border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">Drill-down hierarquico</Badge><h2 className="text-2xl font-semibold tracking-tight">Estado {'>'} Cidade {'>'} NCM {'>'} Produto</h2><p className="max-w-3xl text-sm text-slate-300">Estrutura igual ao detalhamento de vendas, separando os KPIs de topo da navegacao hierarquica.</p></div><Button type="button" variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100" asChild><Link to="/detalhamento-vendas">Abrir detalhamento de vendas<ArrowRight className="h-4 w-4" /></Link></Button></div></CardContent></Card>

      {(cfopQuery.isError || hierarchyQuery.isError) && <Alert variant="destructive"><AlertTitle>Erro ao carregar analise fiscal</AlertTitle><AlertDescription>{(cfopQuery.error instanceof Error && cfopQuery.error.message) || (hierarchyQuery.error instanceof Error && hierarchyQuery.error.message) || 'Nao foi possivel consultar os dados fiscais.'}</AlertDescription></Alert>}

      <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]"><CardContent className="p-0"><div className="border-b border-slate-800/80 px-6 py-4"><div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"><div className="relative w-full max-w-xl"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><Input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Pesquisar nos blocos carregados do drill-down" className="border-slate-700 bg-slate-900/80 pl-10 text-slate-100 placeholder:text-slate-400 focus-visible:ring-sky-500" /></div><div className="text-xs text-slate-400">Carregamento inicial em blocos por estado. Cidades, NCMs e produtos sob demanda.</div></div><div className="text-xs text-slate-400">Exibindo {hierarchyQuery.data?.por_estado.length ?? 0} estados no primeiro nivel.</div></div>{(hierarchyQuery.data?.por_estado?.length ?? 0) > 0 ? <DetalhamentoFiscalHierarquiaMode fetchHierarchy={fiscalApi.analiseFiscalHierarquica} baseParams={{ emitente_cnpj: emitenteCnpj, email: fiscalApi.isSped ? undefined : user?.email, ...fiscalPeriod.params }} states={hierarchyQuery.data?.por_estado ?? []} searchTerm={searchTerm} /> : <div className="p-6 text-sm text-slate-300">{hierarchyQuery.isLoading ? 'Carregando drill-down fiscal por estado...' : searchTerm.trim() ? 'Nenhum resultado encontrado para a pesquisa informada.' : 'Nenhum dado fiscal encontrado para o periodo selecionado.'}</div>}</CardContent></Card>
    </div>
  );
}
