import { useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { FileText, FileUp, Loader2, Upload, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import {
  consultarPendenciasXmlImportados,
  importarXmlArquivos,
  processarXmlsImportados,
  type ImportacaoXmlArquivoResultado,
  type ImportacaoXmlPendenciasResponse,
} from '@/services/nfe';

interface XmlFileItem {
  id: string;
  file: File;
}

type OperationStage = 'idle' | 'importing' | 'processing' | 'completed' | 'cancelled' | 'error';

const MAX_XML_FILES = 10000;
const XML_IMPORT_BATCH_SIZE = 200;
const IMPORT_PROGRESS_MAX = 55;
const PROCESS_PROGRESS_START = 55;
const PROCESS_PROGRESS_END = 100;

const formatFileSize = (size: number): string => {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  }

  if (size >= 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${size} B`;
};

const formatElapsedTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
};

const chunkFiles = (files: XmlFileItem[], size: number): XmlFileItem[][] => {
  const chunks: XmlFileItem[][] = [];

  for (let index = 0; index < files.length; index += size) {
    chunks.push(files.slice(index, index + size));
  }

  return chunks;
};

export default function ImportacaoXML() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();

  const [selectedFiles, setSelectedFiles] = useState<XmlFileItem[]>([]);
  const [isImporting, setIsImporting] = useState(false);
  const [importedCount, setImportedCount] = useState(0);
  const [results, setResults] = useState<ImportacaoXmlArquivoResultado[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendenciasXml, setPendenciasXml] = useState<ImportacaoXmlPendenciasResponse | null>(null);
  const [isLoadingPendencias, setIsLoadingPendencias] = useState(false);
  const [operationStage, setOperationStage] = useState<OperationStage>('idle');
  const [operationProgress, setOperationProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const operationAbortRef = useRef<AbortController | null>(null);
  const elapsedIntervalRef = useRef<number | null>(null);
  const processingAnimationRef = useRef<number | null>(null);

  const totalSize = useMemo(
    () => selectedFiles.reduce((acc, item) => acc + item.file.size, 0),
    [selectedFiles],
  );

  const progressLabel = useMemo(() => {
    const progressText = `${Math.round(operationProgress)}% - ${formatElapsedTime(elapsedSeconds)}`;

    switch (operationStage) {
      case 'importing':
        return `Importando XMLs - ${progressText}`;
      case 'processing':
        return `Processando - ${progressText}`;
      case 'completed':
        return `Processamento terminado - 100% - ${formatElapsedTime(elapsedSeconds)}`;
      case 'cancelled':
        return `Operação cancelada - ${progressText}`;
      case 'error':
        return `Falha no processamento - ${progressText}`;
      default:
        return `0% - ${formatElapsedTime(elapsedSeconds)}`;
    }
  }, [elapsedSeconds, operationProgress, operationStage]);

  const cnpjsImportados = useMemo(() => {
    const cnpjs = new Set(
      results
        .filter((item) => item.status === 'importado' && item.cnpj_emitente)
        .map((item) => item.cnpj_emitente as string),
    );

    return Array.from(cnpjs);
  }, [results]);

  const possuiPendenciasNaoProcessadas = (pendenciasXml?.total_pendentes ?? 0) > 0;

  const carregarPendenciasXml = async () => {
    if (!user?.emitente_cnpj) {
      setPendenciasXml(null);
      return;
    }

    setIsLoadingPendencias(true);

    try {
      const response = await consultarPendenciasXmlImportados(user.emitente_cnpj);
      setPendenciasXml(response);
    } catch {
      setPendenciasXml(null);
    } finally {
      setIsLoadingPendencias(false);
    }
  };

  useEffect(() => {
    void carregarPendenciasXml();
  }, [user?.emitente_cnpj]);

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

  const addFiles = (files: FileList | null) => {
    if (!files?.length) {
      return;
    }

    const xmlFiles = Array.from(files).filter((file) => file.name.toLowerCase().endsWith('.xml'));

    if (!xmlFiles.length) {
      return;
    }

    setSelectedFiles((prev) => {
      const existingNames = new Set(prev.map((item) => item.file.name));
      const availableSlots = MAX_XML_FILES - prev.length;

      const newItems = xmlFiles
        .filter((file) => !existingNames.has(file.name))
        .slice(0, Math.max(availableSlots, 0))
        .map((file) => ({
          id: `${file.name}-${file.lastModified}`,
          file,
        }));

      const nextFiles = [...prev, ...newItems];

      if (nextFiles.length >= MAX_XML_FILES && xmlFiles.length > newItems.length) {
        toast({
          title: 'Limite atingido',
          description: 'Você pode importar no máximo 10000 XMLs por vez.',
          variant: 'destructive',
        });
      }

      return nextFiles;
    });
  };

  const clearList = () => {
    setSelectedFiles([]);
    setImportedCount(0);
    setResults([]);
    setOperationStage('idle');
    setOperationProgress(0);
    setElapsedSeconds(0);
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
    setOperationProgress((current) => Math.max(current, PROCESS_PROGRESS_START));

    try {
      for (const [index, cnpj] of cnpjs.entries()) {
        const rangeStart =
          PROCESS_PROGRESS_START + (index / cnpjs.length) * (PROCESS_PROGRESS_END - PROCESS_PROGRESS_START);
        const rangeEnd =
          PROCESS_PROGRESS_START + ((index + 1) / cnpjs.length) * (PROCESS_PROGRESS_END - PROCESS_PROGRESS_START);

        setOperationProgress((current) => Math.max(current, Math.round(rangeStart)));
        startProcessingAnimation(Math.round(rangeStart), Math.max(Math.round(rangeEnd) - 3, Math.round(rangeStart)));

        const response = await processarXmlsImportados(cnpj, { signal: abortController.signal });

        if (response.status !== 'processado') {
          throw new Error(response.erros?.[0]?.mensagem ?? 'Falha ao processar XMLs importados.');
        }

        stopProcessingAnimation();
        setOperationProgress(Math.round(rangeEnd));
      }

      setOperationStage('completed');
      setOperationProgress(100);

      toast({
        title: 'Processamento concluído',
        description: 'Itens, notas e KPIs foram registrados com sucesso.',
      });

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['nfe-kpis'] }),
        queryClient.invalidateQueries({ queryKey: ['nfe-kpis-years'] }),
        queryClient.invalidateQueries({ queryKey: ['nfe-kpis-clientes'] }),
      ]);

      await carregarPendenciasXml();
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

    const importResults: ImportacaoXmlArquivoResultado[] = [];
    const batches = chunkFiles(selectedFiles, XML_IMPORT_BATCH_SIZE);

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
        const importProgress = Math.round((importedFiles / selectedFiles.length) * IMPORT_PROGRESS_MAX);
        setOperationProgress(importProgress);
      }

      const duplicados = importResults.filter((item) => item.status === 'duplicado').length;
      const erros = importResults.filter((item) => item.status === 'erro').length;

      toast({
        title: 'Importação concluída',
        description: `Importação finalizada com sucesso. Duplicados: ${duplicados}. Erros: ${erros}.`,
      });

      setSelectedFiles([]);
      await carregarPendenciasXml();

      const cnpjsProcessaveis =
        cnpjsImportados.length > 0
          ? cnpjsImportados
          : importResults
              .filter((item) => item.status === 'importado' && item.cnpj_emitente)
              .map((item) => item.cnpj_emitente as string);

      const cnpjsParaProcessar = Array.from(new Set(cnpjsProcessaveis));
      const fallbackCnpj =
        !cnpjsParaProcessar.length && user.emitente_cnpj && (pendenciasXml?.possui_pendentes ?? true)
          ? [user.emitente_cnpj]
          : cnpjsParaProcessar;

      await processImportedXml(fallbackCnpj, abortController);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        stopProcessingAnimation();
        setOperationStage('cancelled');
        toast({
          title: 'Operação cancelada',
          description: 'A importação/processamento dos XMLs foi cancelada na tela.',
        });
        return;
      }

      setOperationStage('error');
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
          <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed p-8 text-center">
            <Input
              id="xml-files"
              type="file"
              accept=".xml,text/xml,application/xml"
              multiple
              className="hidden"
              onChange={(event) => {
                addFiles(event.target.files);
                event.currentTarget.value = '';
              }}
            />
            <Button
              asChild
              variant="secondary"
              size="lg"
              disabled={isImporting || isProcessing || selectedFiles.length >= MAX_XML_FILES}
            >
              <label htmlFor="xml-files" className="cursor-pointer">
                <FileUp className="mr-2 h-4 w-4" />
                Importar arquivos XMLs
              </label>
            </Button>

            <p className="text-sm text-muted-foreground">
              {selectedFiles.length}/{MAX_XML_FILES} arquivo(s) • {formatFileSize(totalSize)}
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3">
            <Button
              variant="outline"
              onClick={clearList}
              disabled={!selectedFiles.length || isImporting || isProcessing}
            >
              <X className="mr-2 h-4 w-4" />
              Limpar lista
            </Button>

            <Button onClick={startImport} disabled={!selectedFiles.length || isImporting || isProcessing}>
              {isImporting || isProcessing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              {isImporting ? 'Importando...' : isProcessing ? 'Processando...' : 'Importar e processar'}
            </Button>

            {(isImporting || isProcessing) && (
              <Button variant="destructive" onClick={cancelOperation}>
                <X className="mr-2 h-4 w-4" />
                Cancelar operação
              </Button>
            )}
          </div>

          {hasOperationFeedback && (
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-3 text-sm">
                <p className="font-medium text-foreground">
                  {operationStage === 'processing'
                    ? 'Processando'
                    : operationStage === 'completed'
                      ? 'Processamento terminado'
                      : operationStage === 'cancelled'
                        ? 'Operação cancelada'
                        : operationStage === 'error'
                          ? 'Falha no processamento'
                          : 'Início do processamento'}
                </p>
                <span className="text-muted-foreground">{progressLabel}</span>
              </div>
              <Progress value={operationProgress} />
            </div>
          )}

          {possuiPendenciasNaoProcessadas && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Ainda faltam XMLs a serem processados ({pendenciasXml?.total_pendentes}). Uma nova operação volta a
              processar os pendentes automaticamente.
            </div>
          )}

          <div className="rounded-lg border">
            {selectedFiles.length ? (
              <ul className="max-h-72 divide-y overflow-auto">
                {selectedFiles.map((item) => (
                  <li key={item.id} className="px-4 py-3">
                    <p className="truncate text-sm font-medium">{item.file.name}</p>
                    <p className="text-xs text-muted-foreground">{formatFileSize(item.file.size)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                <FileText className="mx-auto mb-2 h-5 w-5" />
                Nenhum arquivo XML selecionado.
              </div>
            )}
          </div>

          {!!results.length && (
            <div className="space-y-2 rounded-lg border p-4">
              <h2 className="font-medium">Resultado da importação</h2>
              <p className="text-sm text-muted-foreground">
                XMLs avaliados: {Math.max(importedCount, results.length)} • Importados:{' '}
                {results.filter((item) => item.status === 'importado').length} • Duplicados:{' '}
                {results.filter((item) => item.status === 'duplicado').length} • Erros:{' '}
                {results.filter((item) => item.status === 'erro').length}
              </p>
              <ul className="max-h-40 space-y-1 overflow-auto text-sm text-muted-foreground">
                {results.map((result, index) => (
                  <li key={`${result.arquivo}-${index}`}>
                    <strong>{result.arquivo}:</strong> {result.mensagem}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
