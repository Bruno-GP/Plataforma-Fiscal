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
    <Card className="rounded-2xl border-slate-800/70 bg-gradient-to-br from-slate-950/80 via-slate-900/85 to-slate-950/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_20px_45px_-30px_rgba(0,0,0,0.9)] backdrop-blur">
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
                className="flex items-center justify-between border-b border-slate-800/70 pb-2 last:border-0"
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