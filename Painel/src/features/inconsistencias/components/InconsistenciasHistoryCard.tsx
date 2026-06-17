import { Clock3 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import { formatInconsistenciasDateTime } from '../formatters/formatInconsistenciasDateTime';
import { operationTypeLabel, statusLabelMap, statusVariantMap } from '../helpers/inconsistenciasDisplay';
import type { InconsistenciasHistoryCardProps } from '../types';

export function InconsistenciasHistoryCard({ entries }: InconsistenciasHistoryCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock3 className="h-5 w-5" />
          Ultimas execucoes
        </CardTitle>
        <CardDescription>Resumo das operacoes fiscais mais recentes salvas pelo painel.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.length === 0 && (
          <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
            Ainda nao existem eventos registrados nesta estacao para a empresa atual.
          </div>
        )}

        {entries.map((entry) => (
          <div key={entry.id} className="rounded-lg border p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium">{entry.title}</p>
                  <Badge variant={statusVariantMap[entry.status]}>{statusLabelMap[entry.status]}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{entry.description}</p>
                {entry.jobId && (
                  <p className="text-xs text-muted-foreground">
                    Job {entry.jobId}
                    {entry.jobStatus ? ` - ${entry.jobStatus}` : ''}
                  </p>
                )}
              </div>
              <div className="text-right text-xs text-muted-foreground">
                <div>{operationTypeLabel[entry.type]}</div>
                <div>{formatInconsistenciasDateTime(entry.createdAt)}</div>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
