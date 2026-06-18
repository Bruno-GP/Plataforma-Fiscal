import { getXmlImportResultSummary } from '../helpers/importacaoXmlView';
import type { ImportacaoXmlResultsPanelProps } from '../types';

export function ImportacaoXmlResultsPanel({ importedCount, results }: ImportacaoXmlResultsPanelProps) {
  if (!results.length) {
    return null;
  }

  const summary = getXmlImportResultSummary(results, importedCount);

  return (
    <div className="space-y-2 rounded-lg border p-4">
      <h2 className="font-medium">Resultado da importação</h2>
      <p className="text-sm text-muted-foreground">
        XMLs avaliados: {summary.evaluated} • Importados: {summary.imported} • Duplicados:{' '}
        {summary.duplicated} • Erros: {summary.errors}
      </p>
      <ul className="max-h-40 space-y-1 overflow-auto text-sm text-muted-foreground">
        {results.map((result, index) => (
          <li key={`${result.arquivo}-${index}`}>
            <strong>{result.arquivo}:</strong> {result.mensagem}
          </li>
        ))}
      </ul>
    </div>
  );
}
