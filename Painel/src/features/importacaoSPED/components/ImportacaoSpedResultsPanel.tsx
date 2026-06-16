import type { ImportacaoSpedResultsPanelProps } from '../types';

export function ImportacaoSpedResultsPanel({ results }: ImportacaoSpedResultsPanelProps) {
  if (!results.length) {
    return null;
  }

  return (
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
  );
}
