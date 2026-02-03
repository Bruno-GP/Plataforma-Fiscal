import { useEffect, useMemo, useState } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

interface DashboardRankingItem {
  key: string;
  title: string;
  subtitle: string;
  value: string;
  rawValue: number;
  percent: number | null;
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
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    if (items.length) {
      setSelectedKey(items[0].key);
    } else {
      setSelectedKey(null);
    }
  }, [items]);

  const selectedItem = useMemo(() => {
    if (!items.length) {
      return null;
    }

    return items.find((item) => item.key === selectedKey) ?? items[0];
  }, [items, selectedKey]);

  const selectedPercent = selectedItem?.percent ?? 0;
  const progressValue = Math.min(Math.max(selectedPercent, 0), 100);

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
            <>
              <div className="space-y-2 rounded-xl border border-slate-800/70 bg-slate-950/40 p-3">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>Faturamento selecionado</span>
                  {selectedItem ? (
                    <span className="font-medium text-foreground">{selectedItem.value}</span>
                  ) : null}
                </div>
                <Progress value={progressValue} className="h-2" />
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{selectedItem?.title ?? 'Selecione um item'}</span>
                  <span>
                    {selectedItem?.percent !== null
                      ? `${selectedPercent.toFixed(1)}% do período`
                      : 'Participação não informada'}
                  </span>
                </div>
              </div>
              {items.map((item) => {
                const isSelected = item.key === selectedItem?.key;

                return (
                  <button
                    type="button"
                    key={item.key}
                    onClick={() => setSelectedKey(item.key)}
                    className="flex w-full items-center justify-between gap-3 border-b border-slate-800/70 pb-2 text-left transition hover:text-foreground/90 last:border-0"
                  >
                    <div>
                      <p className={`font-medium ${isSelected ? 'text-foreground' : ''}`}>
                        {item.title}
                      </p>
                      <p className="text-sm text-muted-foreground">{item.subtitle}</p>
                    </div>
                    <span className={`text-sm font-medium ${isSelected ? 'text-foreground' : ''}`}>
                      {item.value}
                    </span>
                  </button>
                );
              })}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">{emptyMessage}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}