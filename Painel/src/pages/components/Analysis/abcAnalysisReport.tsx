import { useMemo } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { calculateAbcCurveList } from '@/services/analysisABC';

interface AbcAnalysisReportItem {
  key: string;
  label: string;
  value: number;
  formattedValue?: string;
}

interface AbcAnalysisReportProps {
  title?: string;
  description?: string;
  items: AbcAnalysisReportItem[];
  emptyMessage?: string;
}

const getAbcBadgeClassName = (abcClass: 'A' | 'B' | 'C') => {
  if (abcClass === 'A') {
    return 'border-emerald-500/40 bg-emerald-500/20 text-emerald-300';
  }

  if (abcClass === 'B') {
    return 'border-amber-500/40 bg-amber-500/20 text-amber-300';
  }

  return 'border-sky-500/40 bg-sky-500/20 text-sky-300';
};

export function AbcAnalysisReport({
  title = 'Relatório da Curva ABC',
  description = 'Classificação dos itens por participação acumulada',
  items,
  emptyMessage = 'Sem dados suficientes para gerar a curva ABC.',
}: AbcAnalysisReportProps) {
  const abcRows = useMemo(
    () => calculateAbcCurveList(items.map((item) => ({ key: item.key, value: item.value }))),
    [items],
  );

  const itemMap = useMemo(() => new Map(items.map((item) => [item.key, item])), [items]);

  const classSummary = useMemo(() => {
    return abcRows.reduce(
      (acc, row) => {
        acc[row.abcClass] += 1;
        return acc;
      },
      { A: 0, B: 0, C: 0 },
    );
  }, [abcRows]);

  return (
    <Card className="rounded-2xl border-slate-800/70 bg-slate-950/40">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {abcRows.length ? (
          <>
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge variant="outline" className="border-emerald-500/40 bg-emerald-500/20 text-emerald-300">
                Classe A: {classSummary.A}
              </Badge>
              <Badge variant="outline" className="border-amber-500/40 bg-amber-500/20 text-amber-300">
                Classe B: {classSummary.B}
              </Badge>
              <Badge variant="outline" className="border-sky-500/40 bg-sky-500/20 text-sky-300">
                Classe C: {classSummary.C}
              </Badge>
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead>Classe</TableHead>
                  <TableHead className="text-right">Participação</TableHead>
                  <TableHead className="text-right">Acumulado</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {abcRows.map((row) => {
                  const originalItem = itemMap.get(row.key);

                  return (
                    <TableRow key={row.key}>
                      <TableCell className="font-medium">{originalItem?.label ?? row.key}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={getAbcBadgeClassName(row.abcClass)}>
                          {row.abcClass}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">{row.participationPercent.toFixed(1)}%</TableCell>
                      <TableCell className="text-right">{row.cumulativePercent.toFixed(1)}%</TableCell>
                      <TableCell className="text-right">{originalItem?.formattedValue ?? row.value.toFixed(2)}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        )}
      </CardContent>
    </Card>
  );
}