import type { ImportFileItem } from '@/hooks/useImportFileQueue';
import type { ProcessingJobResponse } from '@/services/jobs';
import type {
  ImportacaoXmlArquivoResultado,
  ImportacaoXmlPendenciasResponse,
} from '@/services/nfe';
import type { XmlImportOperationStage } from '@/utils/xmlImportProgress';

export type ImportacaoXmlSelectedFile = ImportFileItem;
export type ImportacaoXmlResult = ImportacaoXmlArquivoResultado;
export type ImportacaoXmlPendencias = ImportacaoXmlPendenciasResponse;
export type ImportacaoXmlJob = ProcessingJobResponse;
export type ImportacaoXmlStage = XmlImportOperationStage;

export interface ImportacaoXmlActionsProps {
  isImporting: boolean;
  isProcessing: boolean;
  onCancel: () => void;
  onClear: () => void;
  onStart: () => void;
  selectedCount: number;
}

export interface ImportacaoXmlFileSelectionProps {
  addFiles: (files: FileList | null) => void;
  formatFileSize: (size: number) => string;
  isDisabled: boolean;
  maxFiles: number;
  selectedFiles: ImportacaoXmlSelectedFile[];
  totalSize: number;
}

export interface ImportacaoXmlOperationFeedbackProps {
  currentJob: ImportacaoXmlJob | null;
  progress: number;
  progressLabel: string;
  stage: ImportacaoXmlStage;
}

export interface ImportacaoXmlPendingNoticeProps {
  pendingCount: number;
}

export interface ImportacaoXmlResultsPanelProps {
  importedCount: number;
  results: ImportacaoXmlResult[];
}

export interface ImportacaoXmlPageData {
  addFiles: (files: FileList | null) => void;
  cancelOperation: () => void;
  clearList: () => void;
  currentJob: ImportacaoXmlJob | null;
  formatFileSize: (size: number) => string;
  hasOperationFeedback: boolean;
  importedCount: number;
  isImporting: boolean;
  isProcessing: boolean;
  maxFiles: number;
  operationProgress: number;
  operationStage: ImportacaoXmlStage;
  pendenciasXml: ImportacaoXmlPendencias | null;
  pendingXmlCount: number;
  progressLabel: string;
  results: ImportacaoXmlResult[];
  selectedFiles: ImportacaoXmlSelectedFile[];
  startImport: () => Promise<void>;
  totalSize: number;
}
