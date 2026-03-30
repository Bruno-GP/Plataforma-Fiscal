import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Percent, TrendingDown, TrendingUp, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAuth } from '@/contexts/AuthContext';
import { Header } from '@/pages/components/Header';
import { StatCard } from '@/pages/components/StatCard';
import {
  fetchNfeDashboardVendas,
  fetchNfeKpis,
  fetchNfeNotasDetalhadas,
  parseDecimal,
} from '@/services/nfe';
import { fetchSpedDashboardVendas, fetchSpedKpis } from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

const NCM_CHAPTER_DESCRIPTIONS: Record<string, string> = {
  '01': 'Animais vivos',
  '02': 'Carnes e miudezas comestiveis',
  '03': 'Peixes, crustaceos e moluscos',
  '04': 'Leite, laticinios, ovos e mel',
  '05': 'Produtos de origem animal diversos',
  '06': 'Plantas vivas e floricultura',
  '07': 'Hortalicas, legumes e tuberculos',
  '08': 'Frutas, cascas de citricos e melao',
  '09': 'Cafe, cha, mate e especiarias',
  '10': 'Cereais',
  '11': 'Produtos da moagem e amidos',
  '12': 'Sementes, frutos oleaginosos e graos',
  '13': 'Gomas, resinas e extratos vegetais',
  '14': 'Materias vegetais para trancaria',
  '15': 'Gorduras, oleos e ceras',
  '16': 'Preparacoes de carne, peixes e afins',
  '17': 'Acucares e produtos de confeitaria',
  '18': 'Cacau e suas preparacoes',
  '19': 'Preparacoes de cereais e panificacao',
  '20': 'Preparacoes de vegetais e frutas',
  '21': 'Preparacoes alimenticias diversas',
  '22': 'Bebidas, liquidos alcoolicos e vinagres',
  '23': 'Residuos para alimentacao animal',
  '24': 'Tabaco e sucedaneos',
  '25': 'Sal, enxofre, terras e pedras',
  '26': 'Minerios, escorias e cinzas',
  '27': 'Combustiveis minerais e oleos',
  '28': 'Produtos quimicos inorganicos',
  '29': 'Produtos quimicos organicos',
  '30': 'Produtos farmaceuticos',
  '31': 'Adubos e fertilizantes',
  '32': 'Extratos tanantes, tintas e pigmentos',
  '33': 'Oleos essenciais e cosmeticos',
  '34': 'Saboes, detergentes e ceras',
  '35': 'Materias albuminoides e colas',
  '36': 'Explosivos e artigos de pirotecnia',
  '37': 'Produtos fotograficos e cinematograficos',
  '38': 'Produtos quimicos diversos',
  '39': 'Plasticos e suas obras',
  '40': 'Borracha e suas obras',
  '41': 'Peles e couros',
  '42': 'Artefatos de couro, bolsas e malas',
  '43': 'Peles com pelo e artefatos',
  '44': 'Madeira, carvao vegetal e obras',
  '45': 'Cortica e suas obras',
  '46': 'Obras de espartaria e cestaria',
  '47': 'Pastas de madeira e papel reciclado',
  '48': 'Papel, cartao e artefatos',
  '49': 'Livros, impressos e reproducoes graficas',
  '50': 'Seda',
  '51': 'La e pelos finos ou grosseiros',
  '52': 'Algodao',
  '53': 'Outras fibras texteis vegetais',
  '54': 'Filamentos sinteticos ou artificiais',
  '55': 'Fibras sinteticas ou artificiais',
  '56': 'Pastas, feltros e falsos tecidos',
  '57': 'Tapetes e revestimentos texteis',
  '58': 'Tecidos especiais e rendas',
  '59': 'Tecidos impregnados e usos tecnicos',
  '60': 'Tecidos de malha',
  '61': 'Vestuarios e acessorios de malha',
  '62': 'Vestuarios e acessorios de tecido',
  '63': 'Artefatos texteis confeccionados',
  '64': 'Calcados e artefatos semelhantes',
  '65': 'Chapeus, bone e artefatos',
  '66': 'Guarda-chuvas, bengalas e chicotes',
  '67': 'Penas preparadas e flores artificiais',
  '68': 'Obras de pedra, gesso, cimento e mica',
  '69': 'Produtos ceramicos',
  '70': 'Vidro e suas obras',
  '71': 'Perolas e metais preciosos',
  '72': 'Ferro fundido, ferro e aco',
  '73': 'Obras de ferro fundido, ferro e aco',
  '74': 'Cobre e suas obras',
  '75': 'Niquel e suas obras',
  '76': 'Aluminio e suas obras',
  '78': 'Chumbo e suas obras',
  '79': 'Zinco e suas obras',
  '80': 'Estanho e suas obras',
  '81': 'Outros metais comuns e obras',
  '82': 'Ferramentas e cutelaria',
  '83': 'Obras diversas de metais comuns',
  '84': 'Maquinas, aparelhos mecanicos e pecas',
  '85': 'Maquinas e aparelhos eletricos',
  '86': 'Material ferroviario e vias ferreas',
  '87': 'Veiculos automoveis e pecas',
  '88': 'Aeronaves e aparelhos espaciais',
  '89': 'Embarcacoes e estruturas flutuantes',
  '90': 'Instrumentos de precisao e medicos',
  '91': 'Relogios e aparelhos de relojoaria',
  '92': 'Instrumentos musicais',
  '93': 'Armas e municoes',
  '94': 'Moveis, iluminacao e pre-fabricados',
  '95': 'Brinquedos, jogos e artigos esportivos',
  '96': 'Obras diversas',
  '97': 'Objetos de arte e colecoes',
};

const getRegionByUf = (uf: string) => {
  const regions: Record<string, string> = {
    AC: 'Norte',
    AL: 'Nordeste',
    AP: 'Norte',
    AM: 'Norte',
    BA: 'Nordeste',
    CE: 'Nordeste',
    DF: 'Centro-Oeste',
    ES: 'Sudeste',
    GO: 'Centro-Oeste',
    MA: 'Nordeste',
    MG: 'Sudeste',
    MS: 'Centro-Oeste',
    MT: 'Centro-Oeste',
    PA: 'Norte',
    PB: 'Nordeste',
    PE: 'Nordeste',
    PI: 'Nordeste',
    PR: 'Sul',
    RJ: 'Sudeste',
    RN: 'Nordeste',
    RO: 'Norte',
    RR: 'Norte',
    RS: 'Sul',
    SC: 'Sul',
    SE: 'Nordeste',
    SP: 'Sudeste',
    TO: 'Norte',
  };

  return regions[uf.trim().toUpperCase()] ?? 'Não definida';
};

const abbreviateNcmDescription = (ncm: string, descricaoNcm?: string | null) => {
  const officialDescription = (descricaoNcm ?? '').trim();
  if (officialDescription) {
    return officialDescription;
  }

  const digits = ncm.replace(/\D/g, '');
  if (!digits) {
    return 'Classificação fiscal abreviada';
  }

  const chapterDescription = NCM_CHAPTER_DESCRIPTIONS[digits.slice(0, 2)] ?? 'Classificação fiscal abreviada';
  const maxLength = Math.max(18, Math.floor(chapterDescription.length * 0.7));

  if (chapterDescription.length <= maxLength) {
    return chapterDescription;
  }

  return `${chapterDescription.slice(0, maxLength).trim()}...`;
};

const hierarchyLabelClass =
  'text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400';

export default function DetalhamentoVendas() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [openNoteValues, setOpenNoteValues] = useState<string[]>([]);
  const [openClientValues, setOpenClientValues] = useState<string[]>([]);
  const [openNcmValues, setOpenNcmValues] = useState<string[]>([]);

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);
  const isSped = Boolean(user?.tem_sped);

  const yearsQuery = useQuery({
    queryKey: ['detalhamento-vendas-anos', emitenteCnpj, isSped],
    queryFn: () =>
      isSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const dashboardQuery = useQuery({
    queryKey: ['detalhamento-vendas-dashboard', emitenteCnpj, isSped, yearNumber, selectedMonth],
    queryFn: () =>
      isSped
        ? fetchSpedDashboardVendas({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          })
        : fetchNfeDashboardVendas({
            emitente_cnpj: emitenteCnpj,
            email: user?.email,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 5,
          }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const notasQuery = useQuery({
    queryKey: ['detalhamento-vendas-notas', emitenteCnpj, selectedYear, selectedMonth],
    queryFn: () =>
      fetchNfeNotasDetalhadas({
        emitente_cnpj: emitenteCnpj,
        email: user?.email,
        periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
        periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
        tipo_operacao: 'vendas',
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

  const currentData = dashboardQuery.data?.resumo_atual;
  const previousData = dashboardQuery.data?.resumo_anterior;
  const totalFaturamento = parseDecimal(currentData?.total_vendido ?? 0);

  const totalSalesChange = parseDecimal(previousData?.total_vendido ?? 0)
    ? ((totalFaturamento - parseDecimal(previousData?.total_vendido ?? 0)) /
        parseDecimal(previousData?.total_vendido ?? 0)) *
      100
    : 0;
  const ticketChange = parseDecimal(previousData?.ticket_medio ?? 0)
    ? ((parseDecimal(currentData?.ticket_medio ?? 0) - parseDecimal(previousData?.ticket_medio ?? 0)) /
        parseDecimal(previousData?.ticket_medio ?? 0)) *
      100
    : 0;
  const totalTaxesChange = parseDecimal(previousData?.total_impostos ?? 0)
    ? ((parseDecimal(currentData?.total_impostos ?? 0) - parseDecimal(previousData?.total_impostos ?? 0)) /
        parseDecimal(previousData?.total_impostos ?? 0)) *
      100
    : 0;

  const stats = [
    {
      title: `Faturamento Mensal${selectedYear ? ` (Período ${selectedYear})` : ''}`,
      value: formatCurrency(totalFaturamento),
      description: formatPercent(totalSalesChange),
      icon: TrendingUp,
      trend: totalSalesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Comparativo anual',
      value: `${totalSalesChange >= 0 ? '+' : ''}${totalSalesChange.toFixed(1)}%`,
      description: selectedMonth === 'all' ? `vs. mesmo período de ${yearNumber - 1}` : 'vs. período anterior',
      icon: totalSalesChange >= 0 ? TrendingUp : TrendingDown,
      trend: totalSalesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-emerald-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Ticket Médio',
      value: formatCurrency(parseDecimal(currentData?.ticket_medio ?? 0)),
      description: formatPercent(ticketChange),
      icon: Users,
      trend: ticketChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Impostos sobre vendas',
      value: formatCurrency(parseDecimal(currentData?.total_impostos ?? 0)),
      description: formatPercent(totalTaxesChange),
      icon: Percent,
      trend: totalTaxesChange >= 0 ? 'up' : 'down',
      accentClass: 'border-l-violet-500',
    },
  ] as const;

  const notas = useMemo(() => notasQuery.data?.notas ?? [], [notasQuery.data?.notas]);

  const noteAccordionValues = useMemo(
    () => notas.map((nota) => `${nota.numero_nf}-${nota.data_emissao}`),
    [notas],
  );

  const clientAccordionValues = useMemo(
    () => notas.map((nota) => `cliente-${nota.numero_nf}-${nota.data_emissao}`),
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
    setOpenClientValues((current) => current.filter((value) => clientAccordionValues.includes(value)));
  }, [clientAccordionValues]);

  useEffect(() => {
    setOpenNcmValues((current) => current.filter((value) => ncmAccordionValues.includes(value)));
  }, [ncmAccordionValues]);

  const allNotesOpen =
    noteAccordionValues.length > 0 && noteAccordionValues.every((value) => openNoteValues.includes(value));
  const allClientsOpen =
    clientAccordionValues.length > 0 && clientAccordionValues.every((value) => openClientValues.includes(value));
  const allNcmsOpen =
    ncmAccordionValues.length > 0 && ncmAccordionValues.every((value) => openNcmValues.includes(value));

  const toggleLevelOne = () => {
    setOpenNoteValues(allNotesOpen ? [] : noteAccordionValues);
  };

  const toggleLevelTwo = () => {
    if (allClientsOpen) {
      setOpenClientValues([]);
      return;
    }

    setOpenNoteValues(noteAccordionValues);
    setOpenClientValues(clientAccordionValues);
  };

  const toggleLevelThree = () => {
    if (allNcmsOpen) {
      setOpenNcmValues([]);
      return;
    }

    setOpenNoteValues(noteAccordionValues);
    setOpenClientValues(clientAccordionValues);
    setOpenNcmValues(ncmAccordionValues);
  };

  const toggleLevelFour = () => {
    if (allNcmsOpen) {
      setOpenNcmValues([]);
      return;
    }

    setOpenNoteValues(noteAccordionValues);
    setOpenClientValues(clientAccordionValues);
    setOpenNcmValues(ncmAccordionValues);
  };

  const levelButtons = [
    {
      key: 'nivel-1',
      title: 'Nível 1',
      isOpen: allNotesOpen,
      onClick: toggleLevelOne,
    },
    {
      key: 'nivel-2',
      title: 'Nível 2',
      isOpen: allClientsOpen,
      onClick: toggleLevelTwo,
    },
    {
      key: 'nivel-3',
      title: 'Nível 3',
      isOpen: allNcmsOpen,
      onClick: toggleLevelThree,
    },
    {
      key: 'nivel-4',
      title: 'Nível 4',
      isOpen: allNcmsOpen,
      onClick: toggleLevelFour,
    },
  ] as const;

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Detalhamento de vendas"
        subtitle="Expansão hierárquica por nota, cliente, NCM e produtos com visual alinhado à paleta azul-marinho."
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={dashboardQuery.isLoading} />
        ))}
      </div>

      <Card className="border border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]">
        <CardContent className="flex flex-col gap-4 p-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <Badge className="border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">
              Drill-down hierárquico
            </Badge>
            <h2 className="text-2xl font-semibold tracking-tight">Expansão em 4 níveis</h2>
            <p className="max-w-3xl text-sm text-slate-300">
              Clique na primeira linha para abrir a segunda, depois a terceira e por fim a quarta, sempre dentro da
              mesma nota.
            </p>
          </div>
          <Button asChild variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100">
            <Link to="/analise-vendas">
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
                        {button.isOpen ? 'Fechar visualização detalhada' : 'Abrir visualização detalhada'}
                      </span>
                    </span>
                  </Button>
                ))}
              </div>
            </div>

            {notas.length ? (
              <Accordion
                type="multiple"
                value={openNoteValues}
                onValueChange={setOpenNoteValues}
                className="w-full"
              >
                {notas.map((nota) => {
                  const notaValue = `${nota.numero_nf}-${nota.data_emissao}`;
                  const clientValue = `cliente-${nota.numero_nf}-${nota.data_emissao}`;
                  const noteTotal = parseDecimal(nota.valor_total_nf);
                  const itemBaseTotal = nota.itens.reduce((total, item) => total + parseDecimal(item.valor_total), 0);

                  const ncmGroups = Array.from(
                    nota.itens.reduce((map, item) => {
                      const key = item.ncm || 'sem-ncm';
                      const current = map.get(key) ?? {
                        ncm: item.ncm || '-',
                        descricaoNcm: '',
                        total: 0,
                      };
                      const descricaoNcm = abbreviateNcmDescription(item.ncm || '', item.descricao_ncm);
                      if (descricaoNcm.length > current.descricaoNcm.length) {
                        current.descricaoNcm = descricaoNcm;
                      }
                      current.total += parseDecimal(item.valor_total);
                      map.set(key, current);
                      return map;
                    }, new Map<string, { ncm: string; descricaoNcm: string; total: number }>()),
                  ).map(([, value]) => value);

                  return (
                    <AccordionItem
                      key={notaValue}
                      value={notaValue}
                      className="border-b border-slate-800/80"
                    >
                      <AccordionTrigger className="px-6 py-5 hover:no-underline">
                        <div className="grid w-full gap-3 text-left md:grid-cols-[1fr_1fr] md:items-center">
                          <div>
                            <p className={hierarchyLabelClass}>Nota</p>
                            <p className="text-base font-semibold text-white">{nota.numero_nf}</p>
                          </div>
                          <div>
                            <p className={hierarchyLabelClass}>Valor total da nota</p>
                            <p className="text-base font-semibold text-white">{formatCurrency(noteTotal)}</p>
                          </div>
                        </div>
                      </AccordionTrigger>

                      <AccordionContent className="px-6 pb-6">
                        <Accordion
                          type="multiple"
                          value={openClientValues}
                          onValueChange={setOpenClientValues}
                          className="w-full"
                        >
                          <AccordionItem value={clientValue} className="border border-slate-800 rounded-2xl bg-slate-900/75 px-4">
                            <AccordionTrigger className="py-4 hover:no-underline">
                              <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-4">
                                <div>
                                  <p className={hierarchyLabelClass}>Nome do cliente</p>
                                  <p className="mt-1 text-sm font-medium text-slate-100">
                                    {nota.destinatario_nome || 'Cliente não identificado'}
                                  </p>
                                </div>
                                <div>
                                  <p className={hierarchyLabelClass}>CPF/CNPJ</p>
                                  <p className="mt-1 text-sm text-slate-300">{nota.destinatario_documento || 'Não informado'}</p>
                                </div>
                                <div>
                                  <p className={hierarchyLabelClass}>Região</p>
                                  <p className="mt-1 text-sm text-slate-300">{getRegionByUf(nota.destinatario_uf || '')}</p>
                                </div>
                                <div>
                                  <p className={hierarchyLabelClass}>Cidade</p>
                                  <p className="mt-1 text-sm text-slate-300">
                                    {nota.destinatario_cidade || 'Não informada'}
                                    {nota.destinatario_uf ? ` - ${nota.destinatario_uf}` : ''}
                                  </p>
                                </div>
                              </div>
                            </AccordionTrigger>

                            <AccordionContent className="pb-4">
                              <Accordion
                                type="multiple"
                                value={openNcmValues}
                                onValueChange={setOpenNcmValues}
                                className="w-full"
                              >
                                {ncmGroups.map((group) => (
                                  <AccordionItem
                                    key={`ncm-${nota.numero_nf}-${nota.data_emissao}-${group.ncm}`}
                                    value={`ncm-${nota.numero_nf}-${nota.data_emissao}-${group.ncm}`}
                                    className="mt-3 rounded-2xl border border-slate-800 bg-slate-950/80 px-4"
                                  >
                                    <AccordionTrigger className="py-4 hover:no-underline">
                                      <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-[minmax(0,1fr)_220px] md:items-start">
                                        <div className="min-w-0">
                                          <p className={hierarchyLabelClass}>NCM</p>
                                          <p className="mt-1 pr-4 text-sm font-medium leading-relaxed text-slate-100 whitespace-normal break-words">
                                            {group.ncm} - {group.descricaoNcm}
                                          </p>
                                        </div>
                                        <div>
                                          <p className={hierarchyLabelClass}>Valor total</p>
                                          <p className="mt-1 text-sm font-medium text-slate-100">
                                            {formatCurrency(group.total)}
                                          </p>
                                        </div>
                                      </div>
                                    </AccordionTrigger>

                                    <AccordionContent className="pb-4">
                                      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/85">
                                        <Table>
                                          <TableHeader>
                                            <TableRow className="border-slate-800 bg-slate-950/80 hover:bg-slate-950/80">
                                              <TableHead className="text-slate-300">Cod do produto</TableHead>
                                              <TableHead className="text-slate-300">Nome do produto</TableHead>
                                              <TableHead className="text-slate-300">QTD vendida</TableHead>
                                              <TableHead className="text-right text-slate-300">Valor total</TableHead>
                                              <TableHead className="text-right text-slate-300">ICMS</TableHead>
                                              <TableHead className="text-right text-slate-300">IPI</TableHead>
                                              <TableHead className="text-right text-slate-300">PIS</TableHead>
                                              <TableHead className="text-right text-slate-300">Cofins</TableHead>
                                            </TableRow>
                                          </TableHeader>
                                          <TableBody>
                                            {nota.itens
                                              .filter((item) => (item.ncm || '-') === group.ncm)
                                              .map((item) => {
                                                const itemTotal = parseDecimal(item.valor_total);
                                                const proportion = itemBaseTotal > 0 ? itemTotal / itemBaseTotal : 0;

                                                return (
                                                  <TableRow
                                                    key={`${nota.numero_nf}-${group.ncm}-${item.item_numero}`}
                                                    className="border-slate-800 hover:bg-slate-800/55"
                                                  >
                                                    <TableCell className="font-medium text-slate-100">
                                                      {item.produto_codigo || '-'}
                                                    </TableCell>
                                                    <TableCell className="text-slate-200">
                                                      {item.descricao || 'Produto não identificado'}
                                                    </TableCell>
                                                    <TableCell className="text-slate-300">
                                                      {parseDecimal(item.quantidade).toFixed(2)}
                                                    </TableCell>
                                                    <TableCell className="text-right font-medium text-slate-100">
                                                      {formatCurrency(itemTotal)}
                                                    </TableCell>
                                                    <TableCell className="text-right text-slate-300">
                                                      {formatCurrency(parseDecimal(nota.valor_icms) * proportion)}
                                                    </TableCell>
                                                    <TableCell className="text-right text-slate-300">
                                                      {formatCurrency(parseDecimal(nota.valor_ipi) * proportion)}
                                                    </TableCell>
                                                    <TableCell className="text-right text-slate-300">
                                                      {formatCurrency(parseDecimal(nota.valor_pis) * proportion)}
                                                    </TableCell>
                                                    <TableCell className="text-right text-slate-300">
                                                      {formatCurrency(parseDecimal(nota.valor_cofins) * proportion)}
                                                    </TableCell>
                                                  </TableRow>
                                                );
                                              })}
                                          </TableBody>
                                        </Table>
                                      </div>
                                    </AccordionContent>
                                  </AccordionItem>
                                ))}
                              </Accordion>
                            </AccordionContent>
                          </AccordionItem>
                        </Accordion>
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            ) : (
              <div className="p-6 text-sm text-slate-300">
                Nenhuma nota de venda encontrada para o período selecionado.
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
