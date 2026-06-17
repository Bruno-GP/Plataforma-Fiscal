import { RefreshCw, ListFilter } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { Tributo } from '@/services/reformaTributaria';

interface ReformaTributariaFiltersCardProps {
  selectedTributo: string;
  tributos: Tributo[];
  hasEmitenteCnpj: boolean;
  isBackfilling: boolean;
  onTributoChange: (value: string) => void;
  onBackfill: () => void;
}

export function ReformaTributariaFiltersCard({
  selectedTributo,
  tributos,
  hasEmitenteCnpj,
  isBackfilling,
  onTributoChange,
  onBackfill,
}: ReformaTributariaFiltersCardProps) {
  return (
    <Card className="border border-slate-800/80 bg-slate-950/70 text-white shadow-[0_18px_55px_-38px_rgba(15,23,42,1)]">
      <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
            <ListFilter className="h-4 w-4 text-sky-300" />
            <span>Filtro de tributo</span>
          </div>
          <p className="text-xs text-slate-400">Apure tributos atuais, de transicao e da Reforma por periodo.</p>
        </div>
        <Select value={selectedTributo} onValueChange={onTributoChange}>
          <SelectTrigger className="w-full border-slate-700 bg-slate-900/80 text-slate-100 md:w-80">
            <SelectValue placeholder="Todos os tributos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os tributos</SelectItem>
            {tributos.map((tributo) => (
              <SelectItem key={tributo.codigo} value={tributo.codigo}>
                {tributo.codigo} - {tributo.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          type="button"
          variant="secondary"
          className="w-full gap-2 md:w-auto"
          disabled={!hasEmitenteCnpj || isBackfilling}
          onClick={onBackfill}
        >
          <RefreshCw className={`h-4 w-4 ${isBackfilling ? 'animate-spin' : ''}`} />
          {isBackfilling ? 'Sincronizando...' : 'Sincronizar dados'}
        </Button>
      </CardContent>
    </Card>
  );
}
