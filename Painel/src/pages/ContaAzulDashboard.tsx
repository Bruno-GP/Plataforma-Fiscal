import { DollarSign } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { StatCard } from './components/StatCard';
import { useAuth } from '@/contexts/AuthContext';
import { fetchContaAzulKpis } from '@/services/contaAzul';
import { formatCurrency } from '@/utils/formatters';

interface ContaAzulKpiMensal {
  mes: string;
  receita_total: number;
}

interface ConsultaContaAzulKpisResponse {
  resultados: ContaAzulKpiMensal[];
}

export default function ContaAzulDashboard() {
  const { user } = useAuth();

  const kpisQuery = useQuery({
    queryKey: ['conta-azul-kpis', user?.emitente_cnpj],
    queryFn: () =>
      fetchContaAzulKpis({ emitente_cnpj: user?.emitente_cnpj, limite: 1 }) as Promise<ConsultaContaAzulKpisResponse>,
    enabled: Boolean(user?.emitente_cnpj),
    staleTime: 5 * 60 * 1000,
  });

  const faturamentoMensal = kpisQuery.data?.resultados?.[0]?.receita_total;

  return (
    <div className="space-y-6 py-6">
      {kpisQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar indicadores</AlertTitle>
          <AlertDescription>
            {kpisQuery.error instanceof Error ? kpisQuery.error.message : 'Não foi possível buscar os KPIs da Conta Azul.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="stat-card-grid">
        <StatCard
          title="Faturamento Mensal"
          value={faturamentoMensal !== undefined ? formatCurrency(faturamentoMensal) : '--'}
          description="Dado sincronizado da Conta Azul"
          icon={DollarSign}
          trend="neutral"
          isLoading={kpisQuery.isLoading}
          appendPreviousMonthLabel={false}
        />
      </div>
    </div>
  );
}
