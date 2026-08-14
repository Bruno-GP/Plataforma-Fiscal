import {
  CartesianGrid,
  Line,
  LineChart as RechartsLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

import type { IndicadorHistoricoPontoResponse, IndicadorResponse } from '@/services/metas';

import { formatCompact, formatIndicatorUnit, formatMetaPeriod } from '../helpers/metasFormatters';

export function MetaIndicatorPreview({
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
