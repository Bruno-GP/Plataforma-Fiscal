import { Clock3 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import { formatInconsistenciasDateTime } from '../formatters/formatInconsistenciasDateTime';
import { jobStatusLabelMap, jobStatusVariantMap } from '../helpers/inconsistenciasDisplay';
import type { InconsistenciasJobsCardProps } from '../types';

export function InconsistenciasJobsCard({ isError, isLoading, jobs }: InconsistenciasJobsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock3 className="h-5 w-5" />
          Jobs de processamento
        </CardTitle>
        <CardDescription>Ultimos processamentos retornados pela API de jobs para o fluxo atual.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && (
          <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
            Carregando jobs recentes...
          </div>
        )}

        {isError && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            Nao foi possivel carregar os jobs recentes.
          </div>
        )}

        {!isLoading && !isError && jobs.length === 0 && (
          <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
            Nenhum job recente encontrado para este fluxo.
          </div>
        )}

        {jobs.map((job) => (
          <div key={job.job_id} className="rounded-lg border p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium">{job.tipo}</p>
                  <Badge variant={jobStatusVariantMap[job.status]}>{jobStatusLabelMap[job.status]}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{job.erro ?? job.mensagem ?? 'Sem mensagem do backend.'}</p>
                {job.total_itens > 0 && (
                  <p className="text-xs text-muted-foreground">Progresso: {job.itens_processados}/{job.total_itens}</p>
                )}
              </div>
              <div className="text-right text-xs text-muted-foreground">
                <div>{job.job_id}</div>
                <div>{formatInconsistenciasDateTime(job.criado_em)}</div>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
