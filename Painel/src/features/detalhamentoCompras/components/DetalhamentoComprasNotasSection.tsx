import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { DetalhamentoComprasNotaMode } from '@/pages/components/Detalhamento/DetalhamentoComprasNotaMode';
import type { NfeNotaDetalhada } from '@/services/nfe';

type Props = {
  isSped: boolean;
  notas: NfeNotaDetalhada[];
  isLoading: boolean;
  openPurchaseSupplierValues: string[];
  onOpenPurchaseSupplierValuesChange: (values: string[]) => void;
  openPurchaseNcmValues: string[];
  onOpenPurchaseNcmValuesChange: (values: string[]) => void;
  openPurchaseProductValues: string[];
  onOpenPurchaseProductValuesChange: (values: string[]) => void;
};

export function DetalhamentoComprasNotasSection({
  isSped,
  notas,
  isLoading,
  openPurchaseSupplierValues,
  onOpenPurchaseSupplierValuesChange,
  openPurchaseNcmValues,
  onOpenPurchaseNcmValuesChange,
  openPurchaseProductValues,
  onOpenPurchaseProductValuesChange,
}: Props) {
  if (isSped) {
    return null;
  }

  return (
    <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
      <CardContent className="p-0">
        <div className="border-b border-slate-800/80 px-6 py-4">
          <div className="flex flex-col gap-2">
            <Badge className="w-fit border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">
              Tributos por item
            </Badge>
            <h2 className="text-xl font-semibold tracking-tight">Compras por fornecedor, NCM e produto</h2>
            <p className="max-w-3xl text-sm text-slate-300">
              A grade usa os tributos complementares sincronizados por item quando existem; caso contrario, mantem
              a leitura proporcional dos tributos legados da nota.
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="p-6 text-sm text-slate-300">Carregando notas detalhadas de compra...</div>
        ) : notas.length > 0 ? (
          <DetalhamentoComprasNotaMode
            notas={notas}
            openNoteValues={openPurchaseSupplierValues}
            onOpenNoteValuesChange={onOpenPurchaseSupplierValuesChange}
            openSupplierValues={openPurchaseNcmValues}
            onOpenSupplierValuesChange={onOpenPurchaseNcmValuesChange}
            openNcmValues={openPurchaseProductValues}
            onOpenNcmValuesChange={onOpenPurchaseProductValuesChange}
          />
        ) : (
          <div className="p-6 text-sm text-slate-300">
            Nenhuma nota detalhada de compra encontrada para o periodo selecionado.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

