import { useMemo, useState } from 'react';
import { ListChecks } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';

import type { AnaliseMetaResponse, IndicadorResponse, MetaResponse } from '@/services/metas';

import { MetaListItem } from './MetaListItem';

function ListLoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-72 w-full" />
    </div>
  );
}

export function MetasListPanel({
  activeMetas,
  indicatorsById,
  analysesByMetaId,
  isLoading,
  selectedMetaId,
  onSelectMeta,
}: {
  activeMetas: MetaResponse[];
  indicatorsById: Record<number, IndicadorResponse>;
  analysesByMetaId: Record<number, AnaliseMetaResponse>;
  isLoading: boolean;
  selectedMetaId: number | null;
  onSelectMeta: (metaId: number | null) => void;
}) {
  const [activeMetaSearch, setActiveMetaSearch] = useState('');

  const visibleMetas = useMemo(() => {
    const query = activeMetaSearch.trim().toLowerCase();

    if (!query) {
      return activeMetas;
    }

    return activeMetas.filter((meta) => {
      const indicator = indicatorsById[meta.indicador_id];
      return (
        meta.titulo.toLowerCase().includes(query) ||
        meta.descricao?.toLowerCase().includes(query) ||
        indicator?.nome.toLowerCase().includes(query) ||
        indicator?.chave.toLowerCase().includes(query)
      );
    });
  }, [activeMetaSearch, activeMetas, indicatorsById]);

  return (
    <Card className="min-w-0 xl:sticky xl:top-6 xl:max-h-[calc(100vh-9rem)] xl:overflow-hidden">
      <CardHeader className="tv-panel-header rounded-t-[inherit]">
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-xl">Metas ativas</CardTitle>
              <CardDescription>Lista de acompanhamento com ritmo estimado e diagnóstico resumido.</CardDescription>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <ListChecks className="h-4 w-4 text-sky-300" />
              {visibleMetas.length} metas
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="metas-search" className="text-xs uppercase tracking-[0.18em] text-slate-500">
              Pesquisar
            </Label>
            <Input
              id="metas-search"
              value={activeMetaSearch}
              onChange={(event) => setActiveMetaSearch(event.target.value)}
              placeholder="Buscar por título, descrição ou indicador..."
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="min-w-0 pt-6">
        {isLoading ? (
          <ListLoadingSkeleton />
        ) : visibleMetas.length ? (
          <div className="max-h-[calc(100vh-28rem)] space-y-3 overflow-y-auto pr-2">
            {visibleMetas.map((meta) => (
              <MetaListItem
                key={meta.id}
                meta={meta}
                analysis={analysesByMetaId[meta.id] ?? null}
                indicator={indicatorsById[meta.indicador_id] ?? null}
                selected={meta.id === selectedMetaId}
                onClick={() => onSelectMeta(meta.id)}
                compact
              />
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-slate-700 bg-slate-950/45 px-4 py-10 text-center text-sm text-slate-400">
            {activeMetaSearch.trim()
              ? 'Nenhuma meta ativa corresponde à pesquisa.'
              : 'Nenhuma meta ativa encontrada. Use o formulário ao lado para criar a primeira meta.'}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
