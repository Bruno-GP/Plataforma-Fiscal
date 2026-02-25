import { useMemo, useState } from 'react';
import { FileUp, FileText, Upload, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { importarXmlArquivo, processarXmlsImportados, type ImportacaoXmlArquivoResultado } from '@/services/nfe';
import { useToast } from '@/hooks/use-toast';

interface XmlFileItem {
  id: string;
  file: File;
}

const MAX_XML_FILES = 1000;

const formatFileSize = (size: number): string => {
    if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  }

  if (size >= 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${size} B`;
};

export default function ImportacaoXML() {
  const [selectedFiles, setSelectedFiles] = useState<XmlFileItem[]>([]);
  const [isImporting, setIsImporting] = useState(false);
  const [importedCount, setImportedCount] = useState(0);
  const [results, setResults] = useState<ImportacaoXmlArquivoResultado[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const { toast } = useToast();

  const totalSize = useMemo(
    () => selectedFiles.reduce((acc, item) => acc + item.file.size, 0),
    [selectedFiles]
  );

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
          description: 'Você pode importar no máximo 1000 XMLs por vez.',
          variant: 'destructive',
        });
      }

      return nextFiles;
    });
  };

  const removeFile = (id: string) => {
    setSelectedFiles((prev) => prev.filter((item) => item.id !== id));
  };

  const clearList = () => {
    setImportedCount(0);
    setResults([]);
  };

  const progressValue = selectedFiles.length ? (importedCount / selectedFiles.length) * 100 : 0;

  const cnpjsImportados = useMemo(() => {
    const cnpjs = new Set(
      results
        .filter((item) => item.status === 'importado' && item.cnpj_emitente)
        .map((item) => item.cnpj_emitente as string)
    );

    return Array.from(cnpjs);
  }, [results]);

  const processImportedXml = async () => {
    if (!cnpjsImportados.length || isProcessing || isImporting) {
      return;
    }

    setIsProcessing(true);

    try {
      for (const cnpj of cnpjsImportados) {
        const response = await processarXmlsImportados(cnpj);

        if (response.status !== 'processado') {
          throw new Error(response.erros?.[0]?.mensagem ?? 'Falha ao processar XMLs importados.');
        }
      }

      toast({
        title: 'Processamento concluído',
        description: 'Itens, notas e KPIs foram registrados com sucesso.',
      });
    } catch (error) {
      toast({
        title: 'Falha no processamento',
        description: error instanceof Error ? error.message : 'Não foi possível processar os XMLs importados.',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const startImport = async () => {
    if (!selectedFiles.length || isImporting) {
      return;
    }

    setIsImporting(true);
    setImportedCount(0);
    setResults([]);

    const importResults: ImportacaoXmlArquivoResultado[] = [];

    try {
      for (const item of selectedFiles) {
        const response = await importarXmlArquivo(item.file);
        importResults.push(...response.resultados);
        setResults([...importResults]);
        setImportedCount((count) => count + 1);
      }

      const duplicados = importResults.filter((item) => item.status === 'duplicado').length;
      const erros = importResults.filter((item) => item.status === 'erro').length;

      toast({
        title: 'Importação concluída',
        description: `Importação finalizada com sucesso. Duplicados: ${duplicados}. Erros: ${erros}.`,
      });

      setSelectedFiles([]);
    } catch (error) {
      toast({
        title: 'Falha na importação',
        description: error instanceof Error ? error.message : 'Não foi possível importar os XMLs.',
        variant: 'destructive',
      });
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Importação de XML</h1>
        <p className="text-muted-foreground">
          Selecione os XMLs da NFe/NFCe e importe em lotes de até 1000 arquivos. Depois da importação, execute a fase de processamento para registrar notas, itens e KPIs.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileUp className="h-5 w-5" />
            Enviar arquivos XML
          </CardTitle>
          <CardDescription>
            Clique no botão central para adicionar os XMLs, acompanhe o contador e depois inicie a importação.
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
            <Button asChild variant="secondary" size="lg" disabled={isImporting || selectedFiles.length >= MAX_XML_FILES}>
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
            <Button variant="outline" onClick={clearList} disabled={!selectedFiles.length || isImporting}>
              <Trash2 className="mr-2 h-4 w-4" />
              Limpar lista
            </Button>
            <Button onClick={startImport} disabled={!selectedFiles.length || isImporting || isProcessing}>
              <Upload className="mr-2 h-4 w-4" />
              {isImporting ? 'Importando...' : 'Iniciar importação'}
            </Button>

            <Button
              variant="default"
              onClick={processImportedXml}
              disabled={!cnpjsImportados.length || isImporting || isProcessing}
            >
              <FileText className="mr-2 h-4 w-4" />
              {isProcessing ? 'Processando NFe...' : 'Processar NFe (itens, notas e KPIs)'}
            </Button>
          </div>

          {(isImporting || importedCount > 0) && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Progresso da importação: {importedCount}/{Math.max(selectedFiles.length, importedCount)} XMLs processados
              </p>
              <Progress value={progressValue} />
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