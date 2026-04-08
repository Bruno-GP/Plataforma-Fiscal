import { RankingCard } from './RankingCard';

export interface RankingConfig {
  title: string;
  description: string;
  items: any[];
  emptyMessage: string;
}

interface RankingPanelGroupProps {
  rankings: RankingConfig[];
  isLoading: boolean;
  totalValue: string;
  columns?: number;
}

export function RankingPanelGroup({ rankings, isLoading, totalValue, columns = 3 }: RankingPanelGroupProps) {
  return (
    <div className={`grid gap-6 lg:grid-cols-${columns}`}>
      {rankings.map((ranking, index) => (
        <RankingCard
          key={`${ranking.title}-${index}`}
          title={ranking.title}
          description={ranking.description}
          items={ranking.items}
          isLoading={isLoading}
          loadingMessage="Carregando ranking..."
          emptyMessage={ranking.emptyMessage}
          totalValue={totalValue}
          showAbcReport={false}
          showAbcClassification={false}
        />
      ))}
    </div>
  );
}
