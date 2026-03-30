import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, FileText, Package, ReceiptText, Truck } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useAuth } from '@/contexts/AuthContext';
import { DetalhamentoComprasNotaMode } from '@/pages/components/DetalhamentoComprasNotaMode';
import { Header } from '@/pages/components/Header';
import { StatCard } from '@/pages/components/StatCard';
import { fetchNfeKpis, fetchNfeNotasDetalhadas, parseDecimal } from '@/services/nfe';
import { fetchSpedKpis } from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

export default function DetalhamentoCompras() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [openNoteValues, setOpenNoteValues] = useState<string[]>([]);
  const [openSupplierValues, setOpenSupplierValues] = useState<string[]>([]);
  const [openNcmValues, setOpenNcmValues] = useState<string[]>([]);

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
      if (item.periodo_ano) years.add(item.periodo_ano);
    }
    return years.size ? [...years].sort((a, b) => b - a) : [new Date().getFullYear()];
  }, [yearsQuery.data]);

  useEffect(() => {
    if (!availableYears.length) return;
    if (!availableYears.includes(Number.parseInt(selectedYear, 10))) {
      setSelectedYear(String(availableYears[0]));
    }
  }, [availableYears, selectedYear]);

  const notas = useMemo(() => notasQuery.data?.notas ?? [], [notasQuery.data?.notas]);
  const totalComprado = notas.reduce((total, nota) => total + parseDecimal(nota.valor_total_nf), 0);
  const ticketMedio = notas.length ? totalComprado / notas.length : 0;
  const totalItens = notas.reduce((total, nota) => total + nota.itens.length, 0);
  const maiorNota = notas.reduce((max, nota) => Math.max(max, parseDecimal(nota.valor_total_nf)), 0);

  const noteAccordionValues = useMemo(
    () => notas.map((nota) => `${nota.numero_nf}-${nota.data_emissao}`),
    [notas],
  );
  const supplierAccordionValues = useMemo(
    () => notas.map((nota) => `fornecedor-${nota.numero_nf}-${nota.data_emissao}`),
    [notas],
  );
  const ncmAccordionValues = useMemo(
    () =>
      notas.flatMap((nota) =>
        Array.from(new Set(nota.itens.map((item) => item.ncm || 'sem-ncm'))).map(
          (ncm) => `ncm-${nota.numero_nf}-${nota.data_emissao}-${ncm}`,
        ),
      ),
    [notas],
  );

  useEffect(() => {
    setOpenNoteValues((current) => current.filter((value) => noteAccordionValues.includes(value)));
  }, [noteAccordionValues]);

  useEffect(() => {
    setOpenSupplierValues((current) => current.filter((value) => supplierAccordionValues.includes(value)));
  }, [supplierAccordionValues]);

  useEffect(() => {
    setOpenNcmValues((current) => current.filter((value) => ncmAccordionValues.includes(value)));
  }, [ncmAccordionValues]);

  const allNotesOpen =
    noteAccordionValues.length > 0 && noteAccordionValues.every((value) => openNoteValues.includes(value));
  const allSuppliersOpen =
    supplierAccordionValues.length > 0 &&
    supplierAccordionValues.every((value) => openSupplierValues.includes(value));
  const allNcmsOpen =
    ncmAccordionValues.length > 0 && ncmAccordionValues.every((value) => openNcmValues.includes(value));

  const levelButtons = [
    {
      key: 'nivel-1',
      title: 'Nota',
      isOpen: allNotesOpen,
      onClick: () => setOpenNoteValues(allNotesOpen ? [] : noteAccordionValues),
    },
    {
      key: 'nivel-2',
      title: 'Fornecedor',
      isOpen: allSuppliersOpen,
      onClick: () => {
        if (allSuppliersOpen) {
          setOpenSupplierValues([]);
          return;
        }
        setOpenNoteValues(noteAccordionValues);
        setOpenSupplierValues(supplierAccordionValues);
      },
    },
    {
      key: 'nivel-3',
      title: 'NCM',
      isOpen: allNcmsOpen,
      onClick: () => {
        if (allNcmsOpen) {
          setOpenNcmValues([]);
          return;
        }
        setOpenNoteValues(noteAccordionValues);
        setOpenSupplierValues(supplierAccordionValues);
        setOpenNcmValues(ncmAccordionValues);
      },
    },
    {
      key: 'nivel-4',
      title: 'Produto',
      isOpen: allNcmsOpen,
      onClick: () => {
        if (allNcmsOpen) {
          setOpenNcmValues([]);
          return;
        }
        setOpenNoteValues(noteAccordionValues);
        setOpenSupplierValues(supplierAccordionValues);
        setOpenNcmValues(ncmAccordionValues);
      },
    },
  ] as const;

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
      title: 'Ticket medio por nota',
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
      description: 'Produtos vinculados as compras',
      icon: Package,
      trend: 'up',
      accentClass: 'border-l-amber-400',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Maior nota',
      value: formatCurrency(maiorNota),
      description: 'Pico do periodo',
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
        subtitle="Expansao hierarquica focada somente nas compras, com leitura em camadas ate o nivel de produto."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={notasQuery.isLoading && !isSped} />
        ))}
      </div>

      <Card className="border border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]">
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <Badge className="border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">
                Drill-down hierarquico
              </Badge>
              <h2 className="text-2xl font-semibold tracking-tight">Expansao em 4 niveis</h2>
              <p className="max-w-3xl text-sm text-slate-300">
                A leitura segue a mesma estrutura do detalhamento de vendas, adaptada para mostrar apenas compras.
              </p>
            </div>
            <Button asChild variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100">
              <Link to="/analise-compras">
                Voltar ao dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {isSped && (
        <Alert>
          <AlertTitle>Detalhamento por nota ainda nao disponivel para SPED</AlertTitle>
          <AlertDescription>
            Esta versao foi conectada a estrutura detalhada de NFe/XML. Se voce quiser, eu posso preparar a mesma
            experiencia para SPED no proximo passo.
          </AlertDescription>
        </Alert>
      )}

      {!isSped && notasQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar notas detalhadas</AlertTitle>
          <AlertDescription>
            {notasQuery.error instanceof Error
              ? notasQuery.error.message
              : 'Nao foi possivel consultar as notas detalhadas deste periodo.'}
          </AlertDescription>
        </Alert>
      )}

      {!isSped && (
        <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
          <CardContent className="p-0">
            <div className="border-b border-slate-800/80 px-6 py-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {levelButtons.map((button) => (
                  <Button
                    key={button.key}
                    type="button"
                    variant="outline"
                    onClick={button.onClick}
                    className="h-auto justify-start border-slate-700 bg-slate-900/80 px-4 py-3 text-left text-slate-100 hover:border-sky-500/60 hover:bg-slate-800"
                  >
                    <span className="flex flex-col items-start gap-1">
                      <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                        {button.title}
                      </span>
                      <span className="text-sm font-medium text-slate-100">
                        {button.isOpen ? 'Fechar visualizacao detalhada' : 'Abrir visualizacao detalhada'}
                      </span>
                    </span>
                  </Button>
                ))}
              </div>
            </div>

            {notas.length ? (
              <DetalhamentoComprasNotaMode
                notas={notas}
                openNoteValues={openNoteValues}
                onOpenNoteValuesChange={setOpenNoteValues}
                openSupplierValues={openSupplierValues}
                onOpenSupplierValuesChange={setOpenSupplierValues}
                openNcmValues={openNcmValues}
                onOpenNcmValuesChange={setOpenNcmValues}
              />
            ) : (
              <div className="p-6 text-sm text-slate-300">
                Nenhuma nota de compra encontrada para o periodo selecionado.
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
