import { Search } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { parseDecimal } from '@/services/fiscal';
import { formatCurrency } from '@/utils/formatters';

import type { MemoriaCalculoTributariaItem } from '@/services/reformaTributaria';

import { formatPercent } from '../helpers/reformaTributariaViewModel';

interface ReformaTributariaMemoriaTableProps {
  memoria: MemoriaCalculoTributariaItem[];
  searchTerm: string;
  isLoading: boolean;
  onSearchTermChange: (value: string) => void;
}

export function ReformaTributariaMemoriaTable({
  memoria,
  searchTerm,
  isLoading,
  onSearchTermChange,
}: ReformaTributariaMemoriaTableProps) {
  return (
    <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
      <CardContent className="p-0">
        <div className="flex flex-col gap-4 border-b border-slate-800/80 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-white">Memoria de calculo</h2>
            <p className="text-sm text-slate-400">Rastreabilidade de regra, base, aliquota e resultado calculado.</p>
          </div>
          <div className="relative w-full max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              value={searchTerm}
              onChange={(event) => onSearchTermChange(event.target.value)}
              placeholder="Pesquisar tributo, etapa, fonte ou hash"
              className="border-slate-700 bg-slate-900/80 pl-10 text-slate-100 placeholder:text-slate-500 focus-visible:ring-sky-500"
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-800 hover:bg-transparent">
                <TableHead className="text-slate-400">Tributo</TableHead>
                <TableHead className="text-slate-400">Etapa</TableHead>
                <TableHead className="text-right text-slate-400">Base</TableHead>
                <TableHead className="text-right text-slate-400">Aliquota</TableHead>
                <TableHead className="text-right text-slate-400">Valor</TableHead>
                <TableHead className="text-slate-400">Fonte</TableHead>
                <TableHead className="text-slate-400">Hash</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {memoria.map((item) => (
                <TableRow key={item.id} className="border-slate-800/80 hover:bg-slate-900/70">
                  <TableCell>
                    <div className="font-medium text-white">{item.tributo_codigo}</div>
                    <div className="text-xs text-slate-400">{item.tributo_nome}</div>
                  </TableCell>
                  <TableCell className="text-slate-300">{item.etapa_calculo}</TableCell>
                  <TableCell className="text-right text-slate-200">{formatCurrency(parseDecimal(item.base_calculo))}</TableCell>
                  <TableCell className="text-right text-slate-200">{formatPercent(item.aliquota_aplicada)}</TableCell>
                  <TableCell className="text-right font-medium text-white">{formatCurrency(parseDecimal(item.valor_calculado))}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="border-slate-600 text-slate-300">
                      {item.fonte_dados}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-[180px] truncate font-mono text-xs text-slate-400">
                    {item.hash_calculo ?? '-'}
                  </TableCell>
                </TableRow>
              ))}
              {!memoria.length && (
                <TableRow className="border-slate-800/80 hover:bg-transparent">
                  <TableCell colSpan={7} className="h-28 text-center text-sm text-slate-400">
                    {isLoading ? 'Carregando memoria de calculo...' : 'Nenhuma memoria de calculo encontrada.'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
