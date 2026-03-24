import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Sparkles } from 'lucide-react';

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
  parseDecimal 
} from '@/services/nfe';
import { fetchSpedAnaliseClientes, fetchSpedAnaliseCompras, fetchSpedAnaliseVendas, fetchSpedKpis } from '@/services/sped';

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

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const usaSped = Boolean(user?.tem_sped);

  const fonteDados = usaSped ? 'SPED Fiscal' : 'XML / NFe';

  const yearsQuery = useQuery({
    queryKey: ['kpis-years', usaSped ? 'sped' : 'xml', emitenteCnpj],
    queryFn: () => (usaSped
      ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
      : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })),
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

  const availableYears = yearOptions.length
    ? yearOptions
    : [new Date().getFullYear()];

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

      const response = tipoRelatorio === 'compras'
        ? (usaSped ? await fetchSpedAnaliseCompras(payload) : await fetchNfeAnaliseCompras(payload))
        : tipoRelatorio === 'clientes'
          ? (usaSped ? await fetchSpedAnaliseClientes(payload) : await fetchNfeAnaliseClientes(payload))
          : (usaSped ? await fetchSpedAnaliseVendas(payload) : await fetchNfeAnaliseVendas(payload));

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
          Escolha o tipo e o formato do relatório para gerar uma leitura com IA baseada nos dados fiscais de compras, vendas ou clientes ({fonteDados}).
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
            <CardTitle>Relatório {formatoSelecionado.label.toLowerCase()} ({periodoDescricao})</CardTitle>
            <CardDescription>
              Formato solicitado: {formatoSelecionado.label}. Total {tipoRelatorio === 'compras' ? 'comprado' : 'vendido'} no período: {formatCurrency(totalPeriodo)}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <IAReportPreview report={report} />
          </CardContent>
        </Card>
      )}
    </section>
  );
}
