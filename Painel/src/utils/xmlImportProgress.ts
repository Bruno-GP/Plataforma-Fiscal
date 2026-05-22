export type XmlImportOperationStage = 'idle' | 'importing' | 'processing' | 'completed' | 'cancelled' | 'error';

export const XML_IMPORT_PROGRESS_MAX = 55;
export const XML_PROCESS_PROGRESS_START = 55;
export const XML_PROCESS_PROGRESS_END = 100;

export const formatElapsedTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
};

export const chunkItems = <T>(items: T[], size: number): T[][] => {
  const chunks: T[][] = [];

  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }

  return chunks;
};

export const getProcessingProgressRange = (
  index: number,
  totalItems: number,
  start = XML_PROCESS_PROGRESS_START,
  end = XML_PROCESS_PROGRESS_END,
) => {
  if (totalItems <= 0) {
    return { rangeStart: end, rangeEnd: end };
  }

  return {
    rangeStart: start + (index / totalItems) * (end - start),
    rangeEnd: start + ((index + 1) / totalItems) * (end - start),
  };
};

export const getImportProgress = (
  importedItems: number,
  totalItems: number,
  maxProgress = XML_IMPORT_PROGRESS_MAX,
) => {
  if (totalItems <= 0) {
    return 0;
  }

  return Math.round((importedItems / totalItems) * maxProgress);
};

export const buildXmlImportProgressLabel = ({
  stage,
  progress,
  elapsedSeconds,
  jobMessage,
}: {
  stage: XmlImportOperationStage;
  progress: number;
  elapsedSeconds: number;
  jobMessage?: string | null;
}) => {
  const progressText = `${Math.round(progress)}% - ${formatElapsedTime(elapsedSeconds)}`;

  switch (stage) {
    case 'importing':
      return `Importando XMLs - ${progressText}`;
    case 'processing':
      return `${jobMessage ?? 'Processamento em fila'} - ${progressText}`;
    case 'completed':
      return `Processamento terminado - 100% - ${formatElapsedTime(elapsedSeconds)}`;
    case 'cancelled':
      return `Operação cancelada - ${progressText}`;
    case 'error':
      return `Falha no processamento - ${progressText}`;
    default:
      return `0% - ${formatElapsedTime(elapsedSeconds)}`;
  }
};
