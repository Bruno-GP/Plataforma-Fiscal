import { CheckCircle2, CircleAlert, Target, XCircle } from 'lucide-react';

import { StatCard } from '@/pages/components/StatCard';

import type { StatusRitmo } from '@/services/metas';

export function MetasStatsGrid({
  activeMetasCount,
  rhythmSummary,
  isLoading,
}: {
  activeMetasCount: number;
  rhythmSummary: Record<StatusRitmo, number>;
  isLoading: boolean;
}) {
  const stats = [
    {
      title: 'Metas ativas',
      value: String(activeMetasCount),
      description: 'Em acompanhamento neste momento.',
      icon: Target,
      trend: 'neutral',
      accentClass: 'border-l-sky-400/70',
    },
    {
      title: 'No caminho',
      value: String(rhythmSummary.no_caminho),
      description: 'Ritmo saudável.',
      icon: CheckCircle2,
      trend: 'up',
      accentClass: 'border-l-emerald-400/70',
    },
    {
      title: 'Em risco',
      value: String(rhythmSummary.em_risco),
      description: 'Atenção imediata.',
      icon: CircleAlert,
      trend: 'neutral',
      accentClass: 'border-l-amber-400/70',
    },
    {
      title: 'Fora da rota',
      value: String(rhythmSummary.fora_da_rota),
      description: 'Baixa chance de fechar.',
      icon: XCircle,
      trend: 'down',
      accentClass: 'border-l-rose-400/70',
    },
  ];

  return (
    <div className="stat-card-grid">
      {stats.map((stat) => (
        <StatCard key={stat.title} {...stat} isLoading={isLoading} appendPreviousMonthLabel={false} />
      ))}
    </div>
  );
}
