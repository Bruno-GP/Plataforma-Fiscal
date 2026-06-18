import { useEffect, useMemo, useRef, useState } from 'react';

import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/contexts/AuthContext';
import { useFiscalYears } from '@/hooks/useFiscalYears';
import { parseDecimal } from '@/services/nfe';
import { createFiscalSourceApi } from '@/services/fiscalSource';
import { createFiscalPeriod, createFiscalQueryKey, getFiscalPeriodDescription } from '@/utils/fiscalPeriod';
import { hasValidEmitenteCnpj, monthLabels } from '@/utils/formatters';
import { printReportElement } from '@/utils/reportPrint';

import {
  buildRelatoriosIASubtitle,
  buildRelatoriosIATitle,
  getTotalPeriodoLabel,
  reportFormatOptions,
  reportTypeOptions,
} from '../helpers/relatoriosIAOptions';
import type { ReportFormat, ReportType } from '../types';

export function useRelatoriosIAPageData() {
  const { user } = useAuth();
  const [selectedYear, setSelectedYear] = useState(String(new Date().getFullYear()));
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [tipoRelatorio, setTipoRelatorio] = useState<ReportType>('compras');
  const [formatoRelatorio, setFormatoRelatorio] = useState<ReportFormat>('executivo');
  const [totalPeriodo, setTotalPeriodo] = useState(0);
  const reportContainerRef = useRef<HTMLDivElement | null>(null);
  const generationAbortRef = useRef<AbortController | null>(null);

  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);
  const fiscalApi = createFiscalSourceApi(user?.tem_sped);

  const fiscalPeriod = useMemo(
    () => createFiscalPeriod(selectedYear, selectedMonth),
    [selectedMonth, selectedYear],
  );
  const fonteDados = fiscalApi.sourceLabel;

  const yearsQuery = useQuery({
    queryKey: createFiscalQueryKey({
      scope: 'kpis-years',
      emitenteCnpj,
      sourceKey: fiscalApi.sourceKey,
    }),
    queryFn: () => fiscalApi.kpis({ emitente_cnpj: emitenteCnpj, limite: 120 }),
    enabled: hasEmitenteCnpj,
    staleTime: 5 * 60 * 1000,
  });

  const { availableYears } = useFiscalYears({
    entries: yearsQuery.data?.resultados ?? [],
    selectedYear,
    setSelectedYear,
  });

  const formatoSelecionado = useMemo(
    () => reportFormatOptions.find((option) => option.value === formatoRelatorio) ?? reportFormatOptions[0],
    [formatoRelatorio],
  );

  const tipoSelecionado = useMemo(
    () => reportTypeOptions.find((option) => option.value === tipoRelatorio) ?? reportTypeOptions[0],
    [tipoRelatorio],
  );

  const periodoDescricao = useMemo(
    () => getFiscalPeriodDescription(fiscalPeriod, monthLabels),
    [fiscalPeriod],
  );

  const reportTitle = useMemo(
    () => buildRelatoriosIATitle(formatoSelecionado.label, periodoDescricao),
    [formatoSelecionado.label, periodoDescricao],
  );

  const totalPeriodoLabel = useMemo(
    () => getTotalPeriodoLabel(tipoRelatorio),
    [tipoRelatorio],
  );

  const reportSubtitle = useMemo(
    () => buildRelatoriosIASubtitle(formatoSelecionado.label, totalPeriodoLabel, totalPeriodo),
    [formatoSelecionado.label, totalPeriodo, totalPeriodoLabel],
  );

  const handleExportPdf = () => {
    const error = printReportElement({
      container: reportContainerRef.current,
      title: reportTitle,
      subtitle: reportSubtitle,
    });

    setErrorMessage(error);
  };

  const handleGenerate = async () => {
    if (!hasEmitenteCnpj || !emitenteCnpj) {
      setErrorMessage('CNPJ emitente inválido. Verifique o cadastro da empresa.');
      return;
    }

    generationAbortRef.current?.abort();
    const abortController = new AbortController();
    generationAbortRef.current = abortController;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const payload = {
        emitente_cnpj: emitenteCnpj,
        ...fiscalPeriod.params,
        limite: 5,
        gerar_relatorio_ia: true,
        formato_relatorio: formatoRelatorio,
        layout: '',
      };

      const requestOptions = { signal: abortController.signal };
      const response =
        tipoRelatorio === 'compras'
          ? await fiscalApi.analiseCompras(payload, requestOptions)
          : tipoRelatorio === 'clientes'
            ? await fiscalApi.analiseClientes(payload, requestOptions)
            : await fiscalApi.analiseVendas(payload, requestOptions);

      const total = 'total_comprado' in response ? response.total_comprado : response.total_vendido;

      setTotalPeriodo(parseDecimal(total ?? 0));
      setReport(response.relatorio_ia ?? 'A IA não retornou conteúdo para este período.');
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        setErrorMessage(null);
        return;
      }

      setReport(null);
      setErrorMessage(error instanceof Error ? error.message : 'Falha ao gerar relatório com IA.');
    } finally {
      if (generationAbortRef.current === abortController) {
        generationAbortRef.current = null;
      }
      setIsLoading(false);
    }
  };

  const handleCancelGeneration = () => {
    generationAbortRef.current?.abort();
  };

  useEffect(() => {
    return () => {
      generationAbortRef.current?.abort();
    };
  }, []);

  return {
    selectedYear,
    setSelectedYear,
    selectedMonth,
    setSelectedMonth,
    isLoading,
    errorMessage,
    report,
    tipoRelatorio,
    setTipoRelatorio,
    formatoRelatorio,
    setFormatoRelatorio,
    totalPeriodo,
    reportContainerRef,
    hasEmitenteCnpj,
    availableYears,
    fonteDados,
    formatoSelecionado,
    tipoSelecionado,
    periodoDescricao,
    reportTitle,
    reportSubtitle,
    handleGenerate,
    handleCancelGeneration,
    handleExportPdf,
  };
}

export type RelatoriosIAPageData = ReturnType<typeof useRelatoriosIAPageData>;
