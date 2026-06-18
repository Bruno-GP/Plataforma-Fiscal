import { FileText, FileUp } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { getImportacaoSpedFileSelectionSummary } from '../helpers/importacaoSpedView';
import type { ImportacaoSpedFileSelectionProps } from '../types';

export function ImportacaoSpedFileSelection({
  addFiles,
  formatFileSize,
  isDisabled,
  maxFiles,
  selectedFiles,
  totalSize,
}: ImportacaoSpedFileSelectionProps) {
  const hasReachedLimit = selectedFiles.length >= maxFiles;

  return (
    <>
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
        <Button asChild variant="secondary" disabled={isDisabled || hasReachedLimit}>
          <label htmlFor="sped-files" className="cursor-pointer">
            <FileUp className="mr-2 h-4 w-4" />
            Selecionar TXT
          </label>
        </Button>
      </div>

      <p className="text-sm text-muted-foreground">
        {getImportacaoSpedFileSelectionSummary({
          maxFiles,
          selectedCount: selectedFiles.length,
          totalSizeLabel: formatFileSize(totalSize),
        })}
      </p>

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
            Nenhum arquivo TXT selecionado.
          </div>
        )}
      </div>
    </>
  );
}
