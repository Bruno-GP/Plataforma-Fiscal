import { useMemo, useState } from 'react';
import { FileUp, FileText, Upload, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';

interface XmlFileItem {
  id: string;
  file: File;
}

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
      const newItems = xmlFiles
        .filter((file) => !existingNames.has(file.name))
        .map((file) => ({
          id: `${file.name}-${file.lastModified}`,
          file,
        }));

      return [...prev, ...newItems];
    });
  };

  const removeFile = (id: string) => {
    setSelectedFiles((prev) => prev.filter((item) => item.id !== id));
  };

  const clearList = () => {
    setSelectedFiles([]);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Importação de XML</h1>
        <p className="text-muted-foreground">
          Selecione os arquivos XML das notas fiscais para enviar e processar no sistema.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileUp className="h-5 w-5" />
            Enviar arquivos XML
          </CardTitle>
          <CardDescription>
            Você pode selecionar um ou mais arquivos. Apenas arquivos com extensão .xml serão listados.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-dashed p-6">
            <Label htmlFor="xml-files" className="mb-2 block text-sm font-medium">
              Arquivos de NFe/NFCe
            </Label>
            <Input
              id="xml-files"
              type="file"
              accept=".xml,text/xml,application/xml"
              multiple
              onChange={(event) => {
                addFiles(event.target.files);
                event.currentTarget.value = '';
              }}
            />
            <p className="mt-3 text-sm text-muted-foreground">
              Dica: você pode selecionar novos arquivos depois, eles serão adicionados à lista.
            </p>
          </div>

          <Separator />

          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-medium">Arquivos selecionados</h2>
                <p className="text-sm text-muted-foreground">
                  {selectedFiles.length} arquivo(s) • {formatFileSize(totalSize)}
                </p>
              </div>

              <Button variant="outline" onClick={clearList} disabled={!selectedFiles.length}>
                <Trash2 className="mr-2 h-4 w-4" />
                Limpar lista
              </Button>
            </div>

            <div className="rounded-lg border">
              {selectedFiles.length ? (
                <ul className="divide-y">
                  {selectedFiles.map((item) => (
                    <li key={item.id} className="flex items-center justify-between gap-3 px-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{item.file.name}</p>
                        <p className="text-xs text-muted-foreground">{formatFileSize(item.file.size)}</p>
                      </div>

                      <Button variant="ghost" size="icon" onClick={() => removeFile(item.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
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
          </div>

          <div className="flex justify-end">
            <Button disabled={!selectedFiles.length}>
              <Upload className="mr-2 h-4 w-4" />
              Iniciar importação
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}