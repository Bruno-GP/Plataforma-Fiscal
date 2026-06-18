import { RelatoriosIAControlsCard } from './RelatoriosIAControlsCard';
import { RelatoriosIAReportSection } from './RelatoriosIAReportSection';
import { useRelatoriosIAPageData } from '../hooks/useRelatoriosIAPageData';

export function RelatoriosIAPage() {
  const {
    selectedYear,
    setSelectedYear,
    selectedMonth,
    setSelectedMonth,
    tipoRelatorio,
    setTipoRelatorio,
    formatoRelatorio,
    setFormatoRelatorio,
    isLoading,
    errorMessage,
    report,
    availableYears,
    hasEmitenteCnpj,
    fonteDados,
    formatoSelecionado,
    tipoSelecionado,
    periodoDescricao,
    reportTitle,
    reportSubtitle,
    reportContainerRef,
    handleGenerate,
    handleCancelGeneration,
    handleExportPdf,
  } = useRelatoriosIAPageData();

  return (
    <section className="space-y-6 py-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Relatórios com IA</h1>
        <p className="text-muted-foreground">
          Escolha o tipo e o formato do relatório para gerar uma leitura com IA baseada nos dados fiscais de
          compras, vendas ou clientes ({fonteDados}).
        </p>
      </div>

      <RelatoriosIAControlsCard
        availableYears={availableYears}
        selectedYear={selectedYear}
        selectedMonth={selectedMonth}
        tipoRelatorio={tipoRelatorio}
        formatoRelatorio={formatoRelatorio}
        hasEmitenteCnpj={hasEmitenteCnpj}
        isLoading={isLoading}
        periodoDescricao={periodoDescricao}
        fonteDados={fonteDados}
        tipoSelecionado={tipoSelecionado}
        formatoSelecionado={formatoSelecionado}
        handleGenerate={handleGenerate}
        handleCancelGeneration={handleCancelGeneration}
        onSelectedYearChange={setSelectedYear}
        onSelectedMonthChange={setSelectedMonth}
        onTipoRelatorioChange={setTipoRelatorio}
        onFormatoRelatorioChange={setFormatoRelatorio}
      />

      <RelatoriosIAReportSection
        errorMessage={errorMessage}
        report={report}
        isLoading={isLoading}
        reportTitle={reportTitle}
        reportSubtitle={reportSubtitle}
        reportContainerRef={reportContainerRef}
        handleGenerate={handleGenerate}
        handleExportPdf={handleExportPdf}
      />
    </section>
  );
}
