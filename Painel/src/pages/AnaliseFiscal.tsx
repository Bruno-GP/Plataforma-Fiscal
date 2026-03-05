import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import { useAuth } from '@/contexts/AuthContext';

import { parseDecimal } from '@/services/nfe';
import { fetchSpedAnaliseCompras, fetchSpedKpis } from '@/services/sped';
import { formatCurrency, monthLabels } from '@/pages/faturamento/utils/utils';

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 14 && ![...digits].every((digit) => digit === '0');
};

export default function AnaliseFiscal() {
  const { user } = useAuth();

  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const monthNumber = Number.parseInt(selectedMonth, 10);
  const yearNumber = Number.parseInt(selectedYear, 10);

  const yearsQuery = useQuery({
    queryKey: ['analise-fiscal-years', emitenteCnpj],
    queryFn: () => fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const analiseComprasQuery = useQuery({
    queryKey: ['analise-fiscal-compras', emitenteCnpj, yearNumber, selectedMonth],
    queryFn: () => fetchSpedAnaliseCompras({
      emitente_cnpj: emitenteCnpj,
      periodo_ano: Number.isNaN(yearNumber) ? undefined : yearNumber,
      periodo_mes: selectedMonth === 'all' ? undefined : monthNumber,
      limite: 5,
    }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const yearOptions = useMemo(() => {
    const resultados = yearsQuery.data?.resultados ?? [];
    const years = new Set<number>();

    resultados.forEach((item) => {
      if (item.periodo_ano) {
        years.add(item.periodo_ano);
      }
    });

    return [...years].sort((a, b) => b - a);
  }, [yearsQuery.data]);

  useEffect(() => {
    if (!yearOptions.length) {
      return;
    }

    const current = Number.parseInt(selectedYear, 10);
    if (!yearOptions.includes(current)) {
      setSelectedYear(String(yearOptions[0]));
    }
  }, [selectedYear, yearOptions]);

  const data = analiseComprasQuery.data;

  const periodoDescricao = selectedMonth === 'all'
    ? `Acumulado em ${selectedYear}`
    : `${monthLabels[monthNumber - 1]} de ${selectedYear}`;

  if (!user?.tem_sped) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-lg border bg-card p-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Análise Fiscal de Compras</h1>
          <p className="text-sm text-muted-foreground">
            Visão inicial com total comprado e Top 5 por fornecedor e produto.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm text-muted-foreground">
            Ano
            <select
              className="mt-1 w-full rounded-md border bg-background p-2 text-foreground"
              value={selectedYear}
              onChange={(event) => setSelectedYear(event.target.value)}
            >
              {(yearOptions.length ? yearOptions : [yearNumber]).map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </label>

          <label className="text-sm text-muted-foreground">
            Mês
            <select
              className="mt-1 w-full rounded-md border bg-background p-2 text-foreground"
              value={selectedMonth}
              onChange={(event) => setSelectedMonth(event.target.value)}
            >
              <option value="all">Todos</option>
              {monthLabels.map((label, index) => (
                <option key={label} value={index + 1}>{label}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {analiseComprasQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar análise de compras</AlertTitle>
          <AlertDescription>
            {analiseComprasQuery.error instanceof Error
              ? analiseComprasQuery.error.message
              : 'Não foi possível consultar os dados de compras no momento.'}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Total Comprado</CardTitle>
          <CardDescription>{periodoDescricao}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">
            {analiseComprasQuery.isLoading ? 'Carregando...' : formatCurrency(parseDecimal(data?.total_comprado ?? 0))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <RankingFornecedorCard
          title="Top 5 fornecedores por valor"
          isLoading={analiseComprasQuery.isLoading}
          rows={data?.top_fornecedores_valor ?? []}
        />
        <RankingFornecedorCard
          title="Top 5 fornecedores por quantidade de documentos"
          isLoading={analiseComprasQuery.isLoading}
          rows={data?.top_fornecedores_quantidade ?? []}
        />
        <RankingProdutoCard
          title="Top 5 produtos por valor"
          isLoading={analiseComprasQuery.isLoading}
          rows={data?.top_produtos_valor ?? []}
        />
        <RankingProdutoCard
          title="Top 5 produtos por quantidade"
          isLoading={analiseComprasQuery.isLoading}
          rows={data?.top_produtos_quantidade ?? []}
        />
      </div>
    </div>
  );
}

function RankingFornecedorCard({
  title,
  isLoading,
  rows,
}: {
  title: string;
  isLoading: boolean;
  rows: Array<{ fornecedor: string; valor_total: number | string; quantidade_documentos: number }>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Carregando ranking...</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sem dados para o período selecionado.</p>
        ) : rows.map((row, index) => (
          <div key={`${row.fornecedor}-${index}`} className="flex items-center justify-between rounded border p-3">
            <div>
              <p className="font-medium">{row.fornecedor}</p>
              <p className="text-xs text-muted-foreground">{row.quantidade_documentos} documentos</p>
            </div>
            <p className="font-semibold">{formatCurrency(parseDecimal(row.valor_total))}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function RankingProdutoCard({
  title,
  isLoading,
  rows,
}: {
  title: string;
  isLoading: boolean;
  rows: Array<{ produto: string; valor_total: number | string; quantidade_total: number | string }>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Carregando ranking...</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sem dados para o período selecionado.</p>
        ) : rows.map((row, index) => (
          <div key={`${row.produto}-${index}`} className="flex items-center justify-between rounded border p-3">
            <div>
              <p className="font-medium">{row.produto}</p>
              <p className="text-xs text-muted-foreground">Qtd. {parseDecimal(row.quantidade_total).toFixed(2)}</p>
            </div>
            <p className="font-semibold">{formatCurrency(parseDecimal(row.valor_total))}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}