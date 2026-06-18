import type { ImportacaoXmlResult, ImportacaoXmlStage } from '../types';

export const getXmlImportPrimaryActionLabel = ({
  isImporting,
  isProcessing,
}: {
  isImporting: boolean;
  isProcessing: boolean;
}) => {
  if (isImporting) {
    return 'Importando...';
  }

  if (isProcessing) {
    return 'Processando...';
  }

  return 'Importar e processar';
};

export const getXmlFileSelectionSummary = ({
  maxFiles,
  selectedCount,
  totalSizeLabel,
}: {
  maxFiles: number;
  selectedCount: number;
  totalSizeLabel: string;
}) => `${selectedCount}/${maxFiles} arquivo(s) • ${totalSizeLabel}`;

export const getXmlImportOperationTitle = (stage: ImportacaoXmlStage) => {
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

export const getXmlPendingNoticeMessage = (pendingCount: number) =>
  `Ainda faltam XMLs a serem processados (${pendingCount}). Uma nova operação volta a processar os pendentes automaticamente.`;

export const getXmlImportResultSummary = (
  results: ImportacaoXmlResult[],
  importedCount: number,
) => ({
  evaluated: Math.max(importedCount, results.length),
  imported: results.filter((item) => item.status === 'importado').length,
  duplicated: results.filter((item) => item.status === 'duplicado').length,
  errors: results.filter((item) => item.status === 'erro').length,
});
