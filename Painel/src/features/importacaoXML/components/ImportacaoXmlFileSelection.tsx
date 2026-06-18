import { FileText, FileUp } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { getXmlFileSelectionSummary } from '../helpers/importacaoXmlView';
import type { ImportacaoXmlFileSelectionProps } from '../types';

export function ImportacaoXmlFileSelection({
  addFiles,
  formatFileSize,
  isDisabled,
  maxFiles,
  selectedFiles,
  totalSize,
}: ImportacaoXmlFileSelectionProps) {
  const hasReachedLimit = selectedFiles.length >= maxFiles;

  return (
    <>
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
        <Button asChild variant="secondary" size="lg" disabled={isDisabled || hasReachedLimit}>
          <label htmlFor="xml-files" className="cursor-pointer">
            <FileUp className="mr-2 h-4 w-4" />
            Importar arquivos XMLs
          </label>
        </Button>

        <p className="text-sm text-muted-foreground">
          {getXmlFileSelectionSummary({
            maxFiles,
            selectedCount: selectedFiles.length,
            totalSizeLabel: formatFileSize(totalSize),
          })}
        </p>
      </div>

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
    </>
  );
}
