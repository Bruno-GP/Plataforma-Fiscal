import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, FileWarning, RefreshCcw } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/contexts/AuthContext';
import { consultarPendenciasXmlImportados } from '@/services/nfe';
import { consultarPendenciasSped } from '@/services/sped';
import { fetchJobs, type JobStatus, type ProcessingJobResponse } from '@/services/jobs';
import { readFiscalOperations, type FiscalOperationEntry } from '@/services/operations';

const operationTypeLabel: Record<FiscalOperationEntry['type'], string> = {
  'xml-import': 'Importacao XML',
  'xml-process': 'Processamento XML',
  'sped-import': 'Importacao SPED',
  'sped-process': 'Processamento SPED',
};

const statusVariantMap: Record<FiscalOperationEntry['status'], 'default' | 'secondary' | 'destructive' | 'outline'> = {
  success: 'default',
  warning: 'secondary',
  error: 'destructive',
  cancelled: 'outline',
  queued: 'secondary',
  running: 'secondary',
};

const statusLabelMap: Record<FiscalOperationEntry['status'], string> = {
  success: 'Sucesso',
  warning: 'Atencao',
  error: 'Erro',
  cancelled: 'Cancelada',
  queued: 'Em fila',
  running: 'Em execucao',
};

const jobStatusVariantMap: Record<JobStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  PENDING: 'secondary',
  QUEUED: 'secondary',
  RUNNING: 'secondary',
  SUCCESS: 'default',
  FAILED: 'destructive',
  CANCELED: 'outline',
};

const jobStatusLabelMap: Record<JobStatus, string> = {
  PENDING: 'Pendente',
  QUEUED: 'Em fila',
  RUNNING: 'Em execucao',
  SUCCESS: 'Concluido',
  FAILED: 'Falhou',
  CANCELED: 'Cancelado',
};

const isActiveJob = (job: ProcessingJobResponse) =>
  job.status === 'PENDING' || job.status === 'QUEUED' || job.status === 'RUNNING';

const isFailedJob = (job: ProcessingJobResponse) => job.status === 'FAILED';

const formatDateTime = (value: string) =>
  new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));

export default function Inconsistencias() {
  const { user } = useAuth();
  const emitenteCnpj = user?.emitente_cnpj;
  const usaSped = Boolean(user?.tem_sped);

  const pendenciasQuery = useQuery({
    queryKey: ['inconsistencias-pendencias', emitenteCnpj, usaSped],
    queryFn: async () => {
      if (!emitenteCnpj) {
        return { total_pendentes: 0, possui_pendentes: false };
      }

      return usaSped
        ? consultarPendenciasSped(emitenteCnpj)
        : consultarPendenciasXmlImportados(emitenteCnpj);
    },
    enabled: Boolean(emitenteCnpj),
    staleTime: 60_000,
  });

  const jobsQuery = useQuery({
    queryKey: ['inconsistencias-jobs', usaSped],
    queryFn: () =>
      fetchJobs({
        tipo: usaSped ? 'SPED_PROCESSAMENTO_IMPORTADOS' : 'NFE_PROCESSAMENTO_IMPORTADOS',
        limit: 10,
      }),
    staleTime: 30_000,
  });

  const operationHistory = useMemo(
    () => readFiscalOperations().filter((entry) => entry.cnpj === emitenteCnpj),
    [emitenteCnpj],
  );

  const latestError = operationHistory.find((entry) => entry.status === 'error');
  const latestWarning = operationHistory.find((entry) => entry.status === 'warning');
  const recentJobs = jobsQuery.data?.resultados ?? [];
  const activeJobs = recentJobs.filter(isActiveJob);
  const failedJobs = recentJobs.filter(isFailedJob);
  const hasPendencias = (pendenciasQuery.data?.total_pendentes ?? 0) > 0;
  const hasActiveJobs = activeJobs.length > 0;
  const hasFailedJobs = failedJobs.length > 0;

  const actionLink = usaSped ? '/importacao-sped' : '/importacao-xml';
  const actionLabel = usaSped ? 'Abrir fluxo SPED' : 'Abrir fluxo XML';

  return (
    <section className="space-y-6 py-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Central de inconsistencias</h1>
          <p className="text-muted-foreground">
            Acompanhe pendencias fiscais, falhas recentes e atalhos para retomar a operacao.
          </p>
        </div>

        <Button variant="outline" onClick={() => pendenciasQuery.refetch()} disabled={pendenciasQuery.isFetching}>
          <RefreshCcw className="mr-2 h-4 w-4" />
          Atualizar
        </Button>
      </div>

      {!hasPendencias && !hasActiveJobs && !hasFailedJobs && !latestError && !latestWarning && (
        <Alert className="border-emerald-200 bg-emerald-50 text-emerald-900 [&>svg]:text-emerald-700">
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>Operacao sem inconsistencias abertas</AlertTitle>
          <AlertDescription>
            Nao encontramos pendencias fiscais abertas nem falhas recentes registradas para esta empresa.
          </AlertDescription>
        </Alert>
      )}

      {(hasPendencias || hasActiveJobs || hasFailedJobs || latestError || latestWarning) && (
        <Alert variant={hasFailedJobs || latestError ? 'destructive' : 'default'}>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Existem pontos que pedem atencao</AlertTitle>
          <AlertDescription>
            {hasActiveJobs
              ? `Ha ${activeJobs.length} processamento(s) em fila ou execucao. Pendencias podem permanecer ate a conclusao.`
              : hasPendencias
              ? `Ha ${pendenciasQuery.data?.total_pendentes ?? 0} arquivo(s) aguardando processamento.`
              : hasFailedJobs || latestError
                ? 'Encontramos uma falha recente na operacao fiscal.'
                : 'Ha um evento recente que merece revisao.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileWarning className="h-5 w-5" />
              Pendencias ativas
            </CardTitle>
            <CardDescription>Status operacional atual da empresa logada.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">Arquivos aguardando processamento</p>
                  <p className="text-3xl font-semibold">{pendenciasQuery.data?.total_pendentes ?? 0}</p>
                </div>
                <Badge variant={hasPendencias ? 'secondary' : 'default'}>
                  {hasPendencias ? 'Atencao' : 'Em dia'}
                </Badge>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                {usaSped
                  ? 'Arquivos TXT importados e ainda nao processados no fluxo SPED.'
                  : 'XMLs importados e ainda nao consolidados nos indicadores fiscais.'}
              </p>
            </div>

            <Button asChild className="w-full justify-between">
              <Link to={actionLink}>
                {actionLabel}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock3 className="h-5 w-5" />
              Jobs de processamento
            </CardTitle>
            <CardDescription>
              Ultimos processamentos retornados pela API de jobs para o fluxo atual.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {jobsQuery.isLoading && (
              <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                Carregando jobs recentes...
              </div>
            )}

            {jobsQuery.isError && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                Nao foi possivel carregar os jobs recentes.
              </div>
            )}

            {!jobsQuery.isLoading && !jobsQuery.isError && recentJobs.length === 0 && (
              <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                Nenhum job recente encontrado para este fluxo.
              </div>
            )}

            {recentJobs.map((job) => (
              <div key={job.job_id} className="rounded-lg border p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{job.tipo}</p>
                      <Badge variant={jobStatusVariantMap[job.status]}>{jobStatusLabelMap[job.status]}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {job.erro ?? job.mensagem ?? 'Sem mensagem do backend.'}
                    </p>
                    {job.total_itens > 0 && (
                      <p className="text-xs text-muted-foreground">
                        Progresso: {job.itens_processados}/{job.total_itens}
                      </p>
                    )}
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div>{job.job_id}</div>
                    <div>{formatDateTime(job.criado_em)}</div>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock3 className="h-5 w-5" />
              Ultimas execucoes
            </CardTitle>
            <CardDescription>Resumo das operacoes fiscais mais recentes salvas pelo painel.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {operationHistory.length === 0 && (
              <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                Ainda nao existem eventos registrados nesta estacao para a empresa atual.
              </div>
            )}

            {operationHistory.map((entry) => (
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
                    <div>{formatDateTime(entry.createdAt)}</div>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
