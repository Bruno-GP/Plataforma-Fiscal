import { Loader2, Upload, X } from 'lucide-react';

import { Button } from '@/components/ui/button';

import { getXmlImportPrimaryActionLabel } from '../helpers/importacaoXmlView';
import type { ImportacaoXmlActionsProps } from '../types';

export function ImportacaoXmlActions({
  isImporting,
  isProcessing,
  onCancel,
  onClear,
  onStart,
  selectedCount,
}: ImportacaoXmlActionsProps) {
  const isBusy = isImporting || isProcessing;
  const hasSelectedFiles = selectedCount > 0;

  return (
    <div className="flex flex-wrap items-center justify-end gap-3">
      <Button variant="outline" onClick={onClear} disabled={!hasSelectedFiles || isBusy}>
        <X className="mr-2 h-4 w-4" />
        Limpar lista
      </Button>

      <Button onClick={onStart} disabled={!hasSelectedFiles || isBusy}>
        {isBusy ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Upload className="mr-2 h-4 w-4" />
        )}
        {getXmlImportPrimaryActionLabel({ isImporting, isProcessing })}
      </Button>

      {isBusy && (
        <Button variant="destructive" onClick={onCancel}>
          <X className="mr-2 h-4 w-4" />
          Parar acompanhamento
        </Button>
      )}
    </div>
  );
}
