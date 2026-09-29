import { useState } from 'react';
import { AlertTriangle, ExternalLink, Link2, PlugZap, RefreshCcw, Unplug } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { SyncStatusPanel } from './SyncStatusPanel';
import { useContaAzulIntegracao } from './useContaAzulIntegracao';
import type { IntegracaoStatus } from './contaAzul.types';

interface ContaAzulSectionProps {
  empresaId: number;
}

const statusConfig: Record<IntegracaoStatus, { label: string; variant: 'default' | 'warning' | 'destructive' | 'outline' }> = {
  ATIVA: { label: 'Ativa', variant: 'default' },
  EXPIRADA: { label: 'Expirada', variant: 'warning' },
  REVOGADA: { label: 'Revogada', variant: 'destructive' },
  ERRO: { label: 'Erro', variant: 'destructive' },
  DESCONECTADA: { label: 'Desconectada', variant: 'outline' },
};

const emptyStateDescription =
  'Conecte a empresa ao Conta Azul para habilitar sincronizacao de pessoas, produtos, categorias, vendas e financeiro.';

export function ContaAzulSection({ empresaId }: ContaAzulSectionProps) {
  const { integracao, loading, sincronizando, error, tokenExpiraBreve, conectar, desconectar, sincronizarAgora } =
    useContaAzulIntegracao(empresaId);
  const [confirmarDesconexao, setConfirmarDesconexao] = useState(false);

  const renderStatus = () => {
    if (loading && !integracao) {
      return (
        <div className="space-y-3">
          <div className="h-10 animate-pulse rounded-xl bg-slate-800/60" />
          <div className="h-24 animate-pulse rounded-2xl bg-slate-800/60" />
          <div className="h-10 w-40 animate-pulse rounded-md bg-slate-800/60" />
        </div>
      );
    }

    if (!integracao) {
      return (
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-2xl border border-dashed border-slate-800/80 bg-slate-900/45 p-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-sky-400/25 bg-sky-400/10 text-sky-300">
              <PlugZap className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <p className="font-semibold text-slate-100">Integração não conectada</p>
              <p className="text-sm text-slate-400">{emptyStateDescription}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" onClick={conectar} className="gap-2">
              <Link2 className="h-4 w-4" />
              Conectar ao Conta Azul
            </Button>
            {loading ? <span className="text-sm text-slate-400">Carregando status...</span> : null}
          </div>
        </div>
      );
    }

    const statusMeta = statusConfig[integracao.status];

    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant={statusMeta.variant}>{statusMeta.label}</Badge>
          <p className="text-sm text-slate-300">
            {integracao.status === 'ATIVA'
              ? 'Conexao ativa com o Conta Azul.'
              : integracao.status === 'EXPIRADA'
                ? 'Sessao expirada.'
                : integracao.status === 'ERRO'
                  ? 'A integracao precisa ser reconectada.'
                  : integracao.status === 'REVOGADA'
                    ? 'Autorizacao revogada.'
                    : 'Integração desconectada.'}
          </p>
        </div>

        {integracao.status === 'ATIVA' && tokenExpiraBreve ? (
          <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-100">
            <AlertDescription>Token expira em breve - reconecte para evitar interrupções.</AlertDescription>
          </Alert>
        ) : null}

        {integracao.status === 'ATIVA' ? (
          <>
            <SyncStatusPanel integracao={integracao} sincronizando={sincronizando} onSincronizarAgora={sincronizarAgora} />

            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="destructive"
                className="gap-2"
                onClick={() => setConfirmarDesconexao(true)}
                aria-label="Desconectar Conta Azul"
              >
                <Unplug className="h-4 w-4" />
                Desconectar
              </Button>
              <Button type="button" variant="outline" className="gap-2" onClick={conectar}>
                <RefreshCcw className="h-4 w-4" />
                Atualizar conexão
              </Button>
            </div>
          </>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" onClick={conectar} className="gap-2">
              <ExternalLink className="h-4 w-4" />
              {integracao.status === 'DESCONECTADA' ? 'Conectar novamente' : 'Reconectar'}
            </Button>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <Card className="border-slate-800/80 bg-slate-950/80 shadow-[0_24px_80px_-52px_rgba(15,23,42,0.9)]">
        <CardHeader className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-sky-400/25 bg-sky-400/10 text-sky-300">
              <PlugZap className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-xl">Integração Conta Azul</CardTitle>
              <CardDescription>Conexão OAuth2, sincronização manual e acompanhamento do estado da integração.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {error ? (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <div aria-live="polite" aria-atomic="true">
            {renderStatus()}
          </div>
        </CardContent>
      </Card>

      <Dialog open={confirmarDesconexao} onOpenChange={setConfirmarDesconexao}>
        <DialogContent aria-labelledby="desconectar-conta-azul-title">
          <DialogHeader>
            <DialogTitle id="desconectar-conta-azul-title">Desconectar Conta Azul?</DialogTitle>
            <DialogDescription>
              Isso removera a integracao. Os dados ja sincronizados serao mantidos.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" autoFocus onClick={() => setConfirmarDesconexao(false)}>
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={async () => {
                await desconectar();
                setConfirmarDesconexao(false);
              }}
            >
              Desconectar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
