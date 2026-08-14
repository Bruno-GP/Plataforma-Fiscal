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

import type { AnaliseMetaResponse, MetaResponse, UnidadeIndicador } from '@/services/metas';

import { formatCompact, formatIndicatorUnit, formatMetaPeriod } from '../helpers/metasFormatters';

export function MetaChartPanel({
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
