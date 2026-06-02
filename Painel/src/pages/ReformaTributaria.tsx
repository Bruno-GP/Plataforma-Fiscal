import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Calculator, FileText, Landmark, ListFilter, ReceiptText, RefreshCw, Search } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAuth } from '@/contexts/AuthContext';
import { useFiscalYears } from '@/hooks/useFiscalYears';
import { Header } from '@/pages/components/Header';
import { StatCard } from '@/pages/components/StatCard';
import { parseDecimal } from '@/services/fiscal';
import {
  backfillReformaTributaria,
  fetchReformaApuracao,
  fetchReformaMemoriaCalculo,
  fetchReformaTributos,
  totalizarApuracao,
  type ApuracaoTributariaItem,
  type MemoriaCalculoTributariaItem,
} from '@/services/reformaTributaria';
import { invalidateFiscalDashboardCache, invalidateReformaTributariaCache } from '@/utils/fiscalCache';
import { createFiscalPeriod, createFiscalQueryKey } from '@/utils/fiscalPeriod';
import { formatCurrency, hasValidEmitenteCnpj, monthLabels } from '@/utils/formatters';

const formatPercent = (value: number | string | null | undefined) => {
  const parsed = parseDecimal(value);
  return `${parsed.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}%`;
};

const statusVariant = (status: string) => {
  const normalized = status.toLowerCase();
  if (['fechada', 'ativo', 'apurado'].includes(normalized)) return 'default';
  if (['retificada', 'parcial'].includes(normalized)) return 'secondary';
  return 'outline';
};

export default function ReformaTributaria() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedTributo, setSelectedTributo] = useState('todos');
  const [searchTerm, setSearchTerm] = useState('');

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const fiscalPeriod = useMemo(
    () => createFiscalPeriod(selectedYear, selectedMonth),
    [selectedMonth, selectedYear],
  );
  const tributoCodigo = selectedTributo === 'todos' ? undefined : selectedTributo;
  const origemBackfill = user?.tem_sped ? 'sped' : 'nfe';

  const tributosQuery = useQuery({
    queryKey: ['reforma-tributaria-tributos'],
    queryFn: ({ signal }) => fetchReformaTributos({}, { signal }),
    staleTime: 10 * 60 * 1000,
  });

  const apuracaoQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'reforma-tributaria-apuracao',
      emitenteCnpj,
      sourceKey: origemBackfill,
      period: fiscalPeriod,
      extra: [tributoCodigo],
    }),
    queryFn: ({ signal }) => fetchReformaApuracao({
      emitente_cnpj: emitenteCnpj,
      ...fiscalPeriod.params,
      tributo_codigo: tributoCodigo,
    }, { signal }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const memoriaQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'reforma-tributaria-memoria',
      emitenteCnpj,
      sourceKey: origemBackfill,
      period: fiscalPeriod,
      extra: [tributoCodigo],
    }),
    queryFn: ({ signal }) => fetchReformaMemoriaCalculo({
      emitente_cnpj: emitenteCnpj,
      ...fiscalPeriod.params,
      tributo_codigo: tributoCodigo,
      limite: 80,
    }, { signal }),
    enabled: hasEmitenteCnpj,
    staleTime: 2 * 60 * 1000,
  });

  const backfillMutation = useMutation({
    mutationFn: () =>
      backfillReformaTributaria({
        emitente_cnpj: emitenteCnpj ?? '',
        origem: origemBackfill,
      }),
    onSuccess: async () => {
      await Promise.all([
        invalidateReformaTributariaCache(queryClient),
        invalidateFiscalDashboardCache(queryClient),
      ]);
    },
  });

  const { availableYears } = useFiscalYears({
    entries: apuracaoQuery.data?.resultados ?? [],
    selectedYear,
    setSelectedYear,
    includeCurrentYear: true,
  });

  useEffect(() => {
    setSearchTerm('');
  }, [selectedMonth, selectedYear, selectedTributo, emitenteCnpj]);

  const apuracoes = apuracaoQuery.data?.resultados ?? [];
  const memoria = memoriaQuery.data?.resultados ?? [];
  const totais = totalizarApuracao(apuracoes);
  const tributosDisponiveis = tributosQuery.data?.resultados ?? [];

  const memoriaFiltrada = memoria.filter((item) => {
    const termo = searchTerm.trim().toLowerCase();
    if (!termo) return true;
    return [
      item.tributo_codigo,
      item.tributo_nome,
      item.etapa_calculo,
      item.fonte_dados,
      item.formula_calculo ?? '',
      item.hash_calculo ?? '',
    ].some((value) => value.toLowerCase().includes(termo));
  });

  const stats = [
    {
      title: 'Debitos',
      value: formatCurrency(totais.debitos),
      description: 'Total apurado no periodo',
      icon: ReceiptText,
      trend: 'neutral',
      accentClass: 'border-l-sky-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Creditos',
      value: formatCurrency(totais.creditos),
      description: 'Creditos vinculados a apuracao',
      icon: Landmark,
      trend: 'neutral',
      accentClass: 'border-l-emerald-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Saldo',
      value: formatCurrency(totais.saldo),
      description: 'Saldo apurado por tributo',
      icon: Calculator,
      trend: 'neutral',
      accentClass: 'border-l-amber-400',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Memorias',
      value: String(memoriaQuery.data?.total ?? 0),
      description: 'Registros de rastreabilidade',
      icon: FileText,
      trend: 'neutral',
      accentClass: 'border-l-violet-500',
      appendPreviousMonthLabel: false,
    },
  ] as const;

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Reforma Tributaria"
        subtitle="Acompanhamento de CBS, IBS, Imposto Seletivo, apuracao e memoria de calculo."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <Card className="border border-slate-800/80 bg-slate-950/70 text-white shadow-[0_18px_55px_-38px_rgba(15,23,42,1)]">
        <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
              <ListFilter className="h-4 w-4 text-sky-300" />
              <span>Filtro de tributo</span>
            </div>
            <p className="text-xs text-slate-400">Apure tributos atuais, de transicao e da Reforma por periodo.</p>
          </div>
          <Select value={selectedTributo} onValueChange={setSelectedTributo}>
            <SelectTrigger className="w-full border-slate-700 bg-slate-900/80 text-slate-100 md:w-80">
              <SelectValue placeholder="Todos os tributos" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todos">Todos os tributos</SelectItem>
              {tributosDisponiveis.map((tributo) => (
                <SelectItem key={tributo.codigo} value={tributo.codigo}>
                  {tributo.codigo} - {tributo.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            type="button"
            variant="secondary"
            className="w-full gap-2 md:w-auto"
            disabled={!hasEmitenteCnpj || backfillMutation.isPending}
            onClick={() => backfillMutation.mutate()}
          >
            <RefreshCw className={`h-4 w-4 ${backfillMutation.isPending ? 'animate-spin' : ''}`} />
            {backfillMutation.isPending ? 'Sincronizando...' : 'Sincronizar dados'}
          </Button>
        </CardContent>
      </Card>

      {backfillMutation.isSuccess && (
        <Alert>
          <AlertTitle>Dados sincronizados</AlertTitle>
          <AlertDescription>
            {backfillMutation.data.periodos_processados} periodo(s) recalculado(s) para {origemBackfill.toUpperCase()}.
          </AlertDescription>
        </Alert>
      )}

      {(apuracaoQuery.isError || memoriaQuery.isError || tributosQuery.isError || backfillMutation.isError) && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar dados da Reforma</AlertTitle>
          <AlertDescription>
            {(apuracaoQuery.error instanceof Error && apuracaoQuery.error.message)
              || (memoriaQuery.error instanceof Error && memoriaQuery.error.message)
              || (tributosQuery.error instanceof Error && tributosQuery.error.message)
              || (backfillMutation.error instanceof Error && backfillMutation.error.message)
              || 'Nao foi possivel consultar a base tributaria.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="stat-card-grid">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={apuracaoQuery.isLoading || memoriaQuery.isLoading} />
        ))}
      </div>

      <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
        <CardContent className="p-0">
          <div className="flex flex-col gap-3 border-b border-slate-800/80 px-6 py-5 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-white">Apuracao por tributo</h2>
              <p className="text-sm text-slate-400">Debitos, creditos, ajustes e saldo por periodo.</p>
            </div>
            <Badge variant="outline" className="w-fit border-slate-600 text-slate-300">
              {apuracoes.length} registros
            </Badge>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-slate-400">Tributo</TableHead>
                  <TableHead className="text-slate-400">Periodo</TableHead>
                  <TableHead className="text-right text-slate-400">Debitos</TableHead>
                  <TableHead className="text-right text-slate-400">Creditos</TableHead>
                  <TableHead className="text-right text-slate-400">Ajustes</TableHead>
                  <TableHead className="text-right text-slate-400">Saldo</TableHead>
                  <TableHead className="text-slate-400">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apuracoes.map((item: ApuracaoTributariaItem) => (
                  <TableRow key={item.id} className="border-slate-800/80 hover:bg-slate-900/70">
                    <TableCell>
                      <div className="font-medium text-white">{item.tributo_codigo}</div>
                      <div className="text-xs text-slate-400">{item.tributo_nome}</div>
                    </TableCell>
                    <TableCell className="text-slate-300">{String(item.periodo_mes).padStart(2, '0')}/{item.periodo_ano}</TableCell>
                    <TableCell className="text-right text-slate-200">{formatCurrency(parseDecimal(item.total_debitos))}</TableCell>
                    <TableCell className="text-right text-slate-200">{formatCurrency(parseDecimal(item.total_creditos))}</TableCell>
                    <TableCell className="text-right text-slate-200">{formatCurrency(parseDecimal(item.ajustes_debito) - parseDecimal(item.ajustes_credito))}</TableCell>
                    <TableCell className="text-right font-medium text-white">{formatCurrency(parseDecimal(item.saldo_apurado))}</TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
                {!apuracoes.length && (
                  <TableRow className="border-slate-800/80 hover:bg-transparent">
                    <TableCell colSpan={7} className="h-28 text-center text-sm text-slate-400">
                      {apuracaoQuery.isLoading ? 'Carregando apuracao...' : 'Nenhuma apuracao encontrada para os filtros selecionados.'}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
        <CardContent className="p-0">
          <div className="flex flex-col gap-4 border-b border-slate-800/80 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-white">Memoria de calculo</h2>
              <p className="text-sm text-slate-400">Rastreabilidade de regra, base, aliquota e resultado calculado.</p>
            </div>
            <div className="relative w-full max-w-md">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Pesquisar tributo, etapa, fonte ou hash"
                className="border-slate-700 bg-slate-900/80 pl-10 text-slate-100 placeholder:text-slate-500 focus-visible:ring-sky-500"
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-slate-400">Tributo</TableHead>
                  <TableHead className="text-slate-400">Etapa</TableHead>
                  <TableHead className="text-right text-slate-400">Base</TableHead>
                  <TableHead className="text-right text-slate-400">Aliquota</TableHead>
                  <TableHead className="text-right text-slate-400">Valor</TableHead>
                  <TableHead className="text-slate-400">Fonte</TableHead>
                  <TableHead className="text-slate-400">Hash</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {memoriaFiltrada.map((item: MemoriaCalculoTributariaItem) => (
                  <TableRow key={item.id} className="border-slate-800/80 hover:bg-slate-900/70">
                    <TableCell>
                      <div className="font-medium text-white">{item.tributo_codigo}</div>
                      <div className="text-xs text-slate-400">{item.tributo_nome}</div>
                    </TableCell>
                    <TableCell className="text-slate-300">{item.etapa_calculo}</TableCell>
                    <TableCell className="text-right text-slate-200">{formatCurrency(parseDecimal(item.base_calculo))}</TableCell>
                    <TableCell className="text-right text-slate-200">{formatPercent(item.aliquota_aplicada)}</TableCell>
                    <TableCell className="text-right font-medium text-white">{formatCurrency(parseDecimal(item.valor_calculado))}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="border-slate-600 text-slate-300">
                        {item.fonte_dados}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[180px] truncate font-mono text-xs text-slate-400">
                      {item.hash_calculo ?? '-'}
                    </TableCell>
                  </TableRow>
                ))}
                {!memoriaFiltrada.length && (
                  <TableRow className="border-slate-800/80 hover:bg-transparent">
                    <TableCell colSpan={7} className="h-28 text-center text-sm text-slate-400">
                      {memoriaQuery.isLoading ? 'Carregando memoria de calculo...' : 'Nenhuma memoria de calculo encontrada.'}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
