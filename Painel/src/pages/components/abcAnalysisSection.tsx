import { useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';

import { AbcAnalysisReport } from './abcAnalysisReport';

interface AbcReportItem {
  key: string;
  label: string;
  value: number;
  formattedValue?: string;
}

interface AbcReportOption {
  id: string;
  label: string;
  title?: string;
  description?: string;
  items: AbcReportItem[];
  emptyMessage?: string;
}

interface AbcAnalysisSectionProps {
  options: AbcReportOption[];
  title?: string;
  description?: string;
}

export function AbcAnalysisSection({
  options,
  title = 'Relatório ABC',
  description = 'Analise a classificação ABC no final da página e alterne entre os grupos.',
}: AbcAnalysisSectionProps) {
  const [selectedId, setSelectedId] = useState(options[0]?.id ?? '');

  const selectedOption = useMemo(
    () => options.find((option) => option.id === selectedId) ?? options[0],
    [options, selectedId],
  );

  if (!selectedOption) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <Button
            key={option.id}
            type="button"
            variant={option.id === selectedOption.id ? 'default' : 'outline'}
            onClick={() => setSelectedId(option.id)}
            className="h-8"
          >
            {option.label}
          </Button>
        ))}
      </div>

      <AbcAnalysisReport
        title={selectedOption.title}
        description={selectedOption.description}
        items={selectedOption.items}
        emptyMessage={selectedOption.emptyMessage}
      />
    </div>
  );
}