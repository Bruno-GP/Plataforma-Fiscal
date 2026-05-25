import type { LucideIcon } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend: string;
  isLoading: boolean;
  accentClass?: string;
  appendPreviousMonthLabel?: boolean;
}

export function StatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
  isLoading,
  accentClass = 'border-l-slate-700',
  appendPreviousMonthLabel = true,
}: StatCardProps) {
  const trendTone =
    trend === 'up'
      ? 'text-emerald-300'
      : trend === 'down'
        ? 'text-rose-300'
        : 'text-slate-400';

  return (
    <Card
      className={cn(
        'group min-h-[156px] overflow-hidden border-l-4 bg-gradient-to-br from-[#172033] via-[#121c31] to-[#0b1425] transition-transform duration-200 hover:-translate-y-0.5 hover:border-slate-500/80',
        accentClass,
      )}
    >
      <CardHeader className="flex flex-row items-start justify-between gap-4 pb-3">
        <CardTitle className="max-w-[13rem] text-sm font-semibold leading-snug text-slate-300">
          {title}
        </CardTitle>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-700/80 bg-slate-950/45 text-sky-300 transition-colors group-hover:border-sky-400/50">
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="truncate text-3xl font-bold tracking-tight text-slate-50">
          {isLoading ? 'Carregando...' : value}
        </div>
        <p className={cn('mt-3 text-xs font-semibold', trendTone)}>
          {isLoading ? '--' : appendPreviousMonthLabel ? `${description} vs mes anterior` : description}
        </p>
      </CardContent>
    </Card>
  );
}
