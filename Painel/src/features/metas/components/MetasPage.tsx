import { Plus } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

import { useMetasPageData } from '../hooks/useMetasPageData';
import { MetaCancelDialog } from './MetaCancelDialog';
import { MetaCreateDialog } from './MetaCreateDialog';
import { MetaDetailPanel } from './MetaDetailPanel';
import { MetaEditDialog } from './MetaEditDialog';
import { MetasListPanel } from './MetasListPanel';
import { MetasStatsGrid } from './MetasStatsGrid';

export function MetasPage() {
  const data = useMetasPageData();
  const selectedMeta = data.selectedMeta;
  const selectedAnalysis = data.selectedMetaAnalysis;
  const selectedUnit = data.selectedIndicator?.unidade ?? null;
  const currentIndicatorHistory = data.selectedIndicatorHistory?.resultados ?? [];

  return (
    <section className="space-y-6 py-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Metas</h1>
          <p className="text-muted-foreground">
            Acompanhe metas com contexto, histórico e diagnóstico automático de cada indicador.
          </p>
        </div>
        <Button onClick={data.openCreateDialog} disabled={!data.indicatorsQuery.data?.length}>
          <Plus className="mr-2 h-4 w-4" />
          Nova meta
        </Button>
      </div>

      {data.indicatorsQuery.isError || data.metasQuery.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar metas</AlertTitle>
          <AlertDescription>
            {data.indicatorsQuery.error instanceof Error
              ? data.indicatorsQuery.error.message
              : data.metasQuery.error instanceof Error
                ? data.metasQuery.error.message
                : 'Não foi possível buscar os dados do módulo de metas.'}
          </AlertDescription>
        </Alert>
      ) : null}

      <MetasStatsGrid
        activeMetasCount={data.activeMetas.length}
        rhythmSummary={data.rhythmSummary}
        isLoading={data.metasQuery.isLoading}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(20rem,0.4fr)_minmax(0,0.6fr)] xl:items-start">
        <MetasListPanel
          activeMetas={data.activeMetas}
          indicatorsById={data.indicatorsById}
          analysesByMetaId={data.analysesByMetaId}
          isLoading={data.metasQuery.isLoading}
          selectedMetaId={data.selectedMetaId}
          onSelectMeta={data.setSelectedMetaId}
        />

        <MetaDetailPanel
          selectedMeta={selectedMeta}
          selectedAnalysis={selectedAnalysis}
          selectedAnalysisLoading={data.selectedMetaAnalysisLoading}
          selectedUnit={selectedUnit}
          onEdit={data.openEditDialog}
          onCancel={data.handleCancelMeta}
          isCanceling={data.isCanceling}
        />
      </div>

      <MetaCreateDialog
        open={data.isCreateDialogOpen}
        onOpenChange={data.setIsCreateDialogOpen}
        indicators={data.indicatorsQuery.data}
        indicatorsLoading={data.indicatorsQuery.isLoading}
        createForm={data.createForm}
        setCreateForm={data.setCreateForm}
        onSelectIndicator={data.setSelectedIndicatorId}
        selectedIndicator={data.selectedIndicator}
        indicatorHistory={currentIndicatorHistory}
        indicatorHistoryLoading={data.selectedIndicatorHistoryLoading}
        isCreating={data.isCreating}
        onSubmit={data.handleCreateSubmit}
      />

      <MetaEditDialog
        open={data.isEditDialogOpen}
        onOpenChange={data.setIsEditDialogOpen}
        editForm={data.editForm}
        setEditForm={data.setEditForm}
        isUpdating={data.isUpdating}
        onSubmit={data.handleEditSubmit}
      />

      <MetaCancelDialog
        meta={data.metaPendingCancel}
        onOpenChange={(open) => !open && data.setMetaPendingCancel(null)}
        onConfirm={data.confirmCancelMeta}
        isCanceling={data.isCanceling}
      />
    </section>
  );
}
