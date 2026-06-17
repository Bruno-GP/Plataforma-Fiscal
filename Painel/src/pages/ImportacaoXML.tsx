import { FileUp } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ImportacaoXmlActions } from '@/features/importacaoXML/components/ImportacaoXmlActions';
import { ImportacaoXmlFileSelection } from '@/features/importacaoXML/components/ImportacaoXmlFileSelection';
import { ImportacaoXmlOperationFeedback } from '@/features/importacaoXML/components/ImportacaoXmlOperationFeedback';
import { ImportacaoXmlPendingNotice } from '@/features/importacaoXML/components/ImportacaoXmlPendingNotice';
import { ImportacaoXmlResultsPanel } from '@/features/importacaoXML/components/ImportacaoXmlResultsPanel';
import { useImportacaoXmlPageData } from '@/features/importacaoXML/hooks/useImportacaoXmlPageData';

export default function ImportacaoXML() {
  const {
    addFiles,
    cancelOperation,
    clearList,
    currentJob,
    formatFileSize,
    hasOperationFeedback,
    importedCount,
    isImporting,
    isProcessing,
    maxFiles,
    operationProgress,
    operationStage,
    pendingXmlCount,
    progressLabel,
    results,
    selectedFiles,
    startImport,
    totalSize,
  } = useImportacaoXmlPageData();

  return (
    <div className="space-y-6 py-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Importação de XML</h1>
        <p className="text-muted-foreground">
          Selecione os XMLs da NFe/NFCe/NFSe e inicie a operação. A tela importa os arquivos e já dispara o
          processamento automaticamente em sequência.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileUp className="h-5 w-5" />
            Enviar arquivos XML
          </CardTitle>
          <CardDescription>
            Clique no botão central para adicionar os XMLs, acompanhe o progresso e, ao final da importação, o
            processamento continua automaticamente.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <ImportacaoXmlFileSelection
            addFiles={addFiles}
            formatFileSize={formatFileSize}
            isDisabled={isImporting || isProcessing}
            maxFiles={maxFiles}
            selectedFiles={selectedFiles}
            totalSize={totalSize}
          />

          <ImportacaoXmlActions
            isImporting={isImporting}
            isProcessing={isProcessing}
            onCancel={cancelOperation}
            onClear={clearList}
            onStart={startImport}
            selectedCount={selectedFiles.length}
          />

          {hasOperationFeedback && (
            <ImportacaoXmlOperationFeedback
              currentJob={currentJob}
              progress={operationProgress}
              progressLabel={progressLabel}
              stage={operationStage}
            />
          )}

          <ImportacaoXmlPendingNotice pendingCount={pendingXmlCount} />

          <ImportacaoXmlResultsPanel importedCount={importedCount} results={results} />
        </CardContent>
      </Card>
    </div>
  );
}
