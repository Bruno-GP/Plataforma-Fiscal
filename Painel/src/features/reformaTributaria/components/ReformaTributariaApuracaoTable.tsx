import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
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

import type { ApuracaoTributariaItem } from '@/services/reformaTributaria';

import { statusVariant, totalizarSaldoApurado } from '../helpers/reformaTributariaViewModel';

interface ReformaTributariaApuracaoTableProps {
  apuracoes: ApuracaoTributariaItem[];
  isLoading: boolean;
}

export function ReformaTributariaApuracaoTable({ apuracoes, isLoading }: ReformaTributariaApuracaoTableProps) {
  return (
    <Card className="overflow-hidden border border-slate-800/80 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white shadow-[0_24px_70px_-44px_rgba(15,23,42,0.42)]">
      <CardContent className="p-0">
        <div className="flex flex-col gap-3 border-b border-slate-800/80 px-6 py-5 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-white">Apuracao por tributo</h2>
            <p className="text-sm text-slate-400">Debitos, creditos, ajustes e saldo por periodo.</p>
          </div>
          <Badge variant="outline" className="w-fit border-slate-600 text-slate-300">
            {apuracoes.length} registros
          </Badge>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-800 hover:bg-transparent">
                <TableHead className="text-slate-400">Tributo</TableHead>
                <TableHead className="text-slate-400">Periodo</TableHead>
                <TableHead className="text-right text-slate-400">Debitos</TableHead>
                <TableHead className="text-right text-slate-400">Creditos</TableHead>
                <TableHead className="text-right text-slate-400">Ajustes</TableHead>
                <TableHead className="text-right text-slate-400">Saldo</TableHead>
                <TableHead className="text-slate-400">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {apuracoes.map((item) => (
                <TableRow key={item.id} className="border-slate-800/80 hover:bg-slate-900/70">
                  <TableCell>
                    <div className="font-medium text-white">{item.tributo_codigo}</div>
                    <div className="text-xs text-slate-400">{item.tributo_nome}</div>
                  </TableCell>
                  <TableCell className="text-slate-300">
                    {String(item.periodo_mes).padStart(2, '0')}/{item.periodo_ano}
                  </TableCell>
                  <TableCell className="text-right text-slate-200">{formatCurrency(parseDecimal(item.total_debitos))}</TableCell>
                  <TableCell className="text-right text-slate-200">{formatCurrency(parseDecimal(item.total_creditos))}</TableCell>
                  <TableCell className="text-right text-slate-200">
                    {formatCurrency(totalizarSaldoApurado(item))}
                  </TableCell>
                  <TableCell className="text-right font-medium text-white">{formatCurrency(parseDecimal(item.saldo_apurado))}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
              {!apuracoes.length && (
                <TableRow className="border-slate-800/80 hover:bg-transparent">
                  <TableCell colSpan={7} className="h-28 text-center text-sm text-slate-400">
                    {isLoading ? 'Carregando apuracao...' : 'Nenhuma apuracao encontrada para os filtros selecionados.'}
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
