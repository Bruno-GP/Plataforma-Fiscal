import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { calculateRiskCompliancePercent } from '../helpers/riskMetrics';

interface RiskDistributionCardProps {
  totalClientes: number;
  clientesSemRisco: number;
  clientesEmRisco: number;
}

export function RiskDistributionCard({
  totalClientes,
  clientesSemRisco,
  clientesEmRisco,
}: RiskDistributionCardProps) {
  const compliancePercent = calculateRiskCompliancePercent(totalClientes, clientesSemRisco);
  const complianceLabel = `${compliancePercent}%`;

  return (
    <Card className="overflow-hidden">
      <CardHeader className="tv-panel-header">
        <CardTitle>Distribuicao de risco</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5 p-5">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border border-emerald-400/25 bg-emerald-400/10 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-300">Baixo</p>
            <p className="mt-2 text-3xl font-bold text-slate-50">{clientesSemRisco}</p>
          </div>
          <div className="rounded-md border border-rose-400/25 bg-rose-400/10 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-rose-300">Critico</p>
            <p className="mt-2 text-3xl font-bold text-slate-50">{clientesEmRisco}</p>
          </div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-slate-300">Conformidade geral</span>
            <span className="font-semibold text-emerald-300">{complianceLabel}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-950">
            <div
              className="h-full rounded-full bg-emerald-400"
              style={{
                width: complianceLabel,
              }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
