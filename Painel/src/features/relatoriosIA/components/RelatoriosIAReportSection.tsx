import { Download, FileText, Loader2, Sparkles } from 'lucide-react';
import type { RefObject } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { IAReportPreview } from '@/components/reports/IAReportPreview';

import type { RelatoriosIAPageData } from '../hooks/useRelatoriosIAPageData';

type RelatoriosIAReportSectionProps = Pick<
  RelatoriosIAPageData,
  'errorMessage' | 'report' | 'isLoading' | 'reportTitle' | 'reportSubtitle' | 'handleGenerate' | 'handleExportPdf'
> & {
  reportContainerRef: RefObject<HTMLDivElement | null>;
};

export function RelatoriosIAReportSection({
  errorMessage,
  report,
  isLoading,
  reportTitle,
  reportSubtitle,
  reportContainerRef,
  handleGenerate,
  handleExportPdf,
}: RelatoriosIAReportSectionProps) {
  return (
    <>
      {errorMessage && (
        <Alert variant="destructive">
          <AlertTitle>Falha ao gerar relatório</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      {report && (
        <Card className="overflow-hidden border-slate-800/80 bg-slate-950/40 shadow-[0_28px_90px_-56px_rgba(15,23,42,1)]">
          <CardHeader className="border-b border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-700/80 bg-slate-900/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-300">
                  <FileText className="h-3.5 w-3.5" />
                  Pré-visualização pronta para exportação
                </div>
                <div className="space-y-1">
                  <CardTitle>{reportTitle}</CardTitle>
                  <CardDescription>{reportSubtitle}</CardDescription>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleGenerate}
                  disabled={isLoading}
                  className="gap-2 border-slate-700 bg-slate-900/80 text-slate-100 hover:bg-slate-800"
                >
                  {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Atualizar
                </Button>
                <Button
                  type="button"
                  onClick={handleExportPdf}
                  className="gap-2 bg-red-600 text-white shadow-lg hover:bg-red-700"
                >
                  <Download className="h-4 w-4" />
                  Exportar PDF
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-4 md:p-6">
            <div className="rounded-[1.75rem] border border-slate-800/80 bg-slate-950/40 p-2 md:p-3">
              <div ref={reportContainerRef}>
                <IAReportPreview report={report} />
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}
