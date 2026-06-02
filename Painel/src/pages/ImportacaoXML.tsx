import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { FileUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { useImportFileQueue } from '@/hooks/useImportFileQueue';
import { useProcessingJobFlow } from '@/hooks/useProcessingJobFlow';
import { ImportacaoXmlActions } from '@/pages/components/ImportacaoXmlActions';
import { ImportacaoXmlFileSelection } from '@/pages/components/ImportacaoXmlFileSelection';
import { ImportacaoXmlOperationFeedback } from '@/pages/components/ImportacaoXmlOperationFeedback';
import { ImportacaoXmlPendingNotice } from '@/pages/components/ImportacaoXmlPendingNotice';
import { ImportacaoXmlResultsPanel } from '@/pages/components/ImportacaoXmlResultsPanel';
import type { ProcessingJobResponse } from '@/services/jobs';
import { saveFiscalOperation } from '@/services/operations';
import {
  consultarPendenciasXmlImportados,
  importarXmlArquivos,
  listarCnpjsXmlImportados,
  processarXmlsImportados,
  type ImportacaoXmlArquivoResultado,
  type ImportacaoXmlPendenciasResponse,
} from '@/services/nfe';
import { invalidateFiscalProcessingCache } from '@/utils/fiscalCache';
import {
  buildXmlImportProgressLabel,
  chunkItems,
  getImportProgress,
  getProcessingProgressRange,
  XML_IMPORT_PROGRESS_MAX,
  XML_PROCESS_PROGRESS_END,
  XML_PROCESS_PROGRESS_START,
  type XmlImportOperationStage,
} from '@/utils/xmlImportProgress';

type OperationStage = XmlImportOperationStage;

const MAX_XML_FILES = 10000;
const XML_IMPORT_BATCH_SIZE = 200;

export default function ImportacaoXML() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();

  const {
    selectedFiles,
    addFiles,
    clearFiles,
    totalSize,
    formatFileSize,
  } = useImportFileQueue({
    maxFiles: MAX_XML_FILES,
    acceptedExtensions: ['.xml'],
    onLimitExceeded: () => {
      toast({
        title: 'Limite atingido',
        description: 'Você pode importar no maximo 10000 XMLs por vez.',
        variant: 'destructive',
      });
    },
  });
  const [isImporting, setIsImporting] = useState(false);
  const [importedCount, setImportedCount] = useState(0);
  const [results, setResults] = useState<ImportacaoXmlArquivoResultado[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendenciasXml, setPendenciasXml] = useState<ImportacaoXmlPendenciasResponse | null>(null);
  const [operationStage, setOperationStage] = useState<OperationStage>('idle');
  const [operationProgress, setOperationProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const {
    currentJob,
    jobMessage: currentJobMessage,
    setJobMessage: setCurrentJobMessage,
    resetJobState,
    trackCreatedJob,
  } = useProcessingJobFlow();

  const operationAbortRef = useRef<AbortController | null>(null);
  const elapsedIntervalRef = useRef<number | null>(null);
  const processingAnimationRef = useRef<number | null>(null);

  const progressLabel = useMemo(
    () => buildXmlImportProgressLabel({
      stage: operationStage,
      progress: operationProgress,
      elapsedSeconds,
      jobMessage: currentJobMessage,
    }),
    [currentJobMessage, elapsedSeconds, operationProgress, operationStage],
  );

  const pendingXmlCount = pendenciasXml?.total_pendentes ?? 0;

  const carregarPendenciasXml = useCallback(async () => {
    if (!user?.emitente_cnpj) {
      setPendenciasXml(null);
      return;
    }

    try {
      const response = await consultarPendenciasXmlImportados(user.emitente_cnpj);
      setPendenciasXml(response);
    } catch {
      setPendenciasXml(null);
    }
  }, [user?.emitente_cnpj]);

  useEffect(() => {
    void carregarPendenciasXml();
  }, [carregarPendenciasXml]);

  useEffect(() => {
    if (!isImporting && !isProcessing) {
      if (elapsedIntervalRef.current !== null) {
        window.clearInterval(elapsedIntervalRef.current);
        elapsedIntervalRef.current = null;
      }
      return;
    }

    if (elapsedIntervalRef.current !== null) {
      return;
    }

    elapsedIntervalRef.current = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);

    return () => {
      if (elapsedIntervalRef.current !== null) {
        window.clearInterval(elapsedIntervalRef.current);
        elapsedIntervalRef.current = null;
      }
    };
  }, [isImporting, isProcessing]);

  useEffect(() => {
    return () => {
      operationAbortRef.current?.abort();

      if (elapsedIntervalRef.current !== null) {
        window.clearInterval(elapsedIntervalRef.current);
      }

      if (processingAnimationRef.current !== null) {
        window.clearInterval(processingAnimationRef.current);
      }
    };
  }, []);

  const clearList = () => {
    clearFiles();
    setImportedCount(0);
    setResults([]);
    setOperationStage('idle');
    setOperationProgress(0);
    setElapsedSeconds(0);
    resetJobState();
  };

  const stopProcessingAnimation = () => {
    if (processingAnimationRef.current !== null) {
      window.clearInterval(processingAnimationRef.current);
      processingAnimationRef.current = null;
    }
  };

  const startProcessingAnimation = (start: number, max: number) => {
    stopProcessingAnimation();
    processingAnimationRef.current = window.setInterval(() => {
      setOperationProgress((current) => {
        const next = Math.min(current + 1, max);
        return Math.max(next, start);
      });
    }, 900);
  };

  const cancelOperation = () => {
    operationAbortRef.current?.abort();
  };

  const processImportedXml = async (
    cnpjs: string[],
    abortController: AbortController,
  ) => {
    if (!cnpjs.length) {
      setOperationStage('completed');
      setOperationProgress(100);
      return;
    }

    setIsProcessing(true);
    setOperationStage('processing');
    setOperationProgress((current) => Math.max(current, XML_PROCESS_PROGRESS_START));

    try {
      let lastFinishedJob: ProcessingJobResponse | null = null;

      for (const [index, cnpj] of cnpjs.entries()) {
        const { rangeStart, rangeEnd } = getProcessingProgressRange(
          index,
          cnpjs.length,
          XML_PROCESS_PROGRESS_START,
          XML_PROCESS_PROGRESS_END,
        );

        setOperationProgress((current) => Math.max(current, Math.round(rangeStart)));
        startProcessingAnimation(Math.round(rangeStart), Math.max(Math.round(rangeEnd) - 3, Math.round(rangeStart)));

        const createdJob = await processarXmlsImportados(cnpj, { signal: abortController.signal });
        setCurrentJobMessage(createdJob.message);
        saveFiscalOperation({
          type: 'xml-process',
          status: 'queued',
          title: 'Processamento XML enviado para fila',
          description: createdJob.message,
          cnpj: user?.emitente_cnpj ?? cnpj,
          jobId: createdJob.job_id,
          jobStatus: createdJob.status,
          backendMessage: createdJob.message,
        });

        const finishedJob = await trackCreatedJob(createdJob, {
          signal: abortController.signal,
        });

        stopProcessingAnimation();
        setOperationProgress(Math.round(rangeEnd));
        lastFinishedJob = finishedJob;
      }

      setOperationStage('completed');
      setOperationProgress(100);

      toast({
        title: 'Processamento concluído',
        description: 'Itens, notas e KPIs foram registrados com sucesso.',
      });
      saveFiscalOperation({
        type: 'xml-process',
        status: 'success',
        title: 'Processamento XML concluido',
        description: `Processamento finalizado para ${cnpjs.length} CNPJ(s).`,
        cnpj: user?.emitente_cnpj ?? '',
        jobId: lastFinishedJob?.job_id,
        jobStatus: lastFinishedJob?.status,
        backendMessage: lastFinishedJob?.mensagem ?? undefined,
      });

      await invalidateFiscalProcessingCache(queryClient, 'nfe');

      await carregarPendenciasXml();
      navigate('/analise-vendas');
    } finally {
      stopProcessingAnimation();
      setIsProcessing(false);
    }
  };

  const startImport = async () => {
    if (!selectedFiles.length || isImporting || isProcessing) {
      return;
    }

    if (!user?.emitente_cnpj) {
      toast({
        title: 'Falha na importação',
        description: 'Não foi possível identificar o CNPJ da empresa logada.',
        variant: 'destructive',
      });
      return;
    }

    operationAbortRef.current?.abort();
    const abortController = new AbortController();
    operationAbortRef.current = abortController;

    setIsImporting(true);
    setIsProcessing(false);
    setImportedCount(0);
    setResults([]);
    setElapsedSeconds(0);
    setOperationProgress(0);
    setOperationStage('importing');
    resetJobState();

    const importResults: ImportacaoXmlArquivoResultado[] = [];
    const batches = chunkItems(selectedFiles, XML_IMPORT_BATCH_SIZE);

    try {
      for (const batch of batches) {
        const response = await importarXmlArquivos(
          batch.map((item) => item.file),
          user.emitente_cnpj,
          { signal: abortController.signal },
        );

        importResults.push(...response.resultados);
        setResults([...importResults]);
        setImportedCount((count) => count + batch.length);

        const importedFiles = Math.min(importedCount + batch.length, selectedFiles.length);
        const importProgress = getImportProgress(importedFiles, selectedFiles.length, XML_IMPORT_PROGRESS_MAX);
        setOperationProgress(importProgress);
      }

      const duplicados = importResults.filter((item) => item.status === 'duplicado').length;
      const erros = importResults.filter((item) => item.status === 'erro').length;

      toast({
        title: 'Importação concluída',
        description: `Importação finalizada com sucesso. Duplicados: ${duplicados}. Erros: ${erros}.`,
      });
      saveFiscalOperation({
        type: 'xml-import',
        status: erros > 0 || duplicados > 0 ? 'warning' : 'success',
        title: 'Importacao XML concluida',
        description: `Importados: ${importResults.filter((item) => item.status === 'importado').length}. Duplicados: ${duplicados}. Erros: ${erros}.`,
        cnpj: user.emitente_cnpj,
      });

      clearFiles();
      await carregarPendenciasXml();

      const cnpjsParaProcessar = listarCnpjsXmlImportados(importResults);

      if (!cnpjsParaProcessar.length) {
        setOperationStage('completed');
        setOperationProgress(100);
        toast({
          title: 'ImportaÃ§Ã£o concluÃ­da',
          description: 'Nenhum XML novo importado para processamento.',
        });
        return;
      }

      await processImportedXml(cnpjsParaProcessar, abortController);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        stopProcessingAnimation();
        setOperationStage('cancelled');
        toast({
          title: 'Operação cancelada',
          description: 'O acompanhamento foi interrompido nesta tela. Um job ja criado pode continuar no backend.',
        });
        saveFiscalOperation({
          type: isProcessing ? 'xml-process' : 'xml-import',
          status: 'cancelled',
          title: 'Operacao XML cancelada',
          description: 'O acompanhamento foi interrompido nesta tela. Um job ja criado pode continuar no backend.',
          cnpj: user?.emitente_cnpj ?? '',
          jobId: currentJob?.job_id,
          jobStatus: currentJob?.status,
          backendMessage: currentJob?.mensagem ?? undefined,
        });
        return;
      }

      setOperationStage('error');
      saveFiscalOperation({
        type: isProcessing ? 'xml-process' : 'xml-import',
        status: 'error',
        title: 'Falha no fluxo XML',
        description: error instanceof Error ? error.message : 'Nao foi possivel importar e processar os XMLs.',
        cnpj: user?.emitente_cnpj ?? '',
      });
      toast({
        title: 'Falha na importação',
        description:
          error instanceof Error ? error.message : 'Não foi possível importar e processar os XMLs.',
        variant: 'destructive',
      });
    } finally {
      if (operationAbortRef.current === abortController) {
        operationAbortRef.current = null;
      }

      setIsImporting(false);
      setIsProcessing(false);
      stopProcessingAnimation();
    }
  };

  const hasOperationFeedback =
    isImporting ||
    isProcessing ||
    operationStage === 'completed' ||
    operationStage === 'cancelled' ||
    operationStage === 'error';

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
            maxFiles={MAX_XML_FILES}
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
