import { useEffect, useMemo, useState } from 'react';
import { ChevronRight } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { AbcAnalysisReport } from '@/pages/components/Analysis/abcAnalysisReport';
import { calculateAbcCurve } from '@/services/analysisABC';

interface RankingItem {
  key: string;
  title: string;
  subtitle: string;
  value: string;
  rawValue: number;
  percent: number | null;
  badgeLabel?: string;
  badgeClassName?: string;
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
  showAbcReport?: boolean;
  showAbcClassification?: boolean;
}

export function RankingCard({
  title,
  description,
  items,
  isLoading,
  loadingMessage,
  emptyMessage,
  totalValue,
  listClassName,
  showAbcReport = true,
  showAbcClassification = true,
}: RankingCardProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const abcCurveMap = useMemo(() => {
    if (!showAbcClassification) {
      return new Map();
    }

    return calculateAbcCurve(items.map((item) => ({ key: item.key, value: item.rawValue })));
  }, [items, showAbcClassification]);

  useEffect(() => {
    if (!items.length) {
      setSelectedKey(null);
    }
  }, [items]);

  const selectedItem = useMemo(() => {
    if (!items.length || !selectedKey) {
      return null;
    }

    return items.find((item) => item.key === selectedKey) ?? null;
  }, [items, selectedKey]);

  const hasSelection = Boolean(selectedItem);
  const selectedPercent = selectedItem?.percent ?? 100;
  const headlineLabel = selectedItem ? 'Selecionado' : 'Total analisado';
  const headlineValue = selectedItem?.value ?? totalValue;
  const captionTitle = selectedItem?.title ?? 'Base do periodo';
  const progressValue = Math.min(Math.max(selectedPercent, 0), 100);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="tv-panel-header">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription className="mt-2">{description}</CardDescription>
          </div>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-700 bg-slate-950/45 text-sky-300">
            <ChevronRight className="h-4 w-4" />
          </div>
        </div>
      </CardHeader>
      <CardContent onClick={() => setSelectedKey(null)} className="p-5">
        <div className="space-y-4">
          {isLoading ? (
            <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/30 px-4 py-8 text-center text-sm text-slate-400">
              {loadingMessage}
            </div>
          ) : items.length ? (
            <>
              <div className="space-y-2 rounded-md border border-slate-700/70 bg-slate-950/35 p-4">
                <div className="flex items-center justify-between gap-4 text-sm">
                  <span className="font-medium text-slate-400">{headlineLabel}</span>
                  <span className="truncate font-semibold text-slate-50">{headlineValue}</span>
                </div>
                <Progress value={progressValue} className="h-2 [&>div]:bg-sky-400" />
                <div className="flex items-center justify-between gap-4 text-xs text-slate-500">
                  <span className="truncate">{captionTitle}</span>
                  <span>
                    {selectedItem?.percent !== null
                      ? `${selectedPercent.toFixed(1)}% do periodo`
                      : 'Participacao nao informada'}
                  </span>
                </div>
              </div>

              <div className={cn('space-y-1', listClassName)}>
                {items.map((item, index) => {
                  const isSelected = item.key === selectedItem?.key;
                  const isMuted = hasSelection && !isSelected;
                  const abcData = showAbcClassification ? abcCurveMap.get(item.key) : null;
                  const abcBadgeClassName =
                    abcData?.abcClass === 'A'
                      ? 'border-emerald-500/40 bg-emerald-500/20 text-emerald-300'
                      : abcData?.abcClass === 'B'
                        ? 'border-amber-500/40 bg-amber-500/20 text-amber-300'
                        : 'border-sky-500/40 bg-sky-500/20 text-sky-300';

                  return (
                    <button
                      type="button"
                      key={item.key}
                      onClick={(event) => {
                        event.stopPropagation();
                        setSelectedKey(item.key);
                      }}
                      className={cn(
                        'grid w-full grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-3 text-left transition-colors duration-200 hover:bg-slate-800/50',
                        isSelected && 'bg-slate-800/70',
                        isMuted && 'opacity-50',
                      )}
                    >
                      <span className="font-mono text-sm font-semibold text-sky-300">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      <span className="min-w-0">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="truncate font-semibold text-slate-100">{item.title}</span>
                          {abcData && (
                            <Badge variant="outline" className={`h-5 px-1.5 py-0 text-[10px] ${abcBadgeClassName}`}>
                              Classe {abcData.abcClass}
                            </Badge>
                          )}
                          {item.badgeLabel && (
                            <Badge variant="outline" className={`h-5 px-1.5 py-0 text-[10px] ${item.badgeClassName ?? ''}`}>
                              {item.badgeLabel}
                            </Badge>
                          )}
                        </span>
                        <span className="mt-1 block truncate text-sm text-slate-400">
                          {item.subtitle}
                          {abcData && ` - Acumulado ${abcData.cumulativePercent.toFixed(1)}%`}
                        </span>
                      </span>
                      <span className="text-right text-sm font-semibold text-slate-50">{item.value}</span>
                    </button>
                  );
                })}
              </div>

              {showAbcReport && (
                <AbcAnalysisReport
                  title="Relatorio ABC"
                  description="Distribuicao dos itens por relevancia no periodo"
                  items={items.map((item) => ({
                    key: item.key,
                    label: item.title,
                    value: item.rawValue,
                    formattedValue: item.value,
                  }))}
                />
              )}
            </>
          ) : (
            <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/30 px-4 py-8 text-center text-sm text-slate-400">
              {emptyMessage}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
