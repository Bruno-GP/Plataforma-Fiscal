import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

import type { MetaResponse } from '@/services/metas';

export function MetaCancelDialog({
  meta,
  onOpenChange,
  onConfirm,
  isCanceling,
}: {
  meta: MetaResponse | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isCanceling: boolean;
}) {
  return (
    <AlertDialog open={Boolean(meta)} onOpenChange={onOpenChange}>
      <AlertDialogContent className="border-slate-800 bg-slate-900 text-slate-100">
        <AlertDialogHeader>
          <AlertDialogTitle>Cancelar meta</AlertDialogTitle>
          <AlertDialogDescription>
            {meta
              ? `A meta "${meta.titulo}" sai do acompanhamento ativo, mas continua no histórico com status "Cancelada".`
              : ''}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Voltar</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isCanceling}
            className="bg-rose-600 text-white hover:bg-rose-500"
          >
            {isCanceling ? 'Cancelando...' : 'Cancelar meta'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
