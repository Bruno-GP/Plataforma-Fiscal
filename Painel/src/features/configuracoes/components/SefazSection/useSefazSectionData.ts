import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';

import { useToast } from '@/hooks/use-toast';

import {
  fetchSefazCertificadoStatus,
  fetchSefazDocumentoDetalhe,
  fetchSefazDocumentos,
  fetchSefazSyncLog,
  manifestarSefazDocumento,
  syncSefazAgora,
  uploadSefazCertificado,
} from './sefaz.api';
import type {
  SefazCertificadoStatus,
  SefazDirecaoFiltro,
  SefazDocumentoDetalhe,
  SefazDocumentoListResponse,
  SefazManifestacaoTipo,
  SefazManifestacaoFiltro,
  SefazSituacaoFiltro,
  SefazSyncLogListResponse,
} from './sefaz.types';

const DOCUMENTOS_PAGE_SIZE = 10;
const SYNC_LOG_PAGE_SIZE = 10;

export interface SefazSectionData {
  activeTab: 'certificado' | 'documentos' | 'historico';
  setActiveTab: (value: 'certificado' | 'documentos' | 'historico') => void;
  certificadoFile: File | null;
  certificadoSenha: string;
  setCertificadoFile: (file: File | null) => void;
  setCertificadoSenha: (value: string) => void;
  documentoFilters: {
    direcao: SefazDirecaoFiltro;
    situacao: SefazSituacaoFiltro;
    manifestacaoPendente: SefazManifestacaoFiltro;
    dataInicio: string;
    dataFim: string;
  };
  setDocumentoFilters: {
    setDirecao: (value: SefazDirecaoFiltro) => void;
    setSituacao: (value: SefazSituacaoFiltro) => void;
    setManifestacaoPendente: (value: SefazManifestacaoFiltro) => void;
    setDataInicio: (value: string) => void;
    setDataFim: (value: string) => void;
    clear: () => void;
  };
  documentosPage: number;
  setDocumentosPage: (value: number) => void;
  syncLogPage: number;
  setSyncLogPage: (value: number) => void;
  selectedDocumentoId: number | null;
  setSelectedDocumentoId: (value: number | null) => void;
  manifestacaoPendenteConfirmacao: { documentoId: number; tipo: SefazManifestacaoTipo } | null;
  setManifestacaoPendenteConfirmacao: (value: { documentoId: number; tipo: SefazManifestacaoTipo } | null) => void;
  statusQuery: UseQueryResult<SefazCertificadoStatus, Error>;
  documentosQuery: UseQueryResult<SefazDocumentoListResponse, Error>;
  documentoDetalheQuery: UseQueryResult<SefazDocumentoDetalhe, Error>;
  syncLogQuery: UseQueryResult<SefazSyncLogListResponse, Error>;
  certificadoUploadPending: boolean;
  sincronizandoAgora: boolean;
  manifestandoDocumento: boolean;
  uploadCertificado: () => Promise<void>;
  syncNow: () => Promise<void>;
  confirmarManifestacao: () => Promise<void>;
  totalDocumentosPages: number;
  totalSyncLogPages: number;
  refreshAll: () => Promise<void>;
}

const defaultFilters = {
  direcao: 'todas' as SefazDirecaoFiltro,
  situacao: 'todas' as SefazSituacaoFiltro,
  manifestacaoPendente: 'todas' as SefazManifestacaoFiltro,
  dataInicio: '',
  dataFim: '',
};

export function useSefazSectionData(): SefazSectionData {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<'certificado' | 'documentos' | 'historico'>('certificado');
  const [certificadoFile, setCertificadoFile] = useState<File | null>(null);
  const [certificadoSenha, setCertificadoSenha] = useState('');
  const [documentosPage, setDocumentosPage] = useState(1);
  const [syncLogPage, setSyncLogPage] = useState(1);
  const [documentoFilters, setDocumentoFiltersState] = useState(defaultFilters);
  const [selectedDocumentoId, setSelectedDocumentoId] = useState<number | null>(null);
  const [manifestacaoPendenteConfirmacao, setManifestacaoPendenteConfirmacao] = useState<{
    documentoId: number;
    tipo: SefazManifestacaoTipo;
  } | null>(null);

  const statusQuery = useQuery({
    queryKey: ['sefaz', 'certificado-status'],
    queryFn: fetchSefazCertificadoStatus,
    staleTime: 60 * 1000,
  });

  const documentosQuery = useQuery({
    queryKey: [
      'sefaz',
      'documentos',
      documentosPage,
      documentoFilters.direcao,
      documentoFilters.situacao,
      documentoFilters.manifestacaoPendente,
      documentoFilters.dataInicio,
      documentoFilters.dataFim,
    ],
    queryFn: () =>
      fetchSefazDocumentos({
        direcao: documentoFilters.direcao === 'todas' ? undefined : documentoFilters.direcao,
        situacao: documentoFilters.situacao === 'todas' ? undefined : documentoFilters.situacao,
        manifestacao_pendente:
          documentoFilters.manifestacaoPendente === 'todas'
            ? undefined
            : documentoFilters.manifestacaoPendente === 'sim',
        data_inicio: documentoFilters.dataInicio || undefined,
        data_fim: documentoFilters.dataFim || undefined,
        limit: DOCUMENTOS_PAGE_SIZE,
        offset: (documentosPage - 1) * DOCUMENTOS_PAGE_SIZE,
      }),
    staleTime: 30 * 1000,
    placeholderData: (previousData) => previousData,
  });

  const syncLogQuery = useQuery({
    queryKey: ['sefaz', 'sync-log', syncLogPage],
    queryFn: () =>
      fetchSefazSyncLog({
        limit: SYNC_LOG_PAGE_SIZE,
        offset: (syncLogPage - 1) * SYNC_LOG_PAGE_SIZE,
      }),
    staleTime: 30 * 1000,
    placeholderData: (previousData) => previousData,
  });

  const documentoDetalheQuery = useQuery({
    queryKey: ['sefaz', 'documento', selectedDocumentoId],
    queryFn: () => fetchSefazDocumentoDetalhe(selectedDocumentoId ?? 0),
    enabled: Boolean(selectedDocumentoId),
  });

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!certificadoFile) {
        throw new Error('Selecione um certificado .pfx ou .p12 antes de enviar.');
      }

      if (!certificadoSenha.trim()) {
        throw new Error('Informe a senha do certificado.');
      }

      return uploadSefazCertificado(certificadoFile, certificadoSenha);
    },
    onSuccess: async () => {
      setCertificadoFile(null);
      setCertificadoSenha('');
      await queryClient.invalidateQueries({ queryKey: ['sefaz'] });
      toast({
        title: 'Certificado salvo',
        description: 'O certificado SEFAZ foi processado com sucesso.',
      });
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Erro ao salvar certificado',
        description: error.message || 'Nao foi possivel salvar o certificado SEFAZ.',
      });
    },
  });

  const syncMutation = useMutation({
    mutationFn: syncSefazAgora,
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['sefaz'] });
      toast({
        title: 'Sincronizacao iniciada',
        description: response.message,
      });
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Erro ao sincronizar',
        description: error.message || 'Nao foi possivel iniciar a sincronizacao SEFAZ.',
      });
    },
  });

  const manifestacaoMutation = useMutation({
    mutationFn: ({
      documentoId,
      tipo,
    }: {
      documentoId: number;
      tipo: SefazManifestacaoTipo;
    }) => manifestarSefazDocumento(documentoId, { tipo_manifestacao: tipo }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['sefaz'] });
      toast({
        title: 'Manifestacao enviada',
        description: `Documento ${response.documento_id} atualizado para ${response.manifestacao_status}.`,
      });
      setManifestacaoPendenteConfirmacao(null);
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Erro ao enviar manifestacao',
        description: error.message || 'Nao foi possivel enviar a manifestacao do documento.',
      });
    },
  });

  const setDirecao = (value: SefazDirecaoFiltro) => {
    setDocumentosPage(1);
    setDocumentoFiltersState((current) => ({ ...current, direcao: value }));
  };

  const setSituacao = (value: SefazSituacaoFiltro) => {
    setDocumentosPage(1);
    setDocumentoFiltersState((current) => ({ ...current, situacao: value }));
  };

  const setManifestacaoPendente = (value: SefazManifestacaoFiltro) => {
    setDocumentosPage(1);
    setDocumentoFiltersState((current) => ({ ...current, manifestacaoPendente: value }));
  };

  const setDataInicio = (value: string) => {
    setDocumentosPage(1);
    setDocumentoFiltersState((current) => ({ ...current, dataInicio: value }));
  };

  const setDataFim = (value: string) => {
    setDocumentosPage(1);
    setDocumentoFiltersState((current) => ({ ...current, dataFim: value }));
  };

  const clearDocumentosFilters = () => {
    setDocumentosPage(1);
    setDocumentoFiltersState(defaultFilters);
  };

  const refreshAll = async () => {
    await queryClient.invalidateQueries({ queryKey: ['sefaz'] });
  };

  const totalDocumentosPages = useMemo(
    () => Math.max(1, Math.ceil((documentosQuery.data?.total ?? 0) / DOCUMENTOS_PAGE_SIZE)),
    [documentosQuery.data?.total],
  );

  const totalSyncLogPages = useMemo(
    () => Math.max(1, Math.ceil((syncLogQuery.data?.total ?? 0) / SYNC_LOG_PAGE_SIZE)),
    [syncLogQuery.data?.total],
  );

  return {
    activeTab,
    setActiveTab,
    certificadoFile,
    certificadoSenha,
    setCertificadoFile,
    setCertificadoSenha,
    documentoFilters,
    setDocumentoFilters: {
      setDirecao,
      setSituacao,
      setManifestacaoPendente,
      setDataInicio,
      setDataFim,
      clear: clearDocumentosFilters,
    },
    documentosPage,
    setDocumentosPage,
    syncLogPage,
    setSyncLogPage,
    selectedDocumentoId,
    setSelectedDocumentoId,
    manifestacaoPendenteConfirmacao,
    setManifestacaoPendenteConfirmacao,
    statusQuery,
    documentosQuery,
    documentoDetalheQuery,
    syncLogQuery,
    certificadoUploadPending: uploadMutation.isPending,
    sincronizandoAgora: syncMutation.isPending,
    manifestandoDocumento: manifestacaoMutation.isPending,
    uploadCertificado: async () => {
      await uploadMutation.mutateAsync();
    },
    syncNow: async () => {
      await syncMutation.mutateAsync();
    },
    confirmarManifestacao: async () => {
      if (!manifestacaoPendenteConfirmacao) {
        return;
      }

      await manifestacaoMutation.mutateAsync({
        documentoId: manifestacaoPendenteConfirmacao.documentoId,
        tipo: manifestacaoPendenteConfirmacao.tipo,
      });
    },
    totalDocumentosPages,
    totalSyncLogPages,
    refreshAll,
  };
}

