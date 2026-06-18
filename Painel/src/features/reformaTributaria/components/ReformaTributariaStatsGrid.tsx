import { StatCard } from '@/pages/components/StatCard';

import type { ReformaTributariaStatConfig } from '../types';

interface ReformaTributariaStatsGridProps {
  stats: ReformaTributariaStatConfig[];
  isLoading: boolean;
}

export function ReformaTributariaStatsGrid({ stats, isLoading }: ReformaTributariaStatsGridProps) {
  return (
    <div className="stat-card-grid">
      {stats.map((stat) => (
        <StatCard key={stat.title} {...stat} isLoading={isLoading} />
      ))}
    </div>
  );
}
