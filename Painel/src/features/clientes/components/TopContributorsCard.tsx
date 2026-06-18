import { Users } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import type { ClienteRankingItem } from '../types';

interface TopContributorsCardProps {
  topClientesItems: ClienteRankingItem[];
}

export function TopContributorsCard({ topClientesItems }: TopContributorsCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="tv-panel-header">
        <CardTitle>Maiores contribuintes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 p-5">
        {topClientesItems.slice(0, 4).map((cliente, index) => (
          <div key={cliente.key} className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-1 py-2">
            <span className="font-mono text-sm font-semibold text-sky-300">{String(index + 1).padStart(2, '0')}</span>
            <span className="min-w-0">
              <span className="block truncate font-semibold text-slate-100">{cliente.title}</span>
              <span className="text-xs text-slate-400">{cliente.subtitle}</span>
            </span>
            <span className="text-sm font-semibold text-slate-50">{cliente.percent?.toFixed(1) ?? '0.0'}%</span>
          </div>
        ))}

        {!topClientesItems.length && (
          <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/30 px-4 py-8 text-center text-sm text-slate-400">
            <Users className="mx-auto mb-2 h-5 w-5" />
            Nenhum cliente no recorte atual.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
