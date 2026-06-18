import { CalendarRange, Loader2, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { monthOptions, reportFormatOptions, reportTypeOptions } from '../helpers/relatoriosIAOptions';
import type { RelatoriosIAPageData } from '../hooks/useRelatoriosIAPageData';
import type { ReportFormat, ReportType } from '../types';

type RelatoriosIAControlsCardProps = Pick<
  RelatoriosIAPageData,
  | 'availableYears'
  | 'selectedYear'
  | 'selectedMonth'
  | 'tipoRelatorio'
  | 'formatoRelatorio'
  | 'hasEmitenteCnpj'
  | 'isLoading'
  | 'periodoDescricao'
  | 'fonteDados'
  | 'tipoSelecionado'
  | 'formatoSelecionado'
  | 'handleGenerate'
  | 'handleCancelGeneration'
> & {
  onSelectedYearChange: (value: string) => void;
  onSelectedMonthChange: (value: string) => void;
  onTipoRelatorioChange: (value: ReportType) => void;
  onFormatoRelatorioChange: (value: ReportFormat) => void;
};

function SummaryTile({
  accentClass,
  title,
  value,
  description,
}: {
  accentClass: string;
  title: string;
  value: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-800/70 bg-slate-900/70 p-4">
      <p className={`text-xs font-semibold uppercase tracking-[0.18em] ${accentClass}`}>{title}</p>
      <p className="mt-2 text-sm text-slate-100">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{description}</p>
    </div>
  );
}

export function RelatoriosIAControlsCard(props: RelatoriosIAControlsCardProps) {
  const {
    availableYears,
    selectedYear,
    selectedMonth,
    tipoRelatorio,
    formatoRelatorio,
    hasEmitenteCnpj,
    isLoading,
    periodoDescricao,
    fonteDados,
    tipoSelecionado,
    formatoSelecionado,
    handleGenerate,
    handleCancelGeneration,
    onSelectedYearChange,
    onSelectedMonthChange,
    onTipoRelatorioChange,
    onFormatoRelatorioChange,
  } = props;

  return (
    <Card className="border-slate-800/80 bg-slate-950/60 shadow-[0_24px_70px_-48px_rgba(15,23,42,1)]">
      <CardHeader>
        <CardTitle>Parâmetros do relatório</CardTitle>
        <CardDescription>
          Defina o tema, o período e o formato desejado antes de solicitar a geração do relatório.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 md:grid-cols-3">
          <SummaryTile
            accentClass="text-sky-300"
            title="Tema"
            value={tipoSelecionado.label}
            description="Leitura guiada por IA com foco executivo."
          />

          <SummaryTile
            accentClass="text-emerald-300"
            title="Formato"
            value={formatoSelecionado.label}
            description={formatoSelecionado.description ?? ''}
          />

          <SummaryTile
            accentClass="text-amber-300"
            title="Período"
            value={periodoDescricao}
            description={`Base consultada: ${fonteDados}`}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="relatorio-tipo">Relatório</Label>
            <Select value={tipoRelatorio} onValueChange={(value) => onTipoRelatorioChange(value as ReportType)}>
              <SelectTrigger id="relatorio-tipo">
                <SelectValue placeholder="Selecione o relatório" />
              </SelectTrigger>
              <SelectContent className="bg-[#0E1525]">
                {reportTypeOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="relatorio-formato">Formato</Label>
            <Select value={formatoRelatorio} onValueChange={(value) => onFormatoRelatorioChange(value as ReportFormat)}>
              <SelectTrigger id="relatorio-formato">
                <SelectValue placeholder="Selecione o formato" />
              </SelectTrigger>
              <SelectContent className="bg-[#0E1525]">
                {reportFormatOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">{formatoSelecionado.description}</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="relatorio-ano">Ano</Label>
            <Select value={selectedYear} onValueChange={onSelectedYearChange}>
              <SelectTrigger id="relatorio-ano">
                <SelectValue placeholder="Selecione o ano" />
              </SelectTrigger>
              <SelectContent className="bg-[#0E1525]">
                {availableYears.map((year) => (
                  <SelectItem key={year} value={String(year)}>
                    {year}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="relatorio-mes">Mês</Label>
            <Select value={selectedMonth} onValueChange={onSelectedMonthChange}>
              <SelectTrigger id="relatorio-mes">
                <SelectValue placeholder="Selecione o mês" />
              </SelectTrigger>
              <SelectContent className="bg-[#0E1525]">
                {monthOptions.map((month) => (
                  <SelectItem key={month.value} value={month.value}>
                    {month.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          {isLoading && (
            <Button type="button" variant="outline" onClick={handleCancelGeneration} className="min-w-32">
              Cancelar
            </Button>
          )}
          <Button onClick={handleGenerate} disabled={isLoading || !hasEmitenteCnpj} className="min-w-32 gap-2">
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {isLoading ? 'Gerando...' : 'Gerar'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
