import { useEffect, useMemo, useState } from 'react';
import { FileText, FileUp, Upload, Database } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import {
  consultarPendenciasSped,
  importarSpedArquivo,
  processarSpedsImportados,
  type ImportacaoSpedArquivoResultado,
  type ImportacaoSpedPendenciasResponse,
  type ProcessamentoSpedResponse,
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
  const [processamento, setProcessamento] = useState<ProcessamentoSpedResponse | null>(null);

  const totalSize = useMemo(() => selectedFiles.reduce((acc, item) => acc + item.file.size, 0), [selectedFiles]);

  const progressValue = selectedFiles.length ? (importedCount / selectedFiles.length) * 100 : 0;

  const formatFileSize = (size: number) => {
    if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${size} B`;
  };

  const carregarPendencias = async () => {
    if (!user?.emitente_cnpj) return;

    try {
      const response = await consultarPendenciasSped(user.emitente_cnpj);
      setPendencias(response);
    } catch {
      setPendencias(null);
    }
  };

  useEffect(() => {
    void carregarPendencias();
  }, [user?.emitente_cnpj]);

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
    } catch (error) {
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

    setIsProcessing(true);
    try {
      const response = await processarSpedsImportados(user.emitente_cnpj);
      setProcessamento(response);

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kpis'] }),
        queryClient.invalidateQueries({ queryKey: ['kpis-years'] }),
      ]);

      await carregarPendencias();

      toast({
        title: 'Processamento concluído',
        description: `Foram processados ${response.total_arquivos_processados} arquivo(s) SPED.`,
      });
    } catch (error) {
      toast({
        title: 'Falha no processamento',
        description: error instanceof Error ? error.message : 'Não foi possível processar os SPEDs.',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
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
          </div>

          <p className="text-sm text-muted-foreground">{selectedFiles.length}/{MAX_SPED_FILES} arquivo(s) • {formatFileSize(totalSize)}</p>

          {(isImporting || importedCount > 0) && <Progress value={progressValue} />}

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

          {processamento && (
            <div className="space-y-2 rounded-lg border p-4 text-sm">
              <p><strong>Arquivos processados:</strong> {processamento.total_arquivos_processados}</p>
              <p><strong>Total de linhas:</strong> {processamento.total_linhas}</p>
              <p><strong>Registros identificados:</strong> {processamento.total_registros_identificados}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}