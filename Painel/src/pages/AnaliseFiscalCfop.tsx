import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileBarChart2, Files, ReceiptText, Scale } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useAuth } from '@/contexts/AuthContext';
import { Header } from '@/pages/components/Header';
import { RankingCard } from '@/pages/components/RankingCard';
import { StatCard } from '@/pages/components/StatCard';
import { CfopAnalysisTable } from '@/pages/components/CfopAnalysisTable';
import {
  fetchNfeAnaliseFiscalCfop,
  fetchNfeKpis,
  parseDecimal,
} from '@/services/nfe';
import {
  fetchSpedAnaliseFiscalCfop,
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

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);
  const isSped = Boolean(user?.tem_sped);

  const yearsQuery = useQuery({
    queryKey: ['analise-fiscal-cfop-anos', emitenteCnpj, isSped],
    queryFn: () =>
      isSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const fiscalQuery = useQuery({
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
    enabled: hasEmitenteCnpj,
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

  const totalMovimentado = parseDecimal(fiscalQuery.data?.total_movimentado ?? 0);
  const totalVendas = parseDecimal(
    fiscalQuery.data?.top_categorias?.find((categoria) => categoria.categoria === 'Venda')?.valor_total ?? 0,
  );
  const quantidadeDocumentos = fiscalQuery.data?.quantidade_documentos ?? 0;
  const quantidadeCfops = fiscalQuery.data?.quantidade_cfops ?? 0;
  const categoriasAtivas = (fiscalQuery.data?.top_categorias ?? []).length;

  const stats = [
    {
      title: 'Total movimentado',
      value: formatCurrency(totalMovimentado),
      description: 'Somatório fiscal do período',
      icon: Scale,
      trend: 'up' as const,
      accentClass: 'border-l-sky-500',
    },
    {
      title: 'Documentos fiscais',
      value: quantidadeDocumentos.toString(),
      description: 'Documentos com itens e CFOP',
      icon: Files,
      trend: 'up' as const,
      accentClass: 'border-l-emerald-500',
    },
    // {
    //   title: 'Vendas por CFOP',
    //   value: formatCurrency(totalVendas),
    //   description: 'SomatÃ³rio apenas das vendas',
    //   icon: ReceiptText,
    //   trend: 'up' as const,
    //   accentClass: 'border-l-fuchsia-500',
    // },
    {
      title: 'CFOPs distintos',
      value: quantidadeCfops.toString(),
      description: 'Variedade de operações no período',
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

  const categoriaItems = (fiscalQuery.data?.top_categorias ?? []).map((categoria, index) => {
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

  const cfopItems = (fiscalQuery.data?.top_cfops ?? []).map((cfop, index) => ({
    key: `${cfop.cfop}-${index}`,
    cfop: cfop.cfop || '0000',
    descricao: cfop.descricao || 'CFOP sem descrição',
    valorTotal: parseDecimal(cfop.valor_total ?? 0),
    participacao: parseDecimal(cfop.participacao_percentual ?? 0),
  }));

  return (
    <div className="space-y-6 py-6">
      <Header
        title="Análise Fiscal por CFOP"
        subtitle="Visão ampla das operações fiscais autorizadas do período"
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={setSelectedMonth}
        onYearChange={setSelectedYear}
      />

      {fiscalQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar análise fiscal</AlertTitle>
          <AlertDescription>
            {fiscalQuery.error instanceof Error
              ? fiscalQuery.error.message
              : 'Não foi possível consultar a análise fiscal por CFOP.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={fiscalQuery.isLoading} />
        ))}
      </div>

      <RankingCard
        title="Categorias fiscais"
        description="Distribuição das principais naturezas de operação no período"
        items={categoriaItems}
        isLoading={fiscalQuery.isLoading}
        loadingMessage="Carregando categorias fiscais..."
        emptyMessage="Nenhuma categoria fiscal encontrada."
        totalValue={formatCurrency(totalMovimentado)}
        showAbcReport={false}
        showAbcClassification={false}
      />

      <CfopAnalysisTable
        items={cfopItems}
        isLoading={fiscalQuery.isLoading}
        isError={fiscalQuery.isError}
        formatCurrency={formatCurrency}
        title="Todos os CFOPs com valor"
        description="CFOPs ordenados por impacto no período, com uma faixa maior de registros para evitar divergências ao conferir as somas."
        emptyMessage="Nenhum CFOP fiscal encontrado para o período selecionado."
      />
    </div>
  );
}
