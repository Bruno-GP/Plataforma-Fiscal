export const getImportacaoSpedPrimaryActionLabel = ({
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

  return 'Importar para banco';
};

export const getImportacaoSpedFileSelectionSummary = ({
  maxFiles,
  selectedCount,
  totalSizeLabel,
}: {
  maxFiles: number;
  selectedCount: number;
  totalSizeLabel: string;
}) => `${selectedCount}/${maxFiles} arquivo(s) â€¢ ${totalSizeLabel}`;
