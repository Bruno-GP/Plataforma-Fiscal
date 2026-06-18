import { Progress } from '@/components/ui/progress';

import { getXmlImportOperationTitle } from '../helpers/importacaoXmlView';
import type { ImportacaoXmlOperationFeedbackProps } from '../types';

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
