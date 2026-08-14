import type { Dispatch, FormEvent, SetStateAction } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { endOfMonth, format, startOfMonth } from 'date-fns';

import { toast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';

import {
  cancelMeta,
  createMeta,
  fetchIndicadorHistorico,
  fetchIndicadores,
  fetchMetaAnalise,
  fetchMetas,
  updateMeta,
  type AnaliseMetaResponse,
  type IndicadorHistoricoResponse,
  type IndicadorResponse,
  type MetaCreatePayload,
  type MetaResponse,
  type MetaUpdatePayload,
  type PeriodoTipo,
  type StatusMeta,
  type StatusRitmo,
  type TipoMeta,
  type UnidadeIndicador,
} from '@/services/metas';

export interface MetaFormValues {
  indicador_id: number;
  titulo: string;
  descricao: string;
  valor_alvo: string;
  tipo_meta: TipoMeta;
  periodo_tipo: PeriodoTipo;
  periodo_inicio: string;
  periodo_fim: string;
}

export interface MetaEditValues {
  titulo: string;
  descricao: string;
  valor_alvo: string;
  status: StatusMeta;
}

const createDefaultForm = (indicadorId = 0): MetaFormValues => {
  const today = new Date();

  return {
    indicador_id: indicadorId,
    titulo: '',
    descricao: '',
    valor_alvo: '',
    tipo_meta: 'crescimento',
    periodo_tipo: 'mensal',
    periodo_inicio: format(startOfMonth(today), 'yyyy-MM-dd'),
    periodo_fim: format(endOfMonth(today), 'yyyy-MM-dd'),
  };
};

export interface MetasPageData {
  indicatorsQuery: ReturnType<typeof useQuery<IndicadorResponse[]>>;
  metasQuery: ReturnType<typeof useQuery<{ total: number; resultados: MetaResponse[] }>>;
  selectedMetaId: number | null;
  setSelectedMetaId: (metaId: number | null) => void;
  selectedIndicatorId: number | null;
  setSelectedIndicatorId: (indicadorId: number | null) => void;
  selectedMeta: MetaResponse | null;
  selectedMetaAnalysis: AnaliseMetaResponse | null;
  selectedMetaAnalysisLoading: boolean;
  selectedIndicator: IndicadorResponse | null;
  selectedIndicatorHistory: IndicadorHistoricoResponse | null;
  selectedIndicatorHistoryLoading: boolean;
  activeMetas: MetaResponse[];
  analysesByMetaId: Record<number, AnaliseMetaResponse>;
  createForm: MetaFormValues;
  setCreateForm: Dispatch<SetStateAction<MetaFormValues>>;
  editForm: MetaEditValues;
  setEditForm: Dispatch<SetStateAction<MetaEditValues>>;
  isEditDialogOpen: boolean;
  setIsEditDialogOpen: Dispatch<SetStateAction<boolean>>;
  isCreateDialogOpen: boolean;
  setIsCreateDialogOpen: Dispatch<SetStateAction<boolean>>;
  openEditDialog: (meta: MetaResponse) => void;
  openCreateDialog: () => void;
  handleCreateSubmit: (event: FormEvent<HTMLFormElement>) => void;
  handleEditSubmit: (event: FormEvent<HTMLFormElement>) => void;
  handleCancelMeta: (meta: MetaResponse) => void;
  metaPendingCancel: MetaResponse | null;
  setMetaPendingCancel: Dispatch<SetStateAction<MetaResponse | null>>;
  confirmCancelMeta: () => void;
  isCreating: boolean;
  isUpdating: boolean;
  isCanceling: boolean;
  rhythmSummary: Record<StatusRitmo, number>;
  indicatorsById: Record<number, IndicadorResponse>;
  formatIndicatorValue: (value: number, unidade?: UnidadeIndicador | null) => string;
}

const formatIndicatorValue = (value: number, unidade?: UnidadeIndicador | null) => {
  if (unidade === 'moeda') {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
  }

  if (unidade === 'percentual') {
    return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value)}%`;
  }

  if (unidade === 'dias') {
    return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value)} dias`;
  }

  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value);
};

export function useMetasPageData(): MetasPageData {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const indicatorsQuery = useQuery({
    queryKey: ['metas', 'indicadores', user?.emitente_cnpj],
    queryFn: () => fetchIndicadores('xml'),
    enabled: Boolean(user?.emitente_cnpj),
    staleTime: 5 * 60 * 1000,
  });

  const metasQuery = useQuery({
    queryKey: ['metas', 'lista', user?.emitente_cnpj],
    queryFn: () => fetchMetas(),
    enabled: Boolean(user?.emitente_cnpj),
    staleTime: 90 * 1000,
  });

  const [selectedMetaId, setSelectedMetaId] = useState<number | null>(null);
  const [selectedIndicatorId, setSelectedIndicatorId] = useState<number | null>(null);
  const [createForm, setCreateForm] = useState<MetaFormValues>(createDefaultForm());
  const [editForm, setEditForm] = useState<MetaEditValues>({
    titulo: '',
    descricao: '',
    valor_alvo: '',
    status: 'ativa',
  });
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  const indicatorsById = useMemo(
    () => Object.fromEntries((indicatorsQuery.data ?? []).map((item) => [item.id, item])),
    [indicatorsQuery.data],
  );

  useEffect(() => {
    if (!selectedIndicatorId && indicatorsQuery.data?.length) {
      const firstIndicatorId = indicatorsQuery.data[0]?.id ?? null;
      setSelectedIndicatorId(firstIndicatorId);
      setCreateForm((current) => ({
        ...current,
        indicador_id: firstIndicatorId ?? current.indicador_id,
      }));
    }
  }, [indicatorsQuery.data, selectedIndicatorId]);

  const activeMetas = useMemo(() => {
    const allMetas = metasQuery.data?.resultados ?? [];
    return allMetas.filter((meta) => meta.status === 'ativa');
  }, [metasQuery.data]);

  useEffect(() => {
    if (selectedMetaId) {
      return;
    }

    const firstMetaId = activeMetas[0]?.id ?? metasQuery.data?.resultados[0]?.id ?? null;
    setSelectedMetaId(firstMetaId);
  }, [activeMetas, metasQuery.data, selectedMetaId]);

  const analyses = useQueries({
    queries: (metasQuery.data?.resultados ?? []).map((meta) => ({
      queryKey: ['metas', 'analise', meta.id],
      queryFn: () => fetchMetaAnalise(meta.id),
      enabled: Boolean(meta.id),
      staleTime: 60 * 1000,
    })),
  });

  const analysesByMetaId = useMemo(
    () =>
      (metasQuery.data?.resultados ?? []).reduce<Record<number, AnaliseMetaResponse>>((acc, meta, index) => {
        const item = analyses[index];
        if (item?.data) {
          acc[meta.id] = item.data;
        }
        return acc;
      }, {}),
    [analyses, metasQuery.data],
  );

  const selectedMeta = useMemo(() => {
    return metasQuery.data?.resultados.find((meta) => meta.id === selectedMetaId) ?? null;
  }, [metasQuery.data, selectedMetaId]);

  const selectedMetaAnalysis = selectedMetaId ? analysesByMetaId[selectedMetaId] ?? null : null;
  const selectedMetaAnalysisLoading = selectedMetaId
    ? analyses.find((item, index) => (metasQuery.data?.resultados ?? [])[index]?.id === selectedMetaId)?.isLoading ?? false
    : false;

  const selectedIndicator = useMemo(() => {
    if (!selectedIndicatorId) {
      return null;
    }

    return indicatorsById[selectedIndicatorId] ?? null;
  }, [indicatorsById, selectedIndicatorId]);

  const selectedIndicatorHistoryQuery = useQuery({
    queryKey: ['metas', 'indicador-historico', selectedIndicatorId],
    queryFn: () => fetchIndicadorHistorico(selectedIndicatorId ?? 0, 12),
    enabled: Boolean(selectedIndicatorId),
    staleTime: 60 * 1000,
  });

  const rhythmSummary = useMemo(() => {
    const base: Record<StatusRitmo, number> = {
      no_caminho: 0,
      em_risco: 0,
      fora_da_rota: 0,
    };

    Object.values(analysesByMetaId).forEach((analysis) => {
      base[analysis.status_ritmo] += 1;
    });

    return base;
  }, [analysesByMetaId]);

  const createMutation = useMutation({
    mutationFn: (payload: MetaCreatePayload) => createMeta(payload),
    onSuccess: (meta) => {
      queryClient.invalidateQueries({ queryKey: ['metas'] });
      setSelectedMetaId(meta.id);
      setCreateForm((current) => ({
        ...createDefaultForm(current.indicador_id),
        indicador_id: current.indicador_id,
      }));
      setIsCreateDialogOpen(false);
      toast({
        title: 'Meta criada',
        description: 'A meta foi salva e já aparece na lista de acompanhamento.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Nao foi possivel criar a meta',
        description: error instanceof Error ? error.message : 'Tente novamente em instantes.',
        variant: 'destructive',
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ metaId, payload }: { metaId: number; payload: MetaUpdatePayload }) => updateMeta(metaId, payload),
    onSuccess: (meta) => {
      queryClient.invalidateQueries({ queryKey: ['metas'] });
      setSelectedMetaId(meta.id);
      setIsEditDialogOpen(false);
      toast({
        title: 'Meta atualizada',
        description: 'Os ajustes foram salvos com sucesso.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Nao foi possivel atualizar a meta',
        description: error instanceof Error ? error.message : 'Tente novamente em instantes.',
        variant: 'destructive',
      });
    },
  });

  const [metaPendingCancel, setMetaPendingCancel] = useState<MetaResponse | null>(null);

  const cancelMutation = useMutation({
    mutationFn: (metaId: number) => cancelMeta(metaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metas'] });
      setSelectedMetaId(null);
      setMetaPendingCancel(null);
      toast({
        title: 'Meta cancelada',
        description: 'A meta foi removida do acompanhamento ativo.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Nao foi possivel cancelar a meta',
        description: error instanceof Error ? error.message : 'Tente novamente em instantes.',
        variant: 'destructive',
      });
    },
  });

  const openEditDialog = (meta: MetaResponse) => {
    setEditForm({
      titulo: meta.titulo,
      descricao: meta.descricao ?? '',
      valor_alvo: String(meta.valor_alvo),
      status: meta.status,
    });
    setIsEditDialogOpen(true);
  };

  const openCreateDialog = () => {
    setIsCreateDialogOpen(true);
  };

  const handleCreateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!createForm.indicador_id) {
      toast({
        title: 'Escolha um indicador',
        description: 'Selecione um indicador antes de criar a meta.',
        variant: 'destructive',
      });
      return;
    }

    const payload: MetaCreatePayload = {
      indicador_id: createForm.indicador_id,
      titulo: createForm.titulo.trim(),
      descricao: createForm.descricao.trim() || null,
      valor_alvo: Number(createForm.valor_alvo),
      tipo_meta: createForm.tipo_meta,
      periodo_tipo: createForm.periodo_tipo,
      periodo_inicio: createForm.periodo_inicio,
      periodo_fim: createForm.periodo_fim,
    };

    if (!payload.titulo || !payload.valor_alvo || Number.isNaN(payload.valor_alvo)) {
      toast({
        title: 'Complete os campos obrigatorios',
        description: 'Titulo e valor alvo sao obrigatorios para salvar a meta.',
        variant: 'destructive',
      });
      return;
    }

    createMutation.mutate(payload);
  };

  const handleEditSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedMeta) {
      return;
    }

    const payload: MetaUpdatePayload = {
      titulo: editForm.titulo.trim(),
      descricao: editForm.descricao.trim() || null,
      valor_alvo: Number(editForm.valor_alvo),
      status: editForm.status,
    };

    if (!payload.titulo || !payload.valor_alvo || Number.isNaN(payload.valor_alvo)) {
      toast({
        title: 'Complete os campos obrigatorios',
        description: 'Titulo e valor alvo precisam estar preenchidos.',
        variant: 'destructive',
      });
      return;
    }

    updateMutation.mutate({ metaId: selectedMeta.id, payload });
  };

  const handleCancelMeta = (meta: MetaResponse) => {
    setMetaPendingCancel(meta);
  };

  const confirmCancelMeta = () => {
    if (!metaPendingCancel) {
      return;
    }

    cancelMutation.mutate(metaPendingCancel.id);
  };

  return {
    indicatorsQuery,
    metasQuery,
    selectedMetaId,
    setSelectedMetaId,
    selectedIndicatorId,
    setSelectedIndicatorId,
    selectedMeta,
    selectedMetaAnalysis,
    selectedMetaAnalysisLoading,
    selectedIndicator,
    selectedIndicatorHistory: selectedIndicatorHistoryQuery.data ?? null,
    selectedIndicatorHistoryLoading: selectedIndicatorHistoryQuery.isLoading,
    activeMetas,
    analysesByMetaId,
    createForm,
    setCreateForm,
    editForm,
    setEditForm,
    isEditDialogOpen,
    setIsEditDialogOpen,
    isCreateDialogOpen,
    setIsCreateDialogOpen,
    openEditDialog,
    openCreateDialog,
    handleCreateSubmit,
    handleEditSubmit,
    handleCancelMeta,
    metaPendingCancel,
    setMetaPendingCancel,
    confirmCancelMeta,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isCanceling: cancelMutation.isPending,
    rhythmSummary,
    indicatorsById,
    formatIndicatorValue,
  };
}
