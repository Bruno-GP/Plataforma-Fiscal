import { Loader2, RefreshCw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

import { SyncEntidadeRow } from './SyncEntidadeRow';
import type { ContaAzulIntegracao } from './contaAzul.types';

interface SyncStatusPanelProps {
  integracao: ContaAzulIntegracao;
  sincronizando: boolean;
  onSincronizarAgora: () => void;
}

const formatSyncDate = (value: string) => {
  const parts = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(new Date(value));

  const getPart = (type: string) => parts.find((part) => part.type === type)?.value ?? '';

  return `${getPart('day')}/${getPart('month')}/${getPart('year')} às ${getPart('hour')}:${getPart('minute')}`;
};

const sortOrder: ContaAzulIntegracao['entidades'][number]['entidade'][] = [
  'pessoas',
  'produtos',
  'categorias',
  'vendas',
  'financeiro',
];

export function SyncStatusPanel({ integracao, sincronizando, onSincronizarAgora }: SyncStatusPanelProps) {
  const entidadesOrdenadas = [...(integracao.entidades ?? [])].sort(
    (a, b) => sortOrder.indexOf(a.entidade) - sortOrder.indexOf(b.entidade),
  );
  const maxRegistros = Math.max(1, ...entidadesOrdenadas.map((entidade) => entidade.registros_processados));
  const semDados = !integracao.ultima_sync_em || entidadesOrdenadas.length === 0;

  return (
    <div className="space-y-4" aria-live="polite" aria-atomic="true">
      {semDados ? (
        <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
          <p>Nenhuma sincronizacao realizada ainda.</p>
          <Button
            type="button"
            variant="outline"
            className="mt-4 gap-2"
            onClick={onSincronizarAgora}
            disabled={sincronizando}
          >
            {sincronizando ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {sincronizando ? 'Sincronizando...' : 'Sincronizar agora'}
          </Button>
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/55 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              Ultima sincronizacao
            </p>
            <p className="mt-1 text-sm text-slate-100">{formatSyncDate(integracao.ultima_sync_em)}</p>
          </div>

          <div className="space-y-3">
            {entidadesOrdenadas.map((entidade) => (
              <SyncEntidadeRow
                key={entidade.entidade}
                entidade={entidade}
                maxRegistros={maxRegistros}
                sincronizando={sincronizando}
              />
            ))}
          </div>

          <div className="flex justify-end">
            <Button
              type="button"
              variant="outline"
              className={cn('gap-2')}
              onClick={onSincronizarAgora}
              disabled={sincronizando}
              aria-label="Sincronizar agora na Conta Azul"
            >
              {sincronizando ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              {sincronizando ? 'Sincronizando...' : 'Sincronizar agora'}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
