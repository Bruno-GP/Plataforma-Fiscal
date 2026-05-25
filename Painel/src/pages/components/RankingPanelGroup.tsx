import { RankingCard } from './RankingCard';

export interface RankingConfig {
  title: string;
  description: string;
  items: any[];
  emptyMessage: string;
  loadingMessage?: string;
}

interface RankingPanelGroupProps {
  rankings: RankingConfig[];
  isLoading: boolean;
  totalValue: string;
  columns?: 1 | 2 | 3;
}

const columnsClassName: Record<NonNullable<RankingPanelGroupProps['columns']>, string> = {
  1: 'lg:grid-cols-1',
  2: 'lg:grid-cols-2',
  3: 'lg:grid-cols-3',
};

export function RankingPanelGroup({ rankings, isLoading, totalValue, columns = 3 }: RankingPanelGroupProps) {
  return (
    <div className={`grid gap-6 ${columnsClassName[columns]}`}>
      {rankings.map((ranking, index) => (
        <RankingCard
          key={`${ranking.title}-${index}`}
          title={ranking.title}
          description={ranking.description}
          items={ranking.items}
          isLoading={isLoading}
          loadingMessage={ranking.loadingMessage ?? 'Carregando ranking...'}
          emptyMessage={ranking.emptyMessage}
          totalValue={totalValue}
          showAbcReport={false}
          showAbcClassification={false}
        />
      ))}
    </div>
  );
}
