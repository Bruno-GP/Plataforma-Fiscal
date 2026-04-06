import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileBarChart2, Files, ReceiptText, Scale } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { Header } from '@/pages/components/Header';
import { RankingCard } from '@/pages/components/RankingCard';
import { StatCard } from '@/pages/components/StatCard';
import { CfopAnalysisTable } from '@/pages/components/CfopAnalysisTable';
import { NcmAnalysisTable } from '@/pages/components/NcmAnalysisTable';
import {
  fetchNfeAnaliseFiscalCfop,
  fetchNfeAnaliseFiscalNcm,
  fetchNfeKpis,
  parseDecimal,
} from '@/services/nfe';
import {
  fetchSpedAnaliseFiscalCfop,
  fetchSpedAnaliseFiscalNcm,
  fetchSpedKpis,
} from '@/services/sped';
import { formatCurrency, monthLabels } from '@/services/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

export default function AnaliseFiscalCfop() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedView, setSelectedView] = useState<'cfop' | 'ncm'>('cfop');

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);
  const isSped = Boolean(user?.tem_sped);

  const yearsQuery = useQuery({
    queryKey: ['analise-fiscal-anos', emitenteCnpj, isSped],
    queryFn: () =>
      isSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const fiscalCfopQuery = useQuery({
    queryKey: ['analise-fiscal-cfop', emitenteCnpj, isSped, yearNumber, selectedMonth],
    queryFn: () =>
      isSped
        ? fetchSpedAnaliseFiscalCfop({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 100000,
          })
        : fetchNfeAnaliseFiscalCfop({
            emitente_cnpj: emitenteCnpj,
            email: user?.email,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 100000,
          }),
    enabled: hasEmitenteCnpj && selectedView === 'cfop',
    staleTime: 5 * 60 * 1000,
  });

  const fiscalNcmQuery = useQuery({
    queryKey: ['analise-fiscal-ncm', emitenteCnpj, isSped, yearNumber, selectedMonth],
    queryFn: () =>
      isSped
        ? fetchSpedAnaliseFiscalNcm({
            emitente_cnpj: emitenteCnpj,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 100000,
          })
        : fetchNfeAnaliseFiscalNcm({
            emitente_cnpj: emitenteCnpj,
            email: user?.email,
            periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
            periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
            limite: 100000,
          }),
    enabled: hasEmitenteCnpj && selectedView === 'ncm',
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

  const totalMovimentadoCfop = parseDecimal(fiscalCfopQuery.data?.total_movimentado ?? 0);
  const quantidadeDocumentosCfop = fiscalCfopQuery.data?.quantidade_documentos ?? 0;
  const quantidadeCfops = fiscalCfopQuery.data?.quantidade_cfops ?? 0;
  const categoriasAtivas = (fiscalCfopQuery.data?.top_categorias ?? []).length;

  const cfopStats = [
    {
      title: 'Total movimentado',
      value: formatCurrency(totalMovimentadoCfop),
      description: 'Somatorio fiscal do periodo',
      icon: Scale,
      trend: 'up' as const,
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Documentos fiscais',
      value: quantidadeDocumentosCfop.toString(),
      description: 'Documentos com itens e CFOP',
      icon: Files,
      trend: 'up' as const,
      accentClass: 'border-l-emerald-500',
    },
    {
      title: 'CFOPs distintos',
      value: quantidadeCfops.toString(),
      description: 'Variedade de operacoes no periodo',
      icon: ReceiptText,
      trend: 'up' as const,
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Categorias ativas',
      value: categoriasAtivas.toString(),
      description: 'Grupos fiscais identificados',
      icon: FileBarChart2,
      trend: 'up' as const,
      accentClass: 'border-l-violet-500',
    },
  ];

  const categoriaItems = (fiscalCfopQuery.data?.top_categorias ?? []).map((categoria, index) => {
    const valorTotal = parseDecimal(categoria.valor_total ?? 0);
    const percentual = parseDecimal(categoria.participacao_percentual ?? 0);

    return {
      key: `${categoria.categoria}-${index}`,
      title: categoria.categoria,
      subtitle: `${categoria.quantidade_documentos} documentos`,
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

  const cfopItems = (fiscalCfopQuery.data?.top_cfops ?? []).map((cfop, index) => ({
    key: `${cfop.cfop}-${index}`,
    cfop: cfop.cfop || '0000',
    descricao: cfop.descricao || 'CFOP sem descricao',
    valorTotal: parseDecimal(cfop.valor_total ?? 0),
    participacao: parseDecimal(cfop.participacao_percentual ?? 0),
  }));

  const totalMovimentadoNcm = parseDecimal(fiscalNcmQuery.data?.total_movimentado ?? 0);
  const quantidadeDocumentosNcm = fiscalNcmQuery.data?.quantidade_documentos ?? 0;
  const quantidadeNcms = fiscalNcmQuery.data?.quantidade_ncms ?? 0;

  const ncmStats = [
    {
      title: 'Total movimentado',
      value: formatCurrency(totalMovimentadoNcm),
      description: 'Somatorio fiscal do periodo',
      icon: Scale,
      trend: 'up' as const,
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Documentos fiscais',
      value: quantidadeDocumentosNcm.toString(),
      description: 'Documentos com itens classificados',
      icon: Files,
      trend: 'up' as const,
      accentClass: 'border-l-emerald-500',
    },
    {
      title: 'NCMs distintos',
      value: quantidadeNcms.toString(),
      description: 'Classificacoes fiscais no periodo',
      icon: ReceiptText,
      trend: 'up' as const,
      accentClass: 'border-l-amber-400',
    },
    {
      title: 'Ticket medio por NCM',
      value: formatCurrency(quantidadeNcms ? totalMovimentadoNcm / quantidadeNcms : 0),
      description: 'Media de valor por classificacao',
      icon: FileBarChart2,
      trend: 'up' as const,
      accentClass: 'border-l-violet-500',
    },
  ];

  const ncmItems = (fiscalNcmQuery.data?.top_ncms ?? []).map((ncm, index) => ({
    key: `${ncm.ncm}-${index}`,
    ncm: ncm.ncm || '00000000',
    descricao: ncm.descricao || 'NCM sem descricao',
    valorTotal: parseDecimal(ncm.valor_total ?? 0),
    participacao: parseDecimal(ncm.participacao_percentual ?? 0),
  }));

  const viewTitle =
    selectedView === 'cfop' ? 'Analise Fiscal por CFOP' : 'Analise Fiscal por NCM';
  const viewSubtitle =
    selectedView === 'cfop'
      ? 'Visao ampla das operacoes fiscais autorizadas do periodo'
      : 'Visao consolidada por classificacao fiscal dos produtos no periodo';

  return (
    <div className="space-y-6 py-6">
      <Header
        title={viewTitle}
        subtitle={viewSubtitle}
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          variant={selectedView === 'cfop' ? 'default' : 'outline'}
          onClick={() => setSelectedView('cfop')}
        >
          Analise Fiscal por CFOP
        </Button>
        <Button
          type="button"
          variant={selectedView === 'ncm' ? 'default' : 'outline'}
          onClick={() => setSelectedView('ncm')}
        >
          Analise Fiscal por NCM
        </Button>
      </div>

      {selectedView === 'cfop' ? (
        <>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {cfopStats.map((stat) => (
              <StatCard key={stat.title} {...stat} isLoading={fiscalCfopQuery.isLoading} />
            ))}
          </div>

          <RankingCard
            title="Categorias fiscais"
            description="Distribuicao das principais naturezas de operacao no periodo"
            items={categoriaItems}
            isLoading={fiscalCfopQuery.isLoading}
            loadingMessage="Carregando categorias fiscais..."
            emptyMessage="Nenhuma categoria fiscal encontrada."
            totalValue={formatCurrency(totalMovimentadoCfop)}
            showAbcReport={false}
            showAbcClassification={false}
          />

          <CfopAnalysisTable
            items={cfopItems}
            isLoading={fiscalCfopQuery.isLoading}
            isError={fiscalCfopQuery.isError}
            formatCurrency={formatCurrency}
            title="Todos os CFOPs com valor"
            description="CFOPs ordenados por impacto no periodo, com uma faixa maior de registros para evitar divergencias ao conferir as somas."
            emptyMessage="Nenhum CFOP fiscal encontrado para o periodo selecionado."
          />
        </>
      ) : (
        <>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {ncmStats.map((stat) => (
              <StatCard key={stat.title} {...stat} isLoading={fiscalNcmQuery.isLoading} />
            ))}
          </div>

          <NcmAnalysisTable
            items={ncmItems}
            isLoading={fiscalNcmQuery.isLoading}
            isError={fiscalNcmQuery.isError}
            formatCurrency={formatCurrency}
            title="Todos os NCMs com valor"
            description="Classificacoes fiscais ordenadas por impacto no periodo para facilitar uma primeira leitura da carteira."
            emptyMessage="Nenhum NCM fiscal encontrado para o periodo selecionado."
          />
        </>
      )}
    </div>
  );
}
