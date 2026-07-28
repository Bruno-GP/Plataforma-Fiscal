import { useCallback, useEffect, useRef, useState } from 'react';

import {
  deleteContaAzulIntegracao,
  getContaAzulAuthUrl,
  getContaAzulIntegracao,
  getContaAzulSincronizacoes,
  syncContaAzul,
} from './contaAzul.api';
import type { ContaAzulIntegracao } from './contaAzul.types';

export interface UseContaAzulIntegracaoReturn {
  integracao: ContaAzulIntegracao | null;
  loading: boolean;
  sincronizando: boolean;
  error: string | null;
  tokenExpiraBreve: boolean;
  conectar: () => Promise<void>;
  desconectar: () => Promise<void>;
  sincronizarAgora: () => Promise<void>;
  refresh: () => Promise<void>;
}

const TOKEN_WARNING_WINDOW_MS = 30 * 60 * 1000;
const SYNC_POLLING_INTERVAL_MS = 3000;
const CONNECT_POLLING_INTERVAL_MS = 1000;
const MAX_SYNC_ATTEMPTS = 60;

const buildErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
};

const isSyncInProgress = (integracao: ContaAzulIntegracao | null) =>
  Boolean(integracao?.entidades?.some((entidade) => entidade.status === 'EM_PROCESSAMENTO'));

export function useContaAzulIntegracao(empresaId: number): UseContaAzulIntegracaoReturn {
  const [integracao, setIntegracao] = useState<ContaAzulIntegracao | null>(null);
  const [loading, setLoading] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenExpiraBreve, setTokenExpiraBreve] = useState(false);

  const mountedRef = useRef(true);
  const connectPollRef = useRef<number | null>(null);
  const syncTimeoutRef = useRef<number | null>(null);
  const syncAttemptsRef = useRef(0);
  const popupRef = useRef<Window | null>(null);
  const syncActiveRef = useRef(false);

  const clearConnectPolling = useCallback(() => {
    if (connectPollRef.current !== null) {
      window.clearInterval(connectPollRef.current);
      connectPollRef.current = null;
    }

    popupRef.current = null;
  }, []);

  const clearSyncPolling = useCallback(() => {
    if (syncTimeoutRef.current !== null) {
      window.clearTimeout(syncTimeoutRef.current);
      syncTimeoutRef.current = null;
    }

    syncActiveRef.current = false;
    syncAttemptsRef.current = 0;
    setSincronizando(false);
  }, []);

  const refresh = useCallback(async () => {
    if (!empresaId || empresaId <= 0) {
      setIntegracao(null);
      setLoading(false);
      setError(null);
      setTokenExpiraBreve(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await getContaAzulIntegracao(empresaId);
      if (!mountedRef.current) {
        return;
      }

      setIntegracao(data);
    } catch (caughtError) {
      if (!mountedRef.current) {
        return;
      }

      setError(buildErrorMessage(caughtError, 'Nao foi possivel carregar a integracao da Conta Azul.'));
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [empresaId]);

  useEffect(() => {
    mountedRef.current = true;

    clearConnectPolling();
    clearSyncPolling();

    if (!empresaId || empresaId <= 0) {
      setIntegracao(null);
      setLoading(false);
      setSincronizando(false);
      setError(null);
      setTokenExpiraBreve(false);
      return () => {
        mountedRef.current = false;
        clearConnectPolling();
        clearSyncPolling();
      };
    }

    void refresh();

    return () => {
      mountedRef.current = false;
      clearConnectPolling();
      clearSyncPolling();
    };
  }, [clearConnectPolling, clearSyncPolling, empresaId, refresh]);

  useEffect(() => {
    if (!integracao?.token_expira_em) {
      setTokenExpiraBreve(false);
      return;
    }

    const tokenExpiraEmMs = new Date(integracao.token_expira_em).getTime();
    const agora = Date.now();
    const expiraBreve = Number.isFinite(tokenExpiraEmMs) && tokenExpiraEmMs > agora && tokenExpiraEmMs - agora <= TOKEN_WARNING_WINDOW_MS;
    setTokenExpiraBreve(expiraBreve);
  }, [integracao?.token_expira_em]);

  const conectar = useCallback(async () => {
    if (!empresaId || empresaId <= 0) {
      setError('Salve a empresa antes de conectar ao Conta Azul.');
      return;
    }

    setError(null);

    try {
      const { auth_url } = await getContaAzulAuthUrl(empresaId);
      const popup = window.open(auth_url, 'conta-azul-auth', 'width=600,height=700');

      if (!popup) {
        throw new Error('Nao foi possivel abrir a janela de autorizacao.');
      }

      clearConnectPolling();
      popupRef.current = popup;

      connectPollRef.current = window.setInterval(() => {
        if (popup.closed) {
          clearConnectPolling();
          void refresh();
        }
      }, CONNECT_POLLING_INTERVAL_MS);
    } catch (caughtError) {
      setError(buildErrorMessage(caughtError, 'Nao foi possivel iniciar a conexao com a Conta Azul.'));
    }
  }, [clearConnectPolling, empresaId, refresh]);

  const desconectar = useCallback(async () => {
    if (!empresaId || empresaId <= 0) {
      setError('Salve a empresa antes de desconectar a Conta Azul.');
      return;
    }

    setError(null);

    try {
      await deleteContaAzulIntegracao(empresaId);
      if (!mountedRef.current) {
        return;
      }

      setIntegracao(null);
      setTokenExpiraBreve(false);
    } catch (caughtError) {
      if (!mountedRef.current) {
        return;
      }

      setError(buildErrorMessage(caughtError, 'Nao foi possivel desconectar a Conta Azul.'));
    }
  }, [empresaId]);

  const finalizarSincronizacao = useCallback(() => {
    clearSyncPolling();
  }, [clearSyncPolling]);

  const acompanharSincronizacao = useCallback(async (): Promise<void> => {
    if (!syncActiveRef.current || !empresaId || empresaId <= 0) {
      finalizarSincronizacao();
      return;
    }

    if (syncAttemptsRef.current >= MAX_SYNC_ATTEMPTS) {
      finalizarSincronizacao();
      setError('A sincronizacao atingiu o limite de 3 minutos. Tente novamente em instantes.');
      return;
    }

    syncAttemptsRef.current += 1;

    try {
      const data = await getContaAzulSincronizacoes(empresaId);
      if (!mountedRef.current) {
        return;
      }

      setIntegracao(data);

      if (!isSyncInProgress(data)) {
        finalizarSincronizacao();
        return;
      }

      syncTimeoutRef.current = window.setTimeout(() => {
        void acompanharSincronizacao();
      }, SYNC_POLLING_INTERVAL_MS);
    } catch (caughtError) {
      if (!mountedRef.current) {
        return;
      }

      finalizarSincronizacao();
      setError(buildErrorMessage(caughtError, 'Nao foi possivel acompanhar a sincronizacao da Conta Azul.'));
    }
  }, [empresaId, finalizarSincronizacao]);

  const sincronizarAgora = useCallback(async () => {
    if (!empresaId || empresaId <= 0) {
      setError('Salve a empresa antes de sincronizar a Conta Azul.');
      return;
    }

    setError(null);
    finalizarSincronizacao();
    setSincronizando(true);
    syncActiveRef.current = true;
    syncAttemptsRef.current = 0;

    try {
      await syncContaAzul(empresaId);
      await acompanharSincronizacao();
    } catch (caughtError) {
      if (!mountedRef.current) {
        return;
      }

      finalizarSincronizacao();
      setError(buildErrorMessage(caughtError, 'Nao foi possivel iniciar a sincronizacao da Conta Azul.'));
    }
  }, [acompanharSincronizacao, empresaId, finalizarSincronizacao]);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
      clearConnectPolling();
      clearSyncPolling();
    };
  }, [clearConnectPolling, clearSyncPolling]);

  return {
    integracao,
    loading,
    sincronizando,
    error,
    tokenExpiraBreve,
    conectar,
    desconectar,
    sincronizarAgora,
    refresh,
  };
}
