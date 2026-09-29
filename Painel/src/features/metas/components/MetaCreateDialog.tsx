import type { Dispatch, FormEvent, SetStateAction } from 'react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

import type {
  IndicadorHistoricoPontoResponse,
  IndicadorResponse,
  PeriodoTipo,
  TipoMeta,
} from '@/services/metas';

import type { MetaFormValues } from '../hooks/useMetasPageData';
import { PERIODO_LABELS, TIPO_META_LABELS } from '../helpers/metasLabels';
import { MetaIndicatorPreview } from './MetaIndicatorPreview';

export function MetaCreateDialog({
  open,
  onOpenChange,
  indicators,
  indicatorsLoading,
  createForm,
  setCreateForm,
  onSelectIndicator,
  selectedIndicator,
  indicatorHistory,
  indicatorHistoryLoading,
  isCreating,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  indicators: IndicadorResponse[] | undefined;
  indicatorsLoading: boolean;
  createForm: MetaFormValues;
  setCreateForm: Dispatch<SetStateAction<MetaFormValues>>;
  onSelectIndicator: (indicadorId: number) => void;
  selectedIndicator: IndicadorResponse | null;
  indicatorHistory: IndicadorHistoricoPontoResponse[];
  indicatorHistoryLoading: boolean;
  isCreating: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto border-slate-800 bg-slate-900 text-slate-100">
        <DialogHeader>
          <DialogTitle>Nova meta</DialogTitle>
          <DialogDescription>Escolha um indicador e veja o histórico antes de definir o alvo.</DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="metas-indicador">Indicador</Label>
              <Select
                value={createForm.indicador_id ? String(createForm.indicador_id) : ''}
                onValueChange={(value) => {
                  const indicadorId = Number(value);
                  onSelectIndicator(indicadorId);
                  setCreateForm((current) => ({ ...current, indicador_id: indicadorId }));
                }}
                disabled={indicatorsLoading || !indicators?.length}
              >
                <SelectTrigger id="metas-indicador">
                  <SelectValue placeholder="Selecione um indicador" />
                </SelectTrigger>
                <SelectContent>
                  {indicators?.map((indicator) => (
                    <SelectItem key={indicator.id} value={String(indicator.id)}>
                      {indicator.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="metas-titulo">Título</Label>
              <Input
                id="metas-titulo"
                value={createForm.titulo}
                onChange={(event) => setCreateForm((current) => ({ ...current, titulo: event.target.value }))}
                placeholder="Ex.: Crescer faturamento do canal direto"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="metas-tipo">Tipo de meta</Label>
              <Select
                value={createForm.tipo_meta}
                onValueChange={(value) => setCreateForm((current) => ({ ...current, tipo_meta: value as TipoMeta }))}
              >
                <SelectTrigger id="metas-tipo">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TIPO_META_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="metas-periodo">Período</Label>
              <Select
                value={createForm.periodo_tipo}
                onValueChange={(value) =>
                  setCreateForm((current) => ({ ...current, periodo_tipo: value as PeriodoTipo }))
                }
              >
                <SelectTrigger id="metas-periodo">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PERIODO_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="metas-inicio">Início</Label>
              <Input
                id="metas-inicio"
                type="date"
                value={createForm.periodo_inicio}
                onChange={(event) => setCreateForm((current) => ({ ...current, periodo_inicio: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="metas-fim">Fim</Label>
              <Input
                id="metas-fim"
                type="date"
                value={createForm.periodo_fim}
                onChange={(event) => setCreateForm((current) => ({ ...current, periodo_fim: event.target.value }))}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="metas-valor">Valor alvo</Label>
            <Input
              id="metas-valor"
              inputMode="decimal"
              value={createForm.valor_alvo}
              onChange={(event) => setCreateForm((current) => ({ ...current, valor_alvo: event.target.value }))}
              placeholder="Ex.: 50000"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="metas-descricao">Descrição</Label>
            <Textarea
              id="metas-descricao"
              value={createForm.descricao}
              onChange={(event) => setCreateForm((current) => ({ ...current, descricao: event.target.value }))}
              placeholder="Contexto da meta, estratégia, equipe responsável..."
              className="min-h-24"
            />
          </div>

          <MetaIndicatorPreview
            indicator={selectedIndicator}
            history={indicatorHistory}
            isLoading={indicatorHistoryLoading}
          />

          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Fechar
            </Button>
            <Button type="submit" disabled={isCreating || !indicators?.length}>
              {isCreating ? 'Salvando...' : 'Criar meta'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
