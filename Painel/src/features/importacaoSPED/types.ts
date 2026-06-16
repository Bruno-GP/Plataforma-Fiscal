import type { ImportFileItem } from '@/hooks/useImportFileQueue';
import type { ProcessingJobResponse } from '@/services/jobs';
import type {
  ImportacaoSpedArquivoResultado,
  ImportacaoSpedPendenciasResponse,
} from '@/services/sped';

export type ImportacaoSpedSelectedFile = ImportFileItem;
export type ImportacaoSpedResult = ImportacaoSpedArquivoResultado;
export type ImportacaoSpedPendencias = ImportacaoSpedPendenciasResponse;
export type ImportacaoSpedJob = ProcessingJobResponse;

export interface ImportacaoSpedHeaderProps {
  title: string;
  description: string;
}

export interface ImportacaoSpedFileSelectionProps {
  addFiles: (files: FileList | null) => void;
  formatFileSize: (size: number) => string;
  isDisabled: boolean;
  maxFiles: number;
  selectedFiles: ImportacaoSpedSelectedFile[];
  totalSize: number;
}

export interface ImportacaoSpedActionsProps {
  isImporting: boolean;
  isProcessing: boolean;
  onImport: () => void;
  onProcess: () => void;
  onStop: () => void;
  pendencias: ImportacaoSpedPendencias | null;
  selectedCount: number;
}

export interface ImportacaoSpedProgressPanelProps {
  currentJob: ImportacaoSpedJob | null;
  importedCount: number;
  isImporting: boolean;
  isProcessing: boolean;
  jobMessage: string | null;
  progress: number;
}

export interface ImportacaoSpedResultsPanelProps {
  results: ImportacaoSpedResult[];
}
