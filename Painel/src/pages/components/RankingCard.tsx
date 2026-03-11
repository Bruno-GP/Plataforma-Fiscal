import { useEffect, useMemo, useState } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

interface RankingItem {
  key: string;
  title: string;
  subtitle: string;
  value: string;
  rawValue: number;
  percent: number | null;
}

interface RankingCardProps {
  title: string;
  description: string;
  items: RankingItem[];
  isLoading: boolean;
  loadingMessage: string;
  emptyMessage: string;
  totalValue: string;
  listClassName?: string;
}

export function RankingCard({
  title,
  description,
  items,
  isLoading,
  loadingMessage,
  emptyMessage,
  totalValue,
  listClassName
}: RankingCardProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    if (!items.length) {
      setSelectedKey(null);
    }
  }, [items]);

  const selectedItem = useMemo(() => {
    if (!items.length) {
      return null;
    }
    if (!selectedKey) {
      return null;
    }

    return items.find((item) => item.key === selectedKey) ?? null;
  }, [items, selectedKey]);

  const hasSelection = Boolean(selectedItem);
  const selectedPercent = selectedItem?.percent ?? 100;
  const headlineLabel = selectedItem ? 'Faturamento selecionado' : 'Faturamento Total';
  const headlineValue = selectedItem?.value ?? totalValue;
  const captionTitle = selectedItem?.title ?? 'Faturamento Total';
  const progressValue = Math.min(Math.max(selectedPercent, 0), 100);

  return (
    <Card className="rounded-2xl border-slate-800/70 bg-gradient-to-br from-slate-950/80 via-slate-900/85 to-slate-950/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_20px_45px_-30px_rgba(0,0,0,0.9)] backdrop-blur">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent onClick={() => setSelectedKey(null)}>
        <div className="space-y-4">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">{loadingMessage}</p>
          ) : items.length ? (
            <>
              <div className="space-y-2 rounded-xl border border-slate-800/70 bg-slate-950/40 p-3">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>{headlineLabel}</span>
                  <span className="font-medium text-foreground">{headlineValue}</span>
                </div>
                <Progress
                  value={progressValue}
                  className="h-2 border border-slate-800/80 bg-slate-900/80 [&>div]:bg-sky-500 [&>div]:transition-all [&>div]:duration-500 [&>div]:ease-out"
                />
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{captionTitle}</span>
                  <span>
                    {selectedItem?.percent !== null
                      ? `${selectedPercent.toFixed(1)}% do período`
                      : 'Participação não informada'}
                  </span>
                </div>
              </div>
              <div className={listClassName}>
                {items.map((item) => {
                  const isSelected = item.key === selectedItem?.key;
                  const isMuted = hasSelection && !isSelected;

                  return (
                    <button
                      type="button"
                      key={item.key}
                      onClick={(event) => {
                        event.stopPropagation();
                        setSelectedKey(item.key);
                      }}
                      className={`flex w-full items-center justify-between gap-3 border-b border-slate-800/70 pb-2 text-left transition-colors duration-300 last:border-0 ${
                        isMuted ? 'text-slate-500' : 'hover:text-foreground/90'
                      }`}
                    >
                      <div>
                        <p
                          className={`font-medium transition-colors duration-300 ${
                            isSelected || !hasSelection ? 'text-foreground' : ''
                          } ${isMuted ? 'text-slate-400' : ''}`}
                        >
                          {item.title}
                        </p>
                        <p
                          className={`text-sm transition-colors duration-300 ${
                            isMuted ? 'text-slate-500' : 'text-muted-foreground'
                          }`}
                        >
                          {item.subtitle}
                        </p>
                      </div>
                      <span
                        className={`text-sm font-medium transition-colors duration-300 ${
                          isSelected || !hasSelection ? 'text-foreground' : ''
                        } ${isMuted ? 'text-slate-400' : ''}`}
                      >
                        {item.value}
                      </span>
                    </button>
                  );
                })}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">{emptyMessage}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}