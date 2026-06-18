import { Progress } from '@/components/ui/progress';

import type { ImportacaoSpedProgressPanelProps } from '../types';

export function ImportacaoSpedProgressPanel({
  currentJob,
  importedCount,
  isImporting,
  isProcessing,
  jobMessage,
  progress,
}: ImportacaoSpedProgressPanelProps) {
  if (!isImporting && importedCount <= 0 && !isProcessing) {
    return null;
  }

  return (
    <div className="space-y-2">
      <Progress value={progress} />

      {isProcessing && (
        <div className="space-y-2 rounded-lg border p-4 text-sm">
          <p className="font-medium">Processamento em fila ou execucao</p>
          <p className="text-muted-foreground">{jobMessage ?? 'Aguardando retorno do backend.'}</p>
          {currentJob && (
            <div className="text-xs text-muted-foreground">
              Job {currentJob.job_id} - {currentJob.status}
              {currentJob.total_itens > 0 ? ` - ${currentJob.itens_processados}/${currentJob.total_itens} item(ns)` : ''}
            </div>
          )}
        </div>
      )}

      {currentJob?.status === 'SUCCESS' && (
        <div className="space-y-2 rounded-lg border p-4 text-sm">
          <p>
            <strong>Job:</strong> {currentJob.job_id}
          </p>
          <p>
            <strong>Status:</strong> {currentJob.status}
          </p>
          {currentJob.total_itens > 0 && (
            <p>
              <strong>Itens processados:</strong> {currentJob.itens_processados}/{currentJob.total_itens}
            </p>
          )}
          {currentJob.mensagem && (
            <p>
              <strong>Mensagem:</strong> {currentJob.mensagem}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
