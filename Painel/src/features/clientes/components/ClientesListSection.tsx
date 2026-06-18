import { Search } from 'lucide-react';

import { Input } from '@/components/ui/input';
import { RankingCard } from '@/pages/components/RankingCard';
import { formatCurrency } from '@/utils/formatters';

import type { ClienteRankingItem } from '../types';

interface ClientesListSectionProps {
  search: string;
  onSearchChange: (value: string) => void;
  clientesCount: number;
  topClientesItems: ClienteRankingItem[];
  isLoading: boolean;
  totalReceita: number;
}

export function ClientesListSection({
  search,
  onSearchChange,
  clientesCount,
  topClientesItems,
  isLoading,
  totalReceita,
}: ClientesListSectionProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-lg border border-slate-700/80 bg-slate-950/25 p-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-100">Listagem de clientes</p>
          <p className="text-xs text-slate-400">{clientesCount} clientes no recorte atual</p>
        </div>
        <div className="relative w-full md:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <Input
            placeholder="Buscar clientes..."
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      <RankingCard
        title="Ranking de Clientes"
        description="Clientes por participacao no faturamento e indicacao de risco"
        items={topClientesItems}
        isLoading={isLoading}
        loadingMessage="Carregando clientes..."
        emptyMessage="Nenhum cliente encontrado."
        totalValue={formatCurrency(totalReceita)}
        listClassName="max-h-[520px] overflow-y-auto pr-1"
        showAbcReport={false}
        showAbcClassification={false}
      />
    </div>
  );
}
