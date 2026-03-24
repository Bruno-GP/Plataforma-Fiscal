import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Loader2, Sparkles } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { IAReportPreview } from '@/components/reports/IAReportPreview';

import { useAuth } from '@/contexts/AuthContext';
import {
  fetchNfeAnaliseClientes,
  fetchNfeAnaliseCompras,
  fetchNfeAnaliseVendas,
  fetchNfeKpis,
  parseDecimal,
} from '@/services/nfe';
import {
  fetchSpedAnaliseClientes,
  fetchSpedAnaliseCompras,
  fetchSpedAnaliseVendas,
  fetchSpedKpis,
} from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

const monthOptions = [
  { value: 'all', label: 'Ano completo' },
  ...monthLabels.map((label, index) => ({ value: String(index + 1), label })),
];

const reportTypeOptions = [
  { value: 'compras', label: 'Compras' },
  { value: 'vendas', label: 'Vendas' },
  { value: 'clientes', label: 'Clientes' },
] as const;

const reportFormatOptions = [
  {
    value: 'executivo',
    label: 'Executivo',
    description: 'Resumo objetivo com os principais indicadores e conclusões.',
  },
  {
    value: 'analitico',
    label: 'Analítico',
    description: 'Visão mais detalhada para aprofundar a leitura dos dados.',
  },
] as const;

type ReportType = (typeof reportTypeOptions)[number]['value'];
type ReportFormat = (typeof reportFormatOptions)[number]['value'];

export default function RelatoriosIA() {
  const { user } = useAuth();
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [tipoRelatorio, setTipoRelatorio] = useState<ReportType>('compras');
  const [formatoRelatorio, setFormatoRelatorio] = useState<ReportFormat>('executivo');
  const [totalPeriodo, setTotalPeriodo] = useState(0);
  const reportContainerRef = useRef<HTMLDivElement | null>(null);

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const usaSped = Boolean(user?.tem_sped);
  const fonteDados = usaSped ? 'SPED Fiscal' : 'XML / NFe';

  const yearsQuery = useQuery({
    queryKey: ['kpis-years', usaSped ? 'sped' : 'xml', emitenteCnpj],
    queryFn: () =>
      usaSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const yearOptions = useMemo(() => {
    const resultados = yearsQuery.data?.resultados ?? [];
    const uniqueYears = new Set<number>();

    resultados.forEach((item) => {
      if (item.periodo_ano) {
        uniqueYears.add(item.periodo_ano);
      }
    });

    return [...uniqueYears].sort((a, b) => b - a);
  }, [yearsQuery.data]);

  useEffect(() => {
    if (!yearOptions.length) {
      return;
    }

    if (!yearOptions.includes(Number.parseInt(selectedYear, 10))) {
      setSelectedYear(String(yearOptions[0]));
    }
  }, [selectedYear, yearOptions]);

  const availableYears = yearOptions.length ? yearOptions : [new Date().getFullYear()];

  const formatoSelecionado = useMemo(
    () => reportFormatOptions.find((option) => option.value === formatoRelatorio) ?? reportFormatOptions[0],
    [formatoRelatorio],
  );

  const periodoDescricao = useMemo(() => {
    if (selectedMonth === 'all') {
      return `Ano ${selectedYear}`;
    }

    const mes = Number.parseInt(selectedMonth, 10);
    return `${monthLabels[mes - 1]} de ${selectedYear}`;
  }, [selectedMonth, selectedYear]);

  const reportTitle = useMemo(
    () => `Relatório ${formatoSelecionado.label.toLowerCase()} (${periodoDescricao})`,
    [formatoSelecionado.label, periodoDescricao],
  );

  const reportSubtitle = useMemo(
    () =>
      `Formato solicitado: ${formatoSelecionado.label}. Total ${
        tipoRelatorio === 'compras' ? 'comprado' : 'vendido'
      } no período: ${formatCurrency(totalPeriodo)}`,
    [formatoSelecionado.label, tipoRelatorio, totalPeriodo],
  );

  const handleExportPdf = () => {
    if (!reportContainerRef.current) {
      setErrorMessage('Não foi possível preparar o relatório para exportação.');
      return;
    }

    setErrorMessage(null);

    const reportHtml = reportContainerRef.current.innerHTML;
    const styleTags = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
      .map((node) => node.outerHTML)
      .join('\n');

    const iframe = document.createElement('iframe');
    iframe.setAttribute('aria-hidden', 'true');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    document.body.appendChild(iframe);

    const iframeDocument = iframe.contentDocument;
    if (!iframeDocument) {
      document.body.removeChild(iframe);
      setErrorMessage('Não foi possível abrir a visualização de impressão do PDF.');
      return;
    }

    iframeDocument.open();
    iframeDocument.write(`
      <!doctype html>
      <html lang="pt-BR">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>${reportTitle}</title>
          ${styleTags}
          <style>
            body {
              margin: 0;
              padding: 32px;
              background: #020617;
              color: #e2e8f0;
              font-family: ui-sans-serif, system-ui, sans-serif;
            }

            .pdf-shell {
              max-width: 1120px;
              margin: 0 auto;
            }

            .pdf-header {
              margin-bottom: 20px;
            }

            .pdf-title {
              margin: 0;
              font-size: 28px;
              font-weight: 700;
              color: #f8fafc;
            }

            .pdf-subtitle {
              margin: 8px 0 0;
              font-size: 14px;
              color: #94a3b8;
            }

            @page {
              size: A4;
              margin: 12mm;
            }

            @media print {
              body {
                padding: 0;
                background: #020617;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
              }
            }
          </style>
        </head>
        <body>
          <div class="pdf-shell">
            <div class="pdf-header">
              <h1 class="pdf-title">${reportTitle}</h1>
              <p class="pdf-subtitle">${reportSubtitle}</p>
            </div>
            ${reportHtml}
          </div>
        </body>
      </html>
    `);
    iframeDocument.close();

    const printFrame = iframe.contentWindow;
    if (!printFrame) {
      document.body.removeChild(iframe);
      setErrorMessage('Não foi possível iniciar a geração do PDF.');
      return;
    }

    window.setTimeout(() => {
      printFrame.focus();
      printFrame.print();
      window.setTimeout(() => {
        if (document.body.contains(iframe)) {
          document.body.removeChild(iframe);
        }
      }, 1000);
    }, 250);
  };

  const handleGenerate = async () => {
    if (!hasEmitenteCnpj || !emitenteCnpj) {
      setErrorMessage('CNPJ emitente inválido. Verifique o cadastro da empresa.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const yearNumber = Number.parseInt(selectedYear, 10);
      const monthNumber = Number.parseInt(selectedMonth, 10);

      const payload = {
        emitente_cnpj: emitenteCnpj,
        periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
        periodo_mes: selectedMonth === 'all' || Number.isNaN(monthNumber) ? undefined : monthNumber,
        limite: 5,
        gerar_relatorio_ia: true,
        formato_relatorio: formatoRelatorio,
      };

      const response =
        tipoRelatorio === 'compras'
          ? usaSped
            ? await fetchSpedAnaliseCompras(payload)
            : await fetchNfeAnaliseCompras(payload)
          : tipoRelatorio === 'clientes'
            ? usaSped
              ? await fetchSpedAnaliseClientes(payload)
              : await fetchNfeAnaliseClientes(payload)
            : usaSped
              ? await fetchSpedAnaliseVendas(payload)
              : await fetchNfeAnaliseVendas(payload);

      const total = 'total_comprado' in response ? response.total_comprado : response.total_vendido;

      setTotalPeriodo(parseDecimal(total ?? 0));
      setReport(response.relatorio_ia ?? 'A IA não retornou conteúdo para este período.');
    } catch (error) {
      setReport(null);
      setErrorMessage(error instanceof Error ? error.message : 'Falha ao gerar relatório com IA.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="space-y-6 py-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Relatórios com IA</h1>
        <p className="text-muted-foreground">
          Escolha o tipo e o formato do relatório para gerar uma leitura com IA baseada nos dados fiscais de
          compras, vendas ou clientes ({fonteDados}).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Parâmetros do relatório</CardTitle>
          <CardDescription>
            Defina o tema, o período e o formato desejado antes de solicitar a geração do relatório.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="relatorio-tipo">Relatório</Label>
              <Select value={tipoRelatorio} onValueChange={(value) => setTipoRelatorio(value as ReportType)}>
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
              <Select value={formatoRelatorio} onValueChange={(value) => setFormatoRelatorio(value as ReportFormat)}>
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
              <Select value={selectedYear} onValueChange={setSelectedYear}>
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
              <Select value={selectedMonth} onValueChange={setSelectedMonth}>
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

          <div className="flex justify-end">
            <Button onClick={handleGenerate} disabled={isLoading || !hasEmitenteCnpj} className="min-w-32 gap-2">
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {isLoading ? 'Gerando...' : 'Gerar'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {errorMessage && (
        <Alert variant="destructive">
          <AlertTitle>Falha ao gerar relatório</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      {report && (
        <Card>
          <CardHeader>
            <div className="space-y-1">
              <CardTitle>{reportTitle}</CardTitle>
              <CardDescription>{reportSubtitle}</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <div className="relative">
              <Button
                type="button"
                variant="destructive"
                onClick={handleExportPdf}
                className="absolute top-3 right-3 z-10 gap-2 bg-red-600 text-white shadow-lg hover:bg-red-700"
              >
                <FileText className="h-4 w-4" />
                Gerar PDF
              </Button>
              <div ref={reportContainerRef}>
                <IAReportPreview report={report} />
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </section>
  );
}
