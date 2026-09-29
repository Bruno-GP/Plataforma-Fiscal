import { useMemo, useState } from 'react';
import { Receipt, ShieldAlert, TrendingUp } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/contexts/AuthContext';
import { getLatestFiscalEntry, useFiscalYears } from '@/hooks/useFiscalYears';
import { createFiscalSourceApi } from '@/services/fiscalSource';
import { parseDecimal } from '@/services/nfe';
import { createFiscalQueryKey } from '@/utils/fiscalPeriod';
import { formatCurrency, hasValidEmitenteCnpj } from '@/utils/formatters';
import { aggregateClientKpis, buildClientRiskItems } from '@/utils/rankingUtils';

import { buildTopClientesItems } from '../formatters/clientesRanking';
import {
  countClientesEmRisco,
  countClientesSemRisco,
} from '../helpers/riskMetrics';
import type { ClienteComRisco } from '../types';

export function useClientesDashboardData() {
  const [search, setSearch] = useState('');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');
  const { user } = useAuth();
  const fiscalApi = createFiscalSourceApi(user);

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const kpisQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'kpis-clientes',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
    }),
    queryFn: () => fiscalApi.kpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const resultados = useMemo(
    () => kpisQuery.data?.resultados ?? [],
    [kpisQuery.data?.resultados],
  );
  const latestResult = useMemo(() => getLatestFiscalEntry(resultados), [resultados]);
  const fallbackYear = latestResult?.periodo_ano ?? new Date().getFullYear();
  const { availableYears, selectedYearNumber } = useFiscalYears({
    entries: resultados,
    selectedYear,
    setSelectedYear,
    fallbackYear,
  });

  const safeYear = selectedYearNumber;

  const selectedPeriodKpis = useMemo(() => {
    const filteredByYear = resultados.filter((item) => item.periodo_ano === safeYear);

    if (selectedMonth !== 'all') {
      const selectedMonthNumber = Number.parseInt(selectedMonth, 10);
      return filteredByYear.find((item) => item.periodo_mes === selectedMonthNumber)?.kpis;
    }

    if (!filteredByYear.length) {
      return undefined;
    }

    return aggregateClientKpis(filteredByYear);
  }, [resultados, safeYear, selectedMonth]);

  const totalReceita = parseDecimal(selectedPeriodKpis?.total_vendas ?? 0);
  const topClientes = useMemo(() => selectedPeriodKpis?.top_clientes ?? [], [selectedPeriodKpis]);
  const ticketMedioPorCliente = topClientes.length > 0 ? totalReceita / topClientes.length : 0;

  const clientesComRisco = useMemo(
    () =>
      buildClientRiskItems({
        resultados,
        topClientes,
        totalReceita,
      }) as ClienteComRisco[],
    [resultados, topClientes, totalReceita],
  );

  const filteredClientes = useMemo(
    () =>
      clientesComRisco.filter((client) =>
        client.cliente.toLowerCase().includes(search.toLowerCase()),
      ),
    [clientesComRisco, search],
  );

  const topClientesItems = useMemo(
    () => buildTopClientesItems(filteredClientes),
    [filteredClientes],
  );

  const clientesEmRisco = countClientesEmRisco(filteredClientes);
  const clientesSemRisco = countClientesSemRisco(filteredClientes);

  const stats = [
    {
      title: 'Faturamento por Cliente',
      value: formatCurrency(totalReceita),
      description: 'Total no periodo selecionado',
      icon: TrendingUp,
      trend: 'up',
      accentClass: 'border-l-sky-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Clientes com Risco',
      value: String(clientesEmRisco),
      description: `${clientesSemRisco} sem risco`,
      icon: ShieldAlert,
      trend: clientesEmRisco > 0 ? 'down' : 'up',
      accentClass: 'border-l-rose-500',
      appendPreviousMonthLabel: false,
    },
    {
      title: 'Ticket Medio por Cliente',
      value: formatCurrency(ticketMedioPorCliente),
      description: `${topClientes.length} clientes no ranking`,
      icon: Receipt,
      trend: 'up',
      accentClass: 'border-l-amber-400',
      appendPreviousMonthLabel: false,
    },
  ] as const;

  return {
    search,
    setSearch,
    selectedMonth,
    setSelectedMonth,
    selectedYear: String(safeYear),
    setSelectedYear,
    availableYears: availableYears.length ? availableYears : [safeYear],
    kpisQuery,
    totalReceita,
    filteredClientes,
    topClientesItems,
    clientesEmRisco,
    clientesSemRisco,
    stats,
  };
}
