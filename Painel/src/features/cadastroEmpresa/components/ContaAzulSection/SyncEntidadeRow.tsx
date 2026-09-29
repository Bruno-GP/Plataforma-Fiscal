import { ChevronDown, ChevronUp, CircleAlert, CheckCircle2, Loader2, Minus } from 'lucide-react';
import { useState } from 'react';

import { cn } from '@/lib/utils';

import type { SyncEntidade } from './contaAzul.types';

interface SyncEntidadeRowProps {
  entidade: SyncEntidade;
  maxRegistros: number;
  sincronizando: boolean;
}

const entidadeLabels: Record<SyncEntidade['entidade'], string> = {
  pessoas: 'Pessoas',
  produtos: 'Produtos',
  categorias: 'Categorias',
  vendas: 'Vendas',
  financeiro: 'Financeiro',
};

const statusLabels: Record<SyncEntidade['status'], string> = {
  SUCESSO: 'Sucesso',
  SUCESSO_PARCIAL: 'Sucesso parcial',
  ERRO: 'Erro',
  EM_PROCESSAMENTO: 'Em processamento',
};

const statusTone: Record<SyncEntidade['status'], string> = {
  SUCESSO: 'text-emerald-300',
  SUCESSO_PARCIAL: 'text-amber-300',
  ERRO: 'text-rose-300',
  EM_PROCESSAMENTO: 'text-sky-300',
};

export function SyncEntidadeRow({ entidade, maxRegistros, sincronizando }: SyncEntidadeRowProps) {
  const [erroAberto, setErroAberto] = useState(false);
  const registros = Math.max(entidade.registros_processados, 0);
  const percent = maxRegistros > 0 ? Math.min((registros / maxRegistros) * 100, 100) : 0;
  const erroId = `conta-azul-erro-${entidade.entidade}`;

  return (
    <div
      className={cn(
        'rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 transition-colors',
        entidade.status === 'ERRO' && 'border-rose-500/30 bg-rose-500/8',
        entidade.status === 'EM_PROCESSAMENTO' && 'border-sky-400/30 bg-sky-400/8',
      )}
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              {entidade.status === 'ERRO' ? (
                <CircleAlert className="h-4 w-4 shrink-0 text-rose-300" />
              ) : entidade.status === 'EM_PROCESSAMENTO' ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-sky-300" />
              ) : (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-300" />
              )}
              <span className="text-sm font-semibold text-slate-100">{entidadeLabels[entidade.entidade]}</span>
              <span className={cn('text-xs font-medium', statusTone[entidade.status])}>{statusLabels[entidade.status]}</span>
            </div>
            <p className="text-xs text-slate-400">
              {registros.toLocaleString('pt-BR')} registros processados
            </p>
          </div>

          {entidade.status === 'ERRO' ? (
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-rose-200 transition hover:bg-rose-500/10"
              onClick={() => setErroAberto((current) => !current)}
              aria-expanded={erroAberto}
              aria-controls={erroId}
            >
              {erroAberto ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              {erroAberto ? 'Ocultar erro' : 'Ver erro'}
            </button>
          ) : null}
        </div>

        <div className="flex items-center gap-3">
          <div
            className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={maxRegistros || 0}
            aria-valuenow={registros}
            aria-label={`Progresso de sincronizacao para ${entidadeLabels[entidade.entidade]}`}
          >
            <div
              className={cn(
                'h-full rounded-full transition-all',
                entidade.status === 'EM_PROCESSAMENTO'
                  ? 'animate-pulse bg-gradient-to-r from-sky-500 via-sky-400 to-cyan-300'
                  : entidade.status === 'ERRO'
                    ? 'bg-rose-400'
                    : 'bg-emerald-400',
              )}
              style={{ width: `${percent}%` }}
            />
          </div>
          <span className="shrink-0 text-sm text-slate-300">{registros.toLocaleString('pt-BR')}</span>
        </div>

        {entidade.status === 'ERRO' && entidade.erro ? (
          <div
            id={erroId}
            className={cn(
              'overflow-hidden rounded-xl border border-rose-500/25 bg-rose-950/35 px-3 py-2 text-sm text-rose-100 transition-all',
              erroAberto ? 'max-h-40 opacity-100' : 'max-h-0 border-transparent px-0 py-0 opacity-0',
            )}
          >
            <div className="flex items-start gap-2">
              <Minus className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />
              <p>{entidade.erro}</p>
            </div>
          </div>
        ) : null}

        {sincronizando && entidade.status === 'EM_PROCESSAMENTO' ? (
          <p className="text-xs text-sky-200/90">Sincronizando esta entidade agora...</p>
        ) : null}
      </div>
    </div>
  );
}
