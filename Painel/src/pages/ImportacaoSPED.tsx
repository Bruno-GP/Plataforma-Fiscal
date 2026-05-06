import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FileText, FileUp, Upload, Database } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { waitForJob, type ProcessingJobResponse } from '@/services/jobs';
import { saveFiscalOperation } from '@/services/operations';
import {
  consultarPendenciasSped,
  importarSpedArquivo,
  processarSpedsImportados,
  type ImportacaoSpedArquivoResultado,
  type ImportacaoSpedPendenciasResponse,
} from '@/services/sped';

interface SpedFileItem {
  id: string;
  file: File;
}

const MAX_SPED_FILES = 500;

export default function ImportacaoSPED() {
  const { toast } = useToast();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [selectedFiles, setSelectedFiles] = useState<SpedFileItem[]>([]);
  const [isImporting, setIsImporting] = useState(false);
  const [importedCount, setImportedCount] = useState(0);
  const [results, setResults] = useState<ImportacaoSpedArquivoResultado[]>([]);
  const [pendencias, setPendencias] = useState<ImportacaoSpedPendenciasResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentJob, setCurrentJob] = useState<ProcessingJobResponse | null>(null);
  const [jobMessage, setJobMessage] = useState<string | null>(null);
  const processingAbortRef = useRef<AbortController | null>(null);

  const totalSize = useMemo(() => selectedFiles.reduce((acc, item) => acc + item.file.size, 0), [selectedFiles]);

  const progressValue = selectedFiles.length ? (importedCount / selectedFiles.length) * 100 : 0;

  const formatFileSize = (size: number) => {
    if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${size} B`;
  };

  const carregarPendencias = useCallback(async () => {
    if (!user?.emitente_cnpj) return;

    try {
      const response = await consultarPendenciasSped(user.emitente_cnpj);
      setPendencias(response);
    } catch {
      setPendencias(null);
    }
  }, [user?.emitente_cnpj]);

  useEffect(() => {
    void carregarPendencias();
  }, [carregarPendencias]);

  useEffect(() => {
    return () => {
      processingAbortRef.current?.abort();
    };
  }, []);

  const addFiles = (files: FileList | null) => {
    if (!files?.length) return;

    const txtFiles = Array.from(files).filter((file) => file.name.toLowerCase().endsWith('.txt'));

    setSelectedFiles((prev) => {
      const existingNames = new Set(prev.map((item) => item.file.name));
      const availableSlots = MAX_SPED_FILES - prev.length;
      const newItems = txtFiles
        .filter((file) => !existingNames.has(file.name))
        .slice(0, Math.max(availableSlots, 0))
        .map((file) => ({ id: `${file.name}-${file.lastModified}`, file }));

      return [...prev, ...newItems];
    });
  };

  const importarArquivos = async () => {
    if (!selectedFiles.length || isImporting || !user?.emitente_cnpj) return;

    setIsImporting(true);
    setImportedCount(0);
    setResults([]);
    setCurrentJob(null);
    setJobMessage(null);

    const importResults: ImportacaoSpedArquivoResultado[] = [];

    try {
      for (const item of selectedFiles) {
        const response = await importarSpedArquivo(item.file, user.emitente_cnpj);
        importResults.push(...response.resultados);
        setResults([...importResults]);
        setImportedCount((count) => count + 1);
      }

      setSelectedFiles([]);
      await carregarPendencias();

      toast({
        title: 'Importação concluída',
        description: `Arquivos importados com sucesso. Total: ${importResults.length}.`,
      });
      saveFiscalOperation({
        type: 'sped-import',
        status: importResults.some((item) => item.status !== 'importado') ? 'warning' : 'success',
        title: 'Importacao SPED concluida',
        description: `Arquivos avaliados: ${importResults.length}.`,
        cnpj: user.emitente_cnpj,
      });
    } catch (error) {
      saveFiscalOperation({
        type: 'sped-import',
        status: 'error',
        title: 'Falha na importacao SPED',
        description: error instanceof Error ? error.message : 'Nao foi possivel importar os SPEDs.',
        cnpj: user?.emitente_cnpj ?? '',
      });
      toast({
        title: 'Falha na importação',
        description: error instanceof Error ? error.message : 'Não foi possível importar os SPEDs.',
        variant: 'destructive',
      });
    } finally {
      setIsImporting(false);
    }
  };

  const processarImportados = async () => {
    if (!user?.emitente_cnpj || isProcessing) return;

    processingAbortRef.current?.abort();
    const abortController = new AbortController();
    processingAbortRef.current = abortController;

    setIsProcessing(true);
    setCurrentJob(null);
    setJobMessage(null);

    try {
      const createdJob = await processarSpedsImportados(user.emitente_cnpj, { signal: abortController.signal });
      setJobMessage(createdJob.message);
      saveFiscalOperation({
        type: 'sped-process',
        status: 'queued',
        title: 'Processamento SPED enviado para fila',
        description: createdJob.message,
        cnpj: user.emitente_cnpj,
        jobId: createdJob.job_id,
        jobStatus: createdJob.status,
        backendMessage: createdJob.message,
      });

      const finishedJob = await waitForJob(createdJob.job_id, {
        signal: abortController.signal,
        onUpdate: (job) => {
          setCurrentJob(job);
          setJobMessage(job.mensagem ?? `Status do processamento: ${job.status}`);
        },
      });
      setCurrentJob(finishedJob);

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kpis'] }),
        queryClient.invalidateQueries({ queryKey: ['kpis-years'] }),
      ]);

      await carregarPendencias();

      toast({
        title: 'Processamento concluído',
        description: finishedJob.mensagem ?? 'Processamento SPED finalizado com sucesso.',
      });
      saveFiscalOperation({
        type: 'sped-process',
        status: 'success',
        title: 'Processamento SPED concluido',
        description: finishedJob.mensagem ?? 'Processamento SPED finalizado com sucesso.',
        cnpj: user.emitente_cnpj,
        jobId: finishedJob.job_id,
        jobStatus: finishedJob.status,
        backendMessage: finishedJob.mensagem ?? undefined,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        saveFiscalOperation({
          type: 'sped-process',
          status: 'cancelled',
          title: 'Acompanhamento SPED interrompido',
          description: 'O acompanhamento foi interrompido nesta tela. Um job ja criado pode continuar no backend.',
          cnpj: user?.emitente_cnpj ?? '',
          jobId: currentJob?.job_id,
          jobStatus: currentJob?.status,
          backendMessage: currentJob?.mensagem ?? undefined,
        });
        toast({
          title: 'Acompanhamento interrompido',
          description: 'O processamento pode continuar no backend. Acompanhe pela Central de inconsistencias.',
        });
        return;
      }

      saveFiscalOperation({
        type: 'sped-process',
        status: 'error',
        title: 'Falha no processamento SPED',
        description: error instanceof Error ? error.message : 'Nao foi possivel processar os SPEDs.',
        cnpj: user?.emitente_cnpj ?? '',
        jobId: currentJob?.job_id,
        jobStatus: currentJob?.status,
        backendMessage: currentJob?.mensagem ?? undefined,
      });
      toast({
        title: 'Falha no processamento',
        description: error instanceof Error ? error.message : 'Não foi possível processar os SPEDs.',
        variant: 'destructive',
      });
    } finally {
      if (processingAbortRef.current === abortController) {
        processingAbortRef.current = null;
      }
      setIsProcessing(false);
    }
  };

  const pararAcompanhamento = () => {
    processingAbortRef.current?.abort();
  };

  return (
    <div className="space-y-6 py-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Importações SPED Fiscal</h1>
        <p className="text-muted-foreground">Tela dedicada para importar arquivos TXT do SPED no banco e executar o processamento.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileUp className="h-5 w-5" />Enviar arquivos SPED (.txt)</CardTitle>
          <CardDescription>Faça a importação para staging e depois rode o processamento dos registros fiscais.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Input
            id="sped-files"
            type="file"
            accept=".txt,text/plain"
            multiple
            className="hidden"
            onChange={(event) => {
              addFiles(event.target.files);
              event.currentTarget.value = '';
            }}
          />

          <div className="flex flex-wrap items-center gap-3">
            <Button asChild variant="secondary" disabled={isImporting || selectedFiles.length >= MAX_SPED_FILES}>
              <label htmlFor="sped-files" className="cursor-pointer"><FileUp className="mr-2 h-4 w-4" />Selecionar TXT</label>
            </Button>
            <Button onClick={importarArquivos} disabled={!selectedFiles.length || isImporting || isProcessing}>
              <Upload className="mr-2 h-4 w-4" />{isImporting ? 'Importando...' : 'Importar para banco'}
            </Button>
            <Button onClick={processarImportados} disabled={!pendencias?.possui_pendentes || isProcessing || isImporting}>
              <Database className="mr-2 h-4 w-4" />{isProcessing ? 'Processando...' : 'Processar SPED importado'}
            </Button>
            {isProcessing && (
              <Button variant="outline" onClick={pararAcompanhamento}>
                Parar acompanhamento
              </Button>
            )}
          </div>

          <p className="text-sm text-muted-foreground">{selectedFiles.length}/{MAX_SPED_FILES} arquivo(s) • {formatFileSize(totalSize)}</p>

          {(isImporting || importedCount > 0) && <Progress value={progressValue} />}

          {isProcessing && (
            <div className="space-y-2 rounded-lg border p-4 text-sm">
              <p className="font-medium">Processamento em fila ou execucao</p>
              <p className="text-muted-foreground">{jobMessage ?? 'Aguardando retorno do backend.'}</p>
              {currentJob && (
                <div className="text-xs text-muted-foreground">
                  Job {currentJob.job_id} - {currentJob.status}
                  {currentJob.total_itens > 0
                    ? ` - ${currentJob.itens_processados}/${currentJob.total_itens} item(ns)`
                    : ''}
                </div>
              )}
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
                <FileText className="mx-auto mb-2 h-5 w-5" />Nenhum arquivo TXT selecionado.
              </div>
            )}
          </div>

          {!!results.length && (
            <div className="space-y-2 rounded-lg border p-4">
              <h2 className="font-medium">Resultado da importação</h2>
              <ul className="max-h-40 space-y-1 overflow-auto text-sm text-muted-foreground">
                {results.map((result, index) => (
                  <li key={`${result.arquivo}-${index}`}><strong>{result.arquivo}:</strong> {result.mensagem}</li>
                ))}
              </ul>
            </div>
          )}

          {currentJob?.status === 'SUCCESS' && (
            <div className="space-y-2 rounded-lg border p-4 text-sm">
              <p><strong>Job:</strong> {currentJob.job_id}</p>
              <p><strong>Status:</strong> {currentJob.status}</p>
              {currentJob.total_itens > 0 && (
                <p><strong>Itens processados:</strong> {currentJob.itens_processados}/{currentJob.total_itens}</p>
              )}
              {currentJob.mensagem && <p><strong>Mensagem:</strong> {currentJob.mensagem}</p>}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
