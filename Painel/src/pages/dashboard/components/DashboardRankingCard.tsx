import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface DashboardRankingItem {
  key: string;
  title: string;
  subtitle: string;
  value: string;
}

interface DashboardRankingCardProps {
  title: string;
  description: string;
  items: DashboardRankingItem[];
  isLoading: boolean;
  loadingMessage: string;
  emptyMessage: string;
}

export function DashboardRankingCard({
  title,
  description,
  items,
  isLoading,
  loadingMessage,
  emptyMessage,
}: DashboardRankingCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">{loadingMessage}</p>
          ) : items.length ? (
            items.map((item) => (
              <div
                key={item.key}
                className="flex items-center justify-between border-b pb-2 last:border-0"
              >
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="text-sm text-muted-foreground">{item.subtitle}</p>
                </div>
                <span className="text-sm font-medium">{item.value}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">{emptyMessage}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}