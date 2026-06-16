import { useCallback, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { Card, CardContent } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { useImportFileQueue } from '@/hooks/useImportFileQueue';
import { isJobAbortError, useProcessingJobFlow } from '@/hooks/useProcessingJobFlow';
import { saveFiscalOperation } from '@/services/operations';
import {
  consultarPendenciasSped,
  importarSpedArquivo,
  processarSpedsImportados,
  type ImportacaoSpedArquivoResultado,
  type ImportacaoSpedPendenciasResponse,
} from '@/services/sped';
import { invalidateFiscalProcessingCache } from '@/utils/fiscalCache';
import { ImportacaoSpedActions } from '@/features/importacaoSPED/components/ImportacaoSpedActions';
import { ImportacaoSpedCardHeader } from '@/features/importacaoSPED/components/ImportacaoSpedCardHeader';
import { ImportacaoSpedFileSelection } from '@/features/importacaoSPED/components/ImportacaoSpedFileSelection';
import { ImportacaoSpedHeader } from '@/features/importacaoSPED/components/ImportacaoSpedHeader';
import { ImportacaoSpedProgressPanel } from '@/features/importacaoSPED/components/ImportacaoSpedProgressPanel';
import { ImportacaoSpedResultsPanel } from '@/features/importacaoSPED/components/ImportacaoSpedResultsPanel';

const MAX_SPED_FILES = 500;

export default function ImportacaoSPED() {
  const { toast } = useToast();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { selectedFiles, setSelectedFiles, addFiles, totalSize, formatFileSize } = useImportFileQueue({
    maxFiles: MAX_SPED_FILES,
    acceptedExtensions: ['.txt'],
  });
  const [isImporting, setIsImporting] = useState(false);
  const [importedCount, setImportedCount] = useState(0);
  const [results, setResults] = useState<ImportacaoSpedArquivoResultado[]>([]);
  const [pendencias, setPendencias] = useState<ImportacaoSpedPendenciasResponse | null>(null);
  const {
    isProcessing,
    currentJob,
    jobMessage,
    resetJobState,
    runProcessingJob,
    cancelProcessing,
    getCurrentJob,
  } = useProcessingJobFlow();

  const progressValue = selectedFiles.length ? (importedCount / selectedFiles.length) * 100 : 0;

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

  const importarArquivos = async () => {
    if (!selectedFiles.length || isImporting || !user?.emitente_cnpj) return;

    setIsImporting(true);
    setImportedCount(0);
    setResults([]);
    resetJobState();

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
        title: 'ImportaÃ§Ã£o concluÃ­da',
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
        title: 'Falha na importaÃ§Ã£o',
        description: error instanceof Error ? error.message : 'NÃ£o foi possÃ­vel importar os SPEDs.',
        variant: 'destructive',
      });
    } finally {
      setIsImporting(false);
    }
  };

  const processarImportados = async () => {
    if (!user?.emitente_cnpj || isProcessing) return;

    try {
      const finishedJob = await runProcessingJob({
        createJob: (signal) => processarSpedsImportados(user.emitente_cnpj, { signal }),
        onCreated: (createdJob) => {
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
        },
      });

      await invalidateFiscalProcessingCache(queryClient, 'sped');

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
      navigate('/analise-vendas');
    } catch (error) {
      const latestJob = getCurrentJob();

      if (isJobAbortError(error)) {
        saveFiscalOperation({
          type: 'sped-process',
          status: 'cancelled',
          title: 'Acompanhamento SPED interrompido',
          description: 'O acompanhamento foi interrompido nesta tela. Um job ja criado pode continuar no backend.',
          cnpj: user?.emitente_cnpj ?? '',
          jobId: latestJob?.job_id,
          jobStatus: latestJob?.status,
          backendMessage: latestJob?.mensagem ?? undefined,
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
        jobId: latestJob?.job_id,
        jobStatus: latestJob?.status,
        backendMessage: latestJob?.mensagem ?? undefined,
      });
      toast({
        title: 'Falha no processamento',
        description: error instanceof Error ? error.message : 'NÃ£o foi possÃ­vel processar os SPEDs.',
        variant: 'destructive',
      });
    }
  };

  const pararAcompanhamento = () => {
    cancelProcessing();
  };

  return (
    <div className="space-y-6 py-6">
      <ImportacaoSpedHeader
        title="Importação SPED Fiscal"
        description="Tela dedicada para importar arquivos TXT do SPED no banco e executar o processamento."
      />

      <Card>
        <ImportacaoSpedCardHeader />
        <CardContent className="space-y-6">
          <ImportacaoSpedFileSelection
            addFiles={addFiles}
            formatFileSize={formatFileSize}
            isDisabled={isImporting || isProcessing}
            maxFiles={MAX_SPED_FILES}
            selectedFiles={selectedFiles}
            totalSize={totalSize}
          />

          <ImportacaoSpedActions
            isImporting={isImporting}
            isProcessing={isProcessing}
            onImport={importarArquivos}
            onProcess={processarImportados}
            onStop={pararAcompanhamento}
            pendencias={pendencias}
            selectedCount={selectedFiles.length}
          />

          <ImportacaoSpedProgressPanel
            currentJob={currentJob}
            importedCount={importedCount}
            isImporting={isImporting}
            isProcessing={isProcessing}
            jobMessage={jobMessage}
            progress={progressValue}
          />

          <ImportacaoSpedResultsPanel results={results} />
        </CardContent>
      </Card>
    </div>
  );
}
