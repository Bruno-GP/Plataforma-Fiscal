import { Progress } from '@/components/ui/progress';
import type { ProcessingJobResponse } from '@/services/jobs';
import type { XmlImportOperationStage } from '@/utils/xmlImportProgress';

export const getXmlImportOperationTitle = (stage: XmlImportOperationStage) => {
  switch (stage) {
    case 'processing':
      return 'Processando';
    case 'completed':
      return 'Processamento terminado';
    case 'cancelled':
      return 'Operação cancelada';
    case 'error':
      return 'Falha no processamento';
    default:
      return 'Início do processamento';
  }
};

interface ImportacaoXmlOperationFeedbackProps {
  currentJob: ProcessingJobResponse | null;
  progress: number;
  progressLabel: string;
  stage: XmlImportOperationStage;
}

export function ImportacaoXmlOperationFeedback({
  currentJob,
  progress,
  progressLabel,
  stage,
}: ImportacaoXmlOperationFeedbackProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <p className="font-medium text-foreground">{getXmlImportOperationTitle(stage)}</p>
        <span className="text-muted-foreground">{progressLabel}</span>
      </div>
      <Progress value={progress} />
      {currentJob && (
        <p className="text-xs text-muted-foreground">
          Job {currentJob.job_id} - {currentJob.status}
          {currentJob.total_itens > 0
            ? ` - ${currentJob.itens_processados}/${currentJob.total_itens} item(ns)`
            : ''}
        </p>
      )}
    </div>
  );
}
