import { CalendarDays, LineChart, Sparkles } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import type { AnaliseMetaResponse, MetaResponse, UnidadeIndicador } from '@/services/metas';

import { formatCompact, formatIndicatorUnit, formatMetaPeriod } from '../helpers/metasFormatters';
import { STATUS_META_LABELS, STATUS_RITMO_CONFIG, TENDENCIA_LABELS } from '../helpers/metasLabels';
import { MetaChartPanel } from './MetaChartPanel';
import { MetaDetailStat } from './MetaDetailStat';

export function MetaDetailPanel({
  selectedMeta,
  selectedAnalysis,
  selectedAnalysisLoading,
  selectedUnit,
  onEdit,
  onCancel,
  isCanceling,
}: {
  selectedMeta: MetaResponse | null;
  selectedAnalysis: AnaliseMetaResponse | null;
  selectedAnalysisLoading: boolean;
  selectedUnit: UnidadeIndicador | null;
  onEdit: (meta: MetaResponse) => void;
  onCancel: (meta: MetaResponse) => void;
  isCanceling: boolean;
}) {
  return (
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
                <Button variant="outline" onClick={() => onEdit(selectedMeta)}>
                  Editar
                </Button>
                <Button variant="destructive" onClick={() => onCancel(selectedMeta)} disabled={isCanceling}>
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
                <MetaDetailStat
                  title="Alvo"
                  value={formatIndicatorUnit(selectedAnalysis.valor_alvo, selectedUnit)}
                  description={selectedMeta.titulo}
                />
                <MetaDetailStat
                  title="Realizado"
                  value={formatIndicatorUnit(selectedAnalysis.valor_realizado_atual, selectedUnit)}
                  description="Valor acumulado no período"
                />
                <MetaDetailStat
                  title="Atingimento"
                  value={`${formatCompact(selectedAnalysis.percentual_atingido)}%`}
                  description={`${formatCompact(selectedAnalysis.tempo_decorrido_pct)}% do tempo decorrido`}
                  tone={
                    selectedAnalysis.percentual_atingido >= selectedAnalysis.tempo_decorrido_pct
                      ? 'positive'
                      : 'warning'
                  }
                />
                <MetaDetailStat
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
                  <MetaDetailStat
                    title="Média"
                    value={formatIndicatorUnit(selectedAnalysis.media_periodos_anteriores, selectedUnit)}
                    description="Histórico dos períodos anteriores"
                  />
                  <MetaDetailStat
                    title="Mediana"
                    value={formatIndicatorUnit(selectedAnalysis.mediana_periodos_anteriores, selectedUnit)}
                    description="Referência central do histórico"
                  />
                  <MetaDetailStat
                    title="Desvio padrão"
                    value={formatIndicatorUnit(selectedAnalysis.desvio_padrao_periodos_anteriores, selectedUnit)}
                    description="Dispersão dos períodos anteriores"
                  />
                  <MetaDetailStat
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
                <MetaChartPanel meta={selectedMeta} analysis={selectedAnalysis} unit={selectedUnit} />
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
          ) : selectedMeta && selectedAnalysisLoading ? (
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
  );
}
