import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '@/contexts/AuthContext';
import { useFiscalYears } from '@/hooks/useFiscalYears';
import { hasValidEmitenteCnpj } from '@/utils/formatters';

import {
  backfillReformaTributaria,
  fetchReformaApuracao,
  fetchReformaMemoriaCalculo,
  fetchReformaTributos,
  totalizarApuracao,
} from '@/services/reformaTributaria';
import { invalidateFiscalDashboardCache, invalidateReformaTributariaCache } from '@/utils/fiscalCache';
import { createFiscalPeriod, createFiscalQueryKey } from '@/utils/fiscalPeriod';

import { buildReformaTributariaStats, filterMemoriaCalculoItems } from '../helpers/reformaTributariaViewModel';

export function useReformaTributariaPageData() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedTributo, setSelectedTributo] = useState('todos');
  const [searchTerm, setSearchTerm] = useState('');

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const fiscalPeriod = useMemo(
    () => createFiscalPeriod(selectedYear, selectedMonth),
    [selectedMonth, selectedYear],
  );
  const tributoCodigo = selectedTributo === 'todos' ? undefined : selectedTributo;
  const origemBackfill: 'nfe' | 'sped' = user?.tem_sped ? 'sped' : 'nfe';

  const tributosQuery = useQuery({
    queryKey: ['reforma-tributaria-tributos'],
    queryFn: ({ signal }) => fetchReformaTributos({}, { signal }),
    staleTime: 10 * 60 * 1000,
  });

  const apuracaoQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'reforma-tributaria-apuracao',
      emitenteCnpj,
      sourceKey: origemBackfill,
      period: fiscalPeriod,
      extra: [tributoCodigo],
    }),
    queryFn: ({ signal }) =>
      fetchReformaApuracao(
        {
          emitente_cnpj: emitenteCnpj,
          ...fiscalPeriod.params,
          tributo_codigo: tributoCodigo,
        },
        { signal },
      ),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const memoriaQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'reforma-tributaria-memoria',
      emitenteCnpj,
      sourceKey: origemBackfill,
      period: fiscalPeriod,
      extra: [tributoCodigo],
    }),
    queryFn: ({ signal }) =>
      fetchReformaMemoriaCalculo(
        {
          emitente_cnpj: emitenteCnpj,
          ...fiscalPeriod.params,
          tributo_codigo: tributoCodigo,
          limite: 80,
        },
        { signal },
      ),
    enabled: hasEmitenteCnpj,
    staleTime: 2 * 60 * 1000,
  });

  const backfillMutation = useMutation({
    mutationFn: () =>
      backfillReformaTributaria({
        emitente_cnpj: emitenteCnpj ?? '',
        origem: origemBackfill,
      }),
    onSuccess: async () => {
      await Promise.all([
        invalidateReformaTributariaCache(queryClient),
        invalidateFiscalDashboardCache(queryClient),
      ]);
    },
  });

  const { availableYears } = useFiscalYears({
    entries: apuracaoQuery.data?.resultados ?? [],
    selectedYear,
    setSelectedYear,
    includeCurrentYear: true,
  });

  useEffect(() => {
    setSearchTerm('');
  }, [selectedMonth, selectedYear, selectedTributo, emitenteCnpj]);

  const apuracoes = apuracaoQuery.data?.resultados ?? [];
  const memoria = memoriaQuery.data?.resultados ?? [];
  const totais = totalizarApuracao(apuracoes);
  const tributosDisponiveis = tributosQuery.data?.resultados ?? [];
  const memoriaFiltrada = useMemo(() => filterMemoriaCalculoItems(memoria, searchTerm), [memoria, searchTerm]);
  const stats = useMemo(
    () => buildReformaTributariaStats({ totais, memoriaTotal: memoriaQuery.data?.total ?? 0 }),
    [memoriaQuery.data?.total, totais],
  );

  return {
    selectedMonth,
    setSelectedMonth,
    selectedYear,
    setSelectedYear,
    selectedTributo,
    setSelectedTributo,
    searchTerm,
    setSearchTerm,
    availableYears,
    tributosDisponiveis,
    apuracoes,
    memoriaFiltrada,
    stats,
    totais,
    emitenteCnpj,
    hasEmitenteCnpj,
    origemBackfill,
    backfillMutation,
    apuracaoQuery,
    memoriaQuery,
    tributosQuery,
  };
}
