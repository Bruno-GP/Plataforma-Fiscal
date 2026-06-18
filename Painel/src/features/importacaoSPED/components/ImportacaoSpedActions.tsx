import { Database, Upload } from 'lucide-react';

import { Button } from '@/components/ui/button';

import { getImportacaoSpedPrimaryActionLabel } from '../helpers/importacaoSpedView';
import type { ImportacaoSpedActionsProps } from '../types';

export function ImportacaoSpedActions({
  isImporting,
  isProcessing,
  onImport,
  onProcess,
  onStop,
  pendencias,
  selectedCount,
}: ImportacaoSpedActionsProps) {
  const isBusy = isImporting || isProcessing;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button onClick={onImport} disabled={!selectedCount || isBusy}>
        <Upload className="mr-2 h-4 w-4" />
        {getImportacaoSpedPrimaryActionLabel({ isImporting, isProcessing })}
      </Button>
      <Button onClick={onProcess} disabled={!pendencias?.possui_pendentes || isProcessing || isImporting}>
        <Database className="mr-2 h-4 w-4" />
        {isProcessing ? 'Processando...' : 'Processar SPED importado'}
      </Button>
      {isProcessing && (
        <Button variant="outline" onClick={onStop}>
          Parar acompanhamento
        </Button>
      )}
    </div>
  );
}
