import type { LucideIcon } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DashboardStatCardProps {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend: 'up' | 'down' | 'neutral';
  isLoading: boolean;
}

export function DashboardStatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
  isLoading,
  accentClass = 'border-l-slate-700',
}: DashboardStatCardProps) {
  return (
    <Card
      className={`rounded-2xl border-l-4 border-slate-800/70 bg-gradient-to-br from-slate-950/80 via-slate-900/85 to-slate-950/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_20px_45px_-30px_rgba(0,0,0,0.9)] backdrop-blur ${accentClass}`}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-sm font-medium text-slate-300">{title}</CardTitle>
        <Icon className="h-4 w-4 text-slate-300/80" />
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold text-white font-bold">{isLoading ? 'Carregando...' : value}</div>
        <p
          className={`mt-2 text-xs font-medium ${
            trend === 'up'
              ? 'text-emerald-400'
              : trend === 'down'
                ? 'text-rose-400'
                : 'text-slate-400'
          }`}
        >
          {isLoading ? '--' : `${description} vs mês anterior`}
        </p>
      </CardContent>
    </Card>
  );
}