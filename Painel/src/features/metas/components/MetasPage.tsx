import { useMemo, useState } from 'react';
import {
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  LineChart,
  ListChecks,
  Plus,
  Sparkles,
  Target,
  XCircle,
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import {
  CartesianGrid,
  Line,
  LineChart as RechartsLineChart,
  ResponsiveContainer,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { StatCard } from '@/pages/components/StatCard';
import { cn } from '@/lib/utils';

import type {
  AnaliseMetaResponse,
  IndicadorHistoricoPontoResponse,
  IndicadorResponse,
  MetaResponse,
  PeriodoTipo,
  StatusMeta,
  StatusRitmo,
  Tendencia,
  TipoMeta,
  UnidadeIndicador,
} from '@/services/metas';

import { useMetasPageData } from '../hooks/useMetasPageData';

const STATUS_RITMO_CONFIG: Record<StatusRitmo, { label: string; variant: 'default' | 'warning' | 'destructive' }> = {
  no_caminho: { label: 'No caminho', variant: 'default' },
  em_risco: { label: 'Em risco', variant: 'warning' },
  fora_da_rota: { label: 'Fora da rota', variant: 'destructive' },
};

const TIPO_META_LABELS: Record<TipoMeta, string> = {
  crescimento: 'Crescimento',
  reducao: 'Redução',
  manutencao: 'Manutenção',
};

const PERIODO_LABELS: Record<PeriodoTipo, string> = {
  mensal: 'Mensal',
  trimestral: 'Trimestral',
  anual: 'Anual',
  custom: 'Personalizado',
};

const TENDENCIA_LABELS: Record<Tendencia, string> = {
  crescimento_forte: 'Crescimento forte',
  crescimento_leve: 'Crescimento leve',
  estavel: 'Estável',
  queda_leve: 'Queda leve',
  queda_forte: 'Queda forte',
};

const STATUS_META_LABELS: Record<StatusMeta, string> = {
  ativa: 'Ativa',
  atingida: 'Atingida',
  nao_atingida: 'Não atingida',
  cancelada: 'Cancelada',
};

const formatMetaPeriod = (period: string) => {
  try {
    return format(parseISO(period), 'MMM/yyyy', { locale: ptBR });
  } catch {
    return period;
  }
};

const formatLongPeriod = (start: string, end: string) => {
  try {
    return `${format(parseISO(start), 'MMM/yyyy', { locale: ptBR })} até ${format(parseISO(end), 'MMM/yyyy', {
      locale: ptBR,
    })}`;
  } catch {
    return `${start} até ${end}`;
  }
};

const formatIndicatorUnit = (value: number, unidade?: UnidadeIndicador | null) => {
  if (unidade === 'moeda') {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
  }

  if (unidade === 'percentual') {
    return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value)}%`;
  }

  if (unidade === 'dias') {
    return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value)} dias`;
  }

  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value);
};

const formatCompact = (value: number) => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value);

function DetailStat({
  title,
  value,
  description,
  tone = 'neutral',
}: {
  title: string;
  value: string;
  description: string;
  tone?: 'neutral' | 'positive' | 'warning';
}) {
  const toneClasses: Record<typeof tone, string> = {
    neutral: 'border-slate-800 bg-slate-900/80',
    positive: 'border-emerald-400/25 bg-emerald-400/10',
    warning: 'border-amber-400/25 bg-amber-400/10',
  };

  return (
    <div className={cn('min-w-0 rounded-md border p-4', toneClasses[tone])}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{title}</p>
      <p className="mt-2 break-words text-xl font-semibold text-slate-100">{value}</p>
      <p className="mt-1 break-words text-xs leading-5 text-slate-400">{description}</p>
    </div>
  );
}

function ChartPanel({
  meta,
  analysis,
  unit,
}: {
  meta: MetaResponse;
  analysis: AnaliseMetaResponse;
  unit?: UnidadeIndicador | null;
}) {
  const data = analysis.serie_historica.map((point) => ({
    label: formatMetaPeriod(point.periodo),
    historico: point.valor,
    meta: meta.valor_alvo,
    projection: null as number | null,
  }));

  if (data.length) {
    data[data.length - 1] = {
      ...data[data.length - 1],
      projection: analysis.valor_realizado_atual,
    };
  }

  data.push({
    label: 'Projeção',
    historico: null,
    meta: meta.valor_alvo,
    projection: analysis.projecao_fim_periodo,
  });

  return (
    <div className="h-[340px] overflow-hidden rounded-md border border-slate-800 bg-slate-900/80 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart data={data} margin={{ top: 12, right: 10, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
          <XAxis
            dataKey="label"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: 'rgba(148,163,184,0.2)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: 'rgba(148,163,184,0.2)' }}
            tickLine={false}
            width={56}
            tickFormatter={(value) => formatCompact(Number(value))}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(8,17,31,0.95)',
              border: '1px solid rgba(51,65,85,0.9)',
              borderRadius: '0.75rem',
              color: '#e2e8f0',
            }}
            labelStyle={{ color: '#7dd3fc', fontWeight: 700 }}
            formatter={(value: number | string) => [formatIndicatorUnit(Number(value), unit), 'Valor']}
          />
          <ReferenceLine y={meta.valor_alvo} stroke="rgba(56,189,248,0.75)" strokeDasharray="5 5" />
          <Line
            type="monotone"
            dataKey="historico"
            stroke="#38bdf8"
            strokeWidth={2.5}
            dot={{ r: 3.5, fill: '#38bdf8' }}
            activeDot={{ r: 5 }}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="projection"
            stroke="#facc15"
            strokeWidth={2.5}
            strokeDasharray="6 5"
            dot={{ r: 4, fill: '#facc15' }}
            connectNulls={false}
          />
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-72 w-full" />
    </div>
  );
}

function MetaListItem({
  meta,
  analysis,
  indicator,
  selected,
  onClick,
  compact = false,
}: {
  meta: MetaResponse;
  analysis?: AnaliseMetaResponse | null;
  indicator?: IndicadorResponse | null;
  selected: boolean;
  onClick: () => void;
  compact?: boolean;
}) {
  const progress = analysis ? Math.min(analysis.percentual_atingido, 100) : 0;
  const rhythm = analysis ? STATUS_RITMO_CONFIG[analysis.status_ritmo] : null;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full rounded-md border text-left transition duration-200',
        compact ? 'p-3' : 'p-4',
        'border-slate-800 bg-slate-900/80 hover:border-sky-500/55',
        selected && 'border-sky-500/70 bg-slate-900',
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className={cn('truncate font-semibold text-slate-100', compact ? 'text-sm' : 'text-base')}>{meta.titulo}</p>
          <p className={cn('mt-1 text-slate-400', compact ? 'text-xs' : 'text-sm')}>{indicator?.nome ?? `Indicador #${meta.indicador_id}`}</p>
          <p className={cn('mt-1 text-slate-500', compact ? 'text-[11px]' : 'text-xs')}>{formatLongPeriod(meta.periodo_inicio, meta.periodo_fim)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={meta.status === 'cancelada' ? 'outline' : 'default'}>{STATUS_META_LABELS[meta.status]}</Badge>
          {rhythm ? <Badge variant={rhythm.variant}>{rhythm.label}</Badge> : null}
        </div>
      </div>

      <div className={cn('space-y-2', compact ? 'mt-3' : 'mt-4')}>
        <div className="flex items-center justify-between text-sm">
          <span className={cn('text-slate-400', compact ? 'text-xs' : 'text-sm')}>Progresso</span>
          <span className={cn('font-semibold text-slate-100', compact ? 'text-xs' : 'text-sm')}>{formatCompact(progress)}%</span>
        </div>
        <Progress value={progress} className={cn('bg-slate-900', compact ? 'h-2' : 'h-2.5')} />
      </div>
    </button>
  );
}

function IndicatorPreview({
  indicator,
  history,
  isLoading,
}: {
  indicator: IndicadorResponse | null;
  history: IndicadorHistoricoPontoResponse[];
  isLoading: boolean;
}) {
  return (
    <div className="space-y-3 rounded-md border border-slate-800 bg-slate-900/80 p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Prévia do indicador</p>
          <p className="mt-1 truncate text-sm text-slate-300">
            {indicator?.nome ?? 'Selecione um indicador para ver o histórico'}
          </p>
        </div>
        {indicator ? <Badge variant="outline">{indicator.unidade}</Badge> : null}
      </div>

      {isLoading ? (
        <Skeleton className="h-56 w-full" />
      ) : history.length ? (
        <>
          <div className="h-56 overflow-hidden rounded-md border border-slate-800 bg-slate-900/80 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsLineChart
                data={history.map((point) => ({
                  label: formatMetaPeriod(point.periodo),
                  valor: point.valor,
                }))}
                margin={{ top: 10, right: 8, bottom: 8, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.14)" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  axisLine={{ stroke: 'rgba(148,163,184,0.18)' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  axisLine={{ stroke: 'rgba(148,163,184,0.18)' }}
                  tickLine={false}
                  width={48}
                  tickFormatter={(value) => formatCompact(Number(value))}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(8,17,31,0.95)',
                    border: '1px solid rgba(51,65,85,0.9)',
                    borderRadius: '0.75rem',
                    color: '#e2e8f0',
                  }}
                  labelStyle={{ color: '#7dd3fc', fontWeight: 700 }}
                  formatter={(value) => [formatIndicatorUnit(Number(value), indicator?.unidade), indicator?.nome ?? 'Valor']}
                />
                <Line type="monotone" dataKey="valor" stroke="#38bdf8" strokeWidth={2.5} dot={{ r: 3.5, fill: '#38bdf8' }} activeDot={{ r: 5 }} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            {history.slice(-3).map((point) => (
              <div key={point.periodo} className="rounded-md border border-slate-800 bg-slate-900/80 px-3 py-2">
                <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{formatMetaPeriod(point.periodo)}</p>
                <p className="mt-1 break-words text-sm font-semibold text-slate-100">
                  {formatIndicatorUnit(point.valor, indicator?.unidade)}
                </p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/45 px-4 py-8 text-sm text-slate-400">
          Não há histórico suficiente para o indicador escolhido.
        </div>
      )}
    </div>
  );
}

export function MetasPage() {
  const data = useMetasPageData();
  const [activeMetaSearch, setActiveMetaSearch] = useState('');
  const selectedMeta = data.selectedMeta;
  const selectedAnalysis = data.selectedMetaAnalysis;
  const selectedUnit = data.selectedIndicator?.unidade ?? null;
  const currentIndicatorHistory = data.selectedIndicatorHistory?.resultados ?? [];

  const stats = [
    {
      title: 'Metas ativas',
      value: String(data.activeMetas.length),
      description: 'Em acompanhamento neste momento.',
      icon: Target,
      trend: 'neutral',
      accentClass: 'border-l-sky-400/70',
    },
    {
      title: 'No caminho',
      value: String(data.rhythmSummary.no_caminho),
      description: 'Ritmo saudável.',
      icon: CheckCircle2,
      trend: 'up',
      accentClass: 'border-l-emerald-400/70',
    },
    {
      title: 'Em risco',
      value: String(data.rhythmSummary.em_risco),
      description: 'Atenção imediata.',
      icon: CircleAlert,
      trend: 'neutral',
      accentClass: 'border-l-amber-400/70',
    },
    {
      title: 'Fora da rota',
      value: String(data.rhythmSummary.fora_da_rota),
      description: 'Baixa chance de fechar.',
      icon: XCircle,
      trend: 'down',
      accentClass: 'border-l-rose-400/70',
    },
  ];

  const visibleMetas = useMemo(() => {
    const query = activeMetaSearch.trim().toLowerCase();
    const source = data.activeMetas;

    if (!query) {
      return source;
    }

    return source.filter((meta) => {
      const indicator = data.indicatorsById[meta.indicador_id];
      return (
        meta.titulo.toLowerCase().includes(query) ||
        meta.descricao?.toLowerCase().includes(query) ||
        indicator?.nome.toLowerCase().includes(query) ||
        indicator?.chave.toLowerCase().includes(query)
      );
    });
  }, [activeMetaSearch, data.activeMetas, data.indicatorsById]);

  return (
    <section className="space-y-6 py-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Metas</h1>
          <p className="text-muted-foreground">
            Acompanhe metas com contexto, histórico e diagnóstico automático de cada indicador.
          </p>
        </div>
        <Button onClick={data.openCreateDialog} disabled={!data.indicatorsQuery.data?.length}>
          <Plus className="mr-2 h-4 w-4" />
          Nova meta
        </Button>
      </div>

      {data.indicatorsQuery.isError || data.metasQuery.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar metas</AlertTitle>
          <AlertDescription>
            {data.indicatorsQuery.error instanceof Error
              ? data.indicatorsQuery.error.message
              : data.metasQuery.error instanceof Error
                ? data.metasQuery.error.message
                : 'Não foi possível buscar os dados do módulo de metas.'}
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="stat-card-grid">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={data.metasQuery.isLoading} appendPreviousMonthLabel={false} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(20rem,0.4fr)_minmax(0,0.6fr)] xl:items-start">
        <Card className="min-w-0 xl:sticky xl:top-6 xl:max-h-[calc(100vh-9rem)] xl:overflow-hidden">
          <CardHeader className="tv-panel-header rounded-t-[inherit]">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-xl">Metas ativas</CardTitle>
                  <CardDescription>Lista de acompanhamento com ritmo estimado e diagnóstico resumido.</CardDescription>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <ListChecks className="h-4 w-4 text-sky-300" />
                  {visibleMetas.length} metas
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="metas-search" className="text-xs uppercase tracking-[0.18em] text-slate-500">
                  Pesquisar
                </Label>
                <Input
                  id="metas-search"
                  value={activeMetaSearch}
                  onChange={(event) => setActiveMetaSearch(event.target.value)}
                  placeholder="Buscar por título, descrição ou indicador..."
                />
              </div>
            </div>
          </CardHeader>
          <CardContent className="min-w-0 pt-6">
            {data.metasQuery.isLoading ? (
              <LoadingSkeleton />
            ) : visibleMetas.length ? (
              <div className="max-h-[calc(100vh-28rem)] space-y-3 overflow-y-auto pr-2">
                {visibleMetas.map((meta) => (
                  <MetaListItem
                    key={meta.id}
                    meta={meta}
                    analysis={data.analysesByMetaId[meta.id] ?? null}
                    indicator={data.indicatorsById[meta.indicador_id] ?? null}
                    selected={meta.id === data.selectedMetaId}
                    onClick={() => data.setSelectedMetaId(meta.id)}
                    compact
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/45 px-4 py-10 text-center text-sm text-slate-400">
                {activeMetaSearch.trim()
                  ? 'Nenhuma meta ativa corresponde à pesquisa.'
                  : 'Nenhuma meta ativa encontrada. Use o formulário ao lado para criar a primeira meta.'}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="min-w-0">
          <Card className="min-w-0">
            <CardHeader className="tv-panel-header rounded-t-[inherit]">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <CardTitle className="flex items-center gap-2 text-xl">
                    <LineChart className="h-5 w-5 text-sky-300" />
                    Detalhe da meta
                  </CardTitle>
                  <CardDescription>Histórico, projeção e leitura automática do indicador selecionado.</CardDescription>
                </div>

                {selectedMeta ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <Button variant="outline" onClick={() => data.openEditDialog(selectedMeta)}>
                      Editar
                    </Button>
                    <Button variant="destructive" onClick={() => data.handleCancelMeta(selectedMeta)} disabled={data.isCanceling}>
                      Cancelar
                    </Button>
                  </div>
                ) : null}
              </div>
            </CardHeader>
            <CardContent className="min-w-0 space-y-8 pt-6">
              {selectedMeta && selectedAnalysis ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={STATUS_RITMO_CONFIG[selectedAnalysis.status_ritmo].variant}>
                      {STATUS_RITMO_CONFIG[selectedAnalysis.status_ritmo].label}
                    </Badge>
                    <Badge variant={selectedMeta.status === 'cancelada' ? 'outline' : 'default'}>
                      {STATUS_META_LABELS[selectedMeta.status]}
                    </Badge>
                    <Badge variant="outline">{TENDENCIA_LABELS[selectedAnalysis.tendencia]}</Badge>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <DetailStat
                      title="Alvo"
                      value={formatIndicatorUnit(selectedAnalysis.valor_alvo, selectedUnit)}
                      description={selectedMeta.titulo}
                    />
                    <DetailStat
                      title="Realizado"
                      value={formatIndicatorUnit(selectedAnalysis.valor_realizado_atual, selectedUnit)}
                      description="Valor acumulado no período"
                    />
                    <DetailStat
                      title="Atingimento"
                      value={`${formatCompact(selectedAnalysis.percentual_atingido)}%`}
                      description={`${formatCompact(selectedAnalysis.tempo_decorrido_pct)}% do tempo decorrido`}
                      tone={
                        selectedAnalysis.percentual_atingido >= selectedAnalysis.tempo_decorrido_pct
                          ? 'positive'
                          : 'warning'
                      }
                    />
                    <DetailStat
                      title="Projeção"
                      value={formatIndicatorUnit(selectedAnalysis.projecao_fim_periodo, selectedUnit)}
                      description="Estimativa até o fim do período"
                    />
                  </div>

                  <div className="rounded-md border border-slate-800 bg-slate-900/80 p-5 md:p-6">
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-sky-400/25 bg-sky-400/10 text-sky-300">
                        <Sparkles className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 space-y-1.5">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Diagnóstico</p>
                        <p className="break-words text-base leading-7 text-slate-200">{selectedAnalysis.diagnostico}</p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Histórico e comparação
                    </p>
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                      <DetailStat
                        title="Média"
                        value={formatIndicatorUnit(selectedAnalysis.media_periodos_anteriores, selectedUnit)}
                        description="Histórico dos períodos anteriores"
                      />
                      <DetailStat
                        title="Mediana"
                        value={formatIndicatorUnit(selectedAnalysis.mediana_periodos_anteriores, selectedUnit)}
                        description="Referência central do histórico"
                      />
                      <DetailStat
                        title="Desvio padrão"
                        value={formatIndicatorUnit(selectedAnalysis.desvio_padrao_periodos_anteriores, selectedUnit)}
                        description="Dispersão dos períodos anteriores"
                      />
                      <DetailStat
                        title="Ano anterior"
                        value={
                          selectedAnalysis.comparativo_ano_anterior_pct === null
                            ? 'Sem comparação'
                            : `${formatCompact(selectedAnalysis.comparativo_ano_anterior_pct)}%`
                        }
                        description="Comparação com o mesmo período anterior"
                      />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Evolução do indicador
                    </p>
                    <ChartPanel meta={selectedMeta} analysis={selectedAnalysis} unit={selectedUnit} />
                  </div>

                  <div className="rounded-md border border-slate-800 bg-slate-900/80 p-5 md:p-6">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Série histórica</p>
                        <p className="mt-1 text-sm text-slate-300">
                          {selectedAnalysis.serie_historica.length} pontos carregados da base materializada.
                        </p>
                      </div>
                      <CalendarDays className="h-5 w-5 text-sky-300" />
                    </div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      {selectedAnalysis.serie_historica.slice(-6).map((point) => (
                        <div key={point.periodo} className="rounded-md border border-slate-800 bg-slate-900/80 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{formatMetaPeriod(point.periodo)}</p>
                          <p className="mt-1.5 break-words text-sm font-semibold text-slate-100">
                            {formatIndicatorUnit(point.valor, selectedUnit)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : selectedMeta && data.selectedMetaAnalysisLoading ? (
                <div className="flex min-h-[420px] items-center justify-center rounded-md border border-dashed border-slate-700 bg-slate-950/45 px-4 text-center text-sm text-slate-400">
                  Carregando a análise da meta selecionada...
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/45 px-4 py-10 text-center text-sm text-slate-400">
                  Clique em uma meta na lista para ver o detalhe completo.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={data.isCreateDialogOpen} onOpenChange={data.setIsCreateDialogOpen}>
        <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto border-slate-800 bg-slate-900 text-slate-100">
          <DialogHeader>
            <DialogTitle>Nova meta</DialogTitle>
            <DialogDescription>Escolha um indicador e veja o histórico antes de definir o alvo.</DialogDescription>
          </DialogHeader>

          <form onSubmit={data.handleCreateSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="metas-indicador">Indicador</Label>
                <Select
                  value={data.createForm.indicador_id ? String(data.createForm.indicador_id) : ''}
                  onValueChange={(value) => {
                    const indicadorId = Number(value);
                    data.setSelectedIndicatorId(indicadorId);
                    data.setCreateForm((current) => ({ ...current, indicador_id: indicadorId }));
                  }}
                  disabled={data.indicatorsQuery.isLoading || !data.indicatorsQuery.data?.length}
                >
                  <SelectTrigger id="metas-indicador">
                    <SelectValue placeholder="Selecione um indicador" />
                  </SelectTrigger>
                  <SelectContent>
                    {data.indicatorsQuery.data?.map((indicator) => (
                      <SelectItem key={indicator.id} value={String(indicator.id)}>
                        {indicator.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="metas-titulo">Título</Label>
                <Input
                  id="metas-titulo"
                  value={data.createForm.titulo}
                  onChange={(event) => data.setCreateForm((current) => ({ ...current, titulo: event.target.value }))}
                  placeholder="Ex.: Crescer faturamento do canal direto"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="metas-tipo">Tipo de meta</Label>
                <Select
                  value={data.createForm.tipo_meta}
                  onValueChange={(value) => data.setCreateForm((current) => ({ ...current, tipo_meta: value as TipoMeta }))}
                >
                  <SelectTrigger id="metas-tipo">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(TIPO_META_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="metas-periodo">Período</Label>
                <Select
                  value={data.createForm.periodo_tipo}
                  onValueChange={(value) =>
                    data.setCreateForm((current) => ({ ...current, periodo_tipo: value as PeriodoTipo }))
                  }
                >
                  <SelectTrigger id="metas-periodo">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(PERIODO_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="metas-inicio">Início</Label>
                <Input
                  id="metas-inicio"
                  type="date"
                  value={data.createForm.periodo_inicio}
                  onChange={(event) => data.setCreateForm((current) => ({ ...current, periodo_inicio: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="metas-fim">Fim</Label>
                <Input
                  id="metas-fim"
                  type="date"
                  value={data.createForm.periodo_fim}
                  onChange={(event) => data.setCreateForm((current) => ({ ...current, periodo_fim: event.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="metas-valor">Valor alvo</Label>
              <Input
                id="metas-valor"
                inputMode="decimal"
                value={data.createForm.valor_alvo}
                onChange={(event) => data.setCreateForm((current) => ({ ...current, valor_alvo: event.target.value }))}
                placeholder="Ex.: 50000"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="metas-descricao">Descrição</Label>
              <Textarea
                id="metas-descricao"
                value={data.createForm.descricao}
                onChange={(event) => data.setCreateForm((current) => ({ ...current, descricao: event.target.value }))}
                placeholder="Contexto da meta, estratégia, equipe responsável..."
                className="min-h-24"
              />
            </div>

            <IndicatorPreview
              indicator={data.selectedIndicator}
              history={currentIndicatorHistory}
              isLoading={data.selectedIndicatorHistoryLoading}
            />

            <DialogFooter className="gap-2">
              <Button type="button" variant="outline" onClick={() => data.setIsCreateDialogOpen(false)}>
                Fechar
              </Button>
              <Button type="submit" disabled={data.isCreating || !data.indicatorsQuery.data?.length}>
                {data.isCreating ? 'Salvando...' : 'Criar meta'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={data.isEditDialogOpen} onOpenChange={data.setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl border-slate-800 bg-slate-900 text-slate-100">
          <DialogHeader>
            <DialogTitle>Editar meta</DialogTitle>
            <DialogDescription>
              Ajuste título, valor alvo, descrição e status sem alterar o indicador ou o período original.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={data.handleEditSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="edit-titulo">Título</Label>
                <Input
                  id="edit-titulo"
                  value={data.editForm.titulo}
                  onChange={(event) => data.setEditForm((current) => ({ ...current, titulo: event.target.value }))}
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="edit-descricao">Descrição</Label>
                <Textarea
                  id="edit-descricao"
                  value={data.editForm.descricao}
                  onChange={(event) => data.setEditForm((current) => ({ ...current, descricao: event.target.value }))}
                  className="min-h-24"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-valor">Valor alvo</Label>
                <Input
                  id="edit-valor"
                  inputMode="decimal"
                  value={data.editForm.valor_alvo}
                  onChange={(event) => data.setEditForm((current) => ({ ...current, valor_alvo: event.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-status">Status</Label>
                <Select
                  value={data.editForm.status}
                  onValueChange={(value) => data.setEditForm((current) => ({ ...current, status: value as StatusMeta }))}
                >
                  <SelectTrigger id="edit-status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(STATUS_META_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter className="gap-2">
              <Button type="button" variant="outline" onClick={() => data.setIsEditDialogOpen(false)}>
                Fechar
              </Button>
              <Button type="submit" disabled={data.isUpdating}>
                {data.isUpdating ? 'Salvando...' : 'Salvar alterações'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(data.metaPendingCancel)} onOpenChange={(open) => !open && data.setMetaPendingCancel(null)}>
        <AlertDialogContent className="border-slate-800 bg-slate-900 text-slate-100">
          <AlertDialogHeader>
            <AlertDialogTitle>Cancelar meta</AlertDialogTitle>
            <AlertDialogDescription>
              {data.metaPendingCancel
                ? `A meta "${data.metaPendingCancel.titulo}" sai do acompanhamento ativo, mas continua no histórico com status "Cancelada".`
                : ''}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Voltar</AlertDialogCancel>
            <AlertDialogAction
              onClick={data.confirmCancelMeta}
              disabled={data.isCanceling}
              className="bg-rose-600 text-white hover:bg-rose-500"
            >
              {data.isCanceling ? 'Cancelando...' : 'Cancelar meta'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}
