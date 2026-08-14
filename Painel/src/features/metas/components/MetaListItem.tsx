import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

import type { AnaliseMetaResponse, IndicadorResponse, MetaResponse } from '@/services/metas';

import { formatCompact, formatLongPeriod } from '../helpers/metasFormatters';
import { STATUS_META_LABELS, STATUS_RITMO_CONFIG } from '../helpers/metasLabels';

export function MetaListItem({
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
