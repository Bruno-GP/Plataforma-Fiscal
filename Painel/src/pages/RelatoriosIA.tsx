import { useMemo, useState } from 'react';
import { Loader2, Sparkles } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '@/contexts/AuthContext';
import { fetchNfeAnaliseCompras, parseDecimal } from '@/services/nfe';
import { fetchSpedAnaliseCompras } from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

const monthOptions = [
  { value: 'all', label: 'Ano completo' },
  ...monthLabels.map((label, index) => ({ value: String(index + 1), label })),
];

export default function RelatoriosIA() {
  const { user } = useAuth();
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [totalComprado, setTotalComprado] = useState(0);

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const fonteDados = user?.tem_sped ? 'SPED Fiscal' : 'XML / NFe';

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
      };

      const response = user?.tem_sped
        ? await fetchSpedAnaliseCompras(payload)
        : await fetchNfeAnaliseCompras(payload);

      setTotalComprado(parseDecimal(response.total_comprado ?? 0));
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
          Gere um relatório executivo automático com base nos dados fiscais de compras ({fonteDados}).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Parâmetros do relatório</CardTitle>
          <CardDescription>
            O sistema utiliza o agente executivo conectado ao backend para produzir o texto narrativo.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="relatorio-ano">Ano</Label>
              <Select value={selectedYear} onValueChange={setSelectedYear}>
                <SelectTrigger id="relatorio-ano">
                  <SelectValue placeholder="Selecione o ano" />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 6 }, (_, idx) => new Date().getFullYear() - idx).map((year) => (
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
                <SelectContent>
                  {monthOptions.map((month) => (
                    <SelectItem key={month.value} value={month.value}>
                      {month.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button onClick={handleGenerate} disabled={isLoading || !hasEmitenteCnpj} className="gap-2">
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {isLoading ? 'Gerando relatório...' : 'Gerar relatório com IA'}
          </Button>
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
            <CardTitle>Relatório executivo ({periodoDescricao})</CardTitle>
            <CardDescription>Total comprado no período: {formatCurrency(totalComprado)}</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap rounded-md border bg-muted/40 p-4 text-sm leading-6 text-foreground">
              {report}
            </pre>
          </CardContent>
        </Card>
      )}
    </section>
  );
}