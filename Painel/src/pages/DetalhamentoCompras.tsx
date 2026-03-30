import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, FileText, Package, ReceiptText, Truck } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAuth } from '@/contexts/AuthContext';
import { Header } from '@/pages/components/Header';
import { StatCard } from '@/pages/components/StatCard';
import { fetchNfeKpis, fetchNfeNotasDetalhadas, parseDecimal } from '@/services/nfe';
import { fetchSpedKpis } from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(new Date(value));

export default function DetalhamentoCompras() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);
  const isSped = Boolean(user?.tem_sped);

  const yearsQuery = useQuery({
    queryKey: ['detalhamento-compras-anos', emitenteCnpj, isSped],
    queryFn: () =>
      isSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const notasQuery = useQuery({
    queryKey: ['detalhamento-compras-notas', emitenteCnpj, selectedYear, selectedMonth],
    queryFn: () =>
      fetchNfeNotasDetalhadas({
        emitente_cnpj: emitenteCnpj,
        email: user?.email,
        periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
        periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
        tipo_operacao: 'compras',
        limite: 100,
      }),
    enabled: hasEmitenteCnpj && !isSped,
    staleTime: 5 * 60 * 1000,
  });

  const availableYears = useMemo(() => {
    const years = new Set<number>();
    for (const item of yearsQuery.data?.resultados ?? []) {
      if (item.periodo_ano) {
        years.add(item.periodo_ano);
      }
    }
    return years.size ? [...years].sort((a, b) => b - a) : [new Date().getFullYear()];
  }, [yearsQuery.data]);

  useEffect(() => {
    if (!availableYears.length) {
      return;
    }

    if (!availableYears.includes(Number.parseInt(selectedYear, 10))) {
      setSelectedYear(String(availableYears[0]));
    }
  }, [availableYears, selectedYear]);

  const notas = notasQuery.data?.notas ?? [];
  const totalComprado = notas.reduce((total, nota) => total + parseDecimal(nota.valor_total_nf), 0);
  const ticketMedio = notas.length ? totalComprado / notas.length : 0;
  const totalItens = notas.reduce((total, nota) => total + nota.itens.length, 0);
  const maiorNota = notas.reduce((max, nota) => Math.max(max, parseDecimal(nota.valor_total_nf)), 0);

  const stats = [
    {
      title: 'Compras detalhadas',
      value: formatCurrency(totalComprado),
      description: `${notas.length} notas no recorte`,
      icon: ReceiptText,
      trend: 'up',
      accentClass: 'border-l-sky-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Ticket médio por nota',
      value: formatCurrency(ticketMedio),
      description: 'Leitura nota a nota',
      icon: FileText,
      trend: 'up',
      accentClass: 'border-l-emerald-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Itens mapeados',
      value: String(totalItens),
      description: 'Produtos vinculados às notas',
      icon: Package,
      trend: 'up',
      accentClass: 'border-l-amber-400',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Maior nota',
      value: formatCurrency(maiorNota),
      description: 'Pico do período',
      icon: Truck,
      trend: 'up',
      accentClass: 'border-l-violet-500',
      appendPreviousMonthLabel: false,
    },
  ] as const;

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Detalhamento de compras"
        subtitle="Expansão por nota com abertura progressiva para operação, produtos e dados fiscais."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <Card className="border-0 bg-gradient-to-r from-emerald-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]">
        <CardContent className="flex flex-col gap-4 p-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <Badge className="border border-white/15 bg-white/10 text-white hover:bg-white/10">
              Drill-down por nota
            </Badge>
            <h2 className="text-2xl font-semibold tracking-tight">Linha principal simples, abertura progressiva</h2>
            <p className="max-w-3xl text-sm text-slate-300">
              A leitura principal começa por `Nota + valor total` e a expansão distribui operação, produtos e bloco
              fiscal em camadas mais claras.
            </p>
          </div>
          <Button asChild variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100">
            <Link to="/analise-compras">
              Voltar ao dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      {isSped && (
        <Alert>
          <AlertTitle>Detalhamento por nota ainda não disponível para SPED</AlertTitle>
          <AlertDescription>
            Esta versão foi conectada à estrutura detalhada de NFe/XML. Se você quiser, eu posso preparar a mesma
            experiência para SPED no próximo passo.
          </AlertDescription>
        </Alert>
      )}

      {!isSped && notasQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar notas detalhadas</AlertTitle>
          <AlertDescription>
            {notasQuery.error instanceof Error
              ? notasQuery.error.message
              : 'Não foi possível consultar as notas detalhadas deste período.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={notasQuery.isLoading && !isSped} />
        ))}
      </div>

      {!isSped && (
        <Card className="overflow-hidden border-0 bg-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
          <CardHeader className="border-b bg-slate-50/80">
            <CardTitle className="text-xl">Notas do período</CardTitle>
            <CardDescription>
              Cada linha começa com o número da nota e o valor total. Ao abrir, você vê dados operacionais, produtos e
              informações fiscais.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {notas.length ? (
              <Accordion type="single" collapsible className="w-full">
                {notas.map((nota) => (
                  <AccordionItem key={`${nota.numero_nf}-${nota.data_emissao}`} value={`${nota.numero_nf}-${nota.data_emissao}`}>
                    <AccordionTrigger className="px-6 py-5 hover:no-underline">
                      <div className="grid w-full gap-3 text-left md:grid-cols-[1.2fr_1fr_1fr_1fr] md:items-center">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Nota</p>
                          <p className="text-base font-semibold text-slate-950">{nota.numero_nf}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Valor total</p>
                          <p className="text-base font-semibold text-slate-950">{formatCurrency(parseDecimal(nota.valor_total_nf))}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Emissão</p>
                          <p className="text-sm text-slate-600">{formatDate(nota.data_emissao)}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Itens</p>
                          <p className="text-sm text-slate-600">{nota.itens.length} produto(s)</p>
                        </div>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="px-6 pb-6">
                      <div className="grid gap-4 xl:grid-cols-[1.1fr_1.6fr_1.3fr]">
                        <Card className="border-slate-200 bg-slate-50/70 shadow-none">
                          <CardHeader className="pb-3">
                            <CardTitle className="text-base">Operação</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-2 text-sm">
                            <p className="font-medium text-slate-950">{nota.natureza_operacao || 'Natureza não informada'}</p>
                            <p className="text-slate-500">Modelo: {nota.modelo || 'Não informado'}</p>
                            <p className="text-slate-500">Emitente CNPJ: {nota.emitente_cnpj || 'Não informado'}</p>
                            <p className="text-slate-500">
                              Destinatário: {nota.destinatario_nome || 'Não informado'}
                            </p>
                          </CardContent>
                        </Card>

                        <Card className="border-slate-200 bg-slate-50/70 shadow-none">
                          <CardHeader className="pb-3">
                            <CardTitle className="text-base">Produtos</CardTitle>
                          </CardHeader>
                          <CardContent className="p-0">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Produto</TableHead>
                                  <TableHead>Qtd.</TableHead>
                                  <TableHead className="text-right">Valor</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {nota.itens.map((item) => (
                                  <TableRow key={`${nota.numero_nf}-${item.item_numero}`}>
                                    <TableCell>
                                      <div>
                                        <p className="font-medium text-slate-950">{item.descricao || 'Item sem descrição'}</p>
                                        <p className="text-xs text-slate-500">CFOP {item.cfop || '-'}</p>
                                      </div>
                                    </TableCell>
                                    <TableCell>{parseDecimal(item.quantidade).toFixed(2)}</TableCell>
                                    <TableCell className="text-right font-medium">
                                      {formatCurrency(parseDecimal(item.valor_total))}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </CardContent>
                        </Card>

                        <Card className="border-slate-200 bg-slate-50/70 shadow-none">
                          <CardHeader className="pb-3">
                            <CardTitle className="text-base">Fiscal</CardTitle>
                          </CardHeader>
                          <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                            <div className="rounded-xl border bg-white p-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">ICMS</p>
                              <p className="mt-1 text-sm font-semibold text-slate-950">
                                {formatCurrency(parseDecimal(nota.valor_icms))}
                              </p>
                            </div>
                            <div className="rounded-xl border bg-white p-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">IPI</p>
                              <p className="mt-1 text-sm font-semibold text-slate-950">
                                {formatCurrency(parseDecimal(nota.valor_ipi))}
                              </p>
                            </div>
                            <div className="rounded-xl border bg-white p-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">PIS</p>
                              <p className="mt-1 text-sm font-semibold text-slate-950">
                                {formatCurrency(parseDecimal(nota.valor_pis))}
                              </p>
                            </div>
                            <div className="rounded-xl border bg-white p-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">COFINS</p>
                              <p className="mt-1 text-sm font-semibold text-slate-950">
                                {formatCurrency(parseDecimal(nota.valor_cofins))}
                              </p>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            ) : (
              <div className="p-6 text-sm text-slate-500">Nenhuma nota de compra encontrada para o período selecionado.</div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
