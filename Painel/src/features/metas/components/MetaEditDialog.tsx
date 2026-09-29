import type { Dispatch, FormEvent, SetStateAction } from 'react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

import type { StatusMeta } from '@/services/metas';

import type { MetaEditValues } from '../hooks/useMetasPageData';
import { STATUS_META_LABELS } from '../helpers/metasLabels';

export function MetaEditDialog({
  open,
  onOpenChange,
  editForm,
  setEditForm,
  isUpdating,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editForm: MetaEditValues;
  setEditForm: Dispatch<SetStateAction<MetaEditValues>>;
  isUpdating: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl border-slate-800 bg-slate-900 text-slate-100">
        <DialogHeader>
          <DialogTitle>Editar meta</DialogTitle>
          <DialogDescription>
            Ajuste título, valor alvo, descrição e status sem alterar o indicador ou o período original.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="edit-titulo">Título</Label>
              <Input
                id="edit-titulo"
                value={editForm.titulo}
                onChange={(event) => setEditForm((current) => ({ ...current, titulo: event.target.value }))}
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="edit-descricao">Descrição</Label>
              <Textarea
                id="edit-descricao"
                value={editForm.descricao}
                onChange={(event) => setEditForm((current) => ({ ...current, descricao: event.target.value }))}
                className="min-h-24"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-valor">Valor alvo</Label>
              <Input
                id="edit-valor"
                inputMode="decimal"
                value={editForm.valor_alvo}
                onChange={(event) => setEditForm((current) => ({ ...current, valor_alvo: event.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-status">Status</Label>
              <Select
                value={editForm.status}
                onValueChange={(value) => setEditForm((current) => ({ ...current, status: value as StatusMeta }))}
              >
                <SelectTrigger id="edit-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(STATUS_META_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Fechar
            </Button>
            <Button type="submit" disabled={isUpdating}>
              {isUpdating ? 'Salvando...' : 'Salvar alterações'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
