import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface NcmAnalysisItem {
  key: string;
  ncm: string;
  descricao: string;
  valorTotal: number;
  participacao: number;
}

interface NcmAnalysisTableProps {
  items: NcmAnalysisItem[];
  isLoading: boolean;
  isError: boolean;
  formatCurrency: (value: number) => string;
  title?: string;
  description?: string;
  emptyMessage?: string;
}

export function NcmAnalysisTable({
  items,
  isLoading,
  isError,
  formatCurrency,
  title = 'Análise fiscal por NCM',
  description = 'Movimentação e participação dos NCMs no período selecionado.',
  emptyMessage = 'Nenhum NCM encontrado para o período selecionado.',
}: NcmAnalysisTableProps) {
  return (
    <Card className="rounded-2xl border-slate-800/70 bg-gradient-to-br from-slate-950/80 via-slate-900/85 to-slate-950/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_20px_45px_-30px_rgba(0,0,0,0.9)] backdrop-blur">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Carregando análise por NCM...</p>
        ) : isError ? (
          <p className="text-sm text-muted-foreground">Não foi possível carregar a análise por NCM.</p>
        ) : items.length ? (
          <Table>
            <TableHeader>
              <TableRow className="border-slate-800/70 hover:bg-transparent">
                <TableHead>NCM</TableHead>
                <TableHead>Descrição</TableHead>
                <TableHead className="text-right">Valor</TableHead>
                <TableHead className="text-right">Participação</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.key} className="border-slate-800/70 hover:bg-slate-900/40">
                  <TableCell className="font-medium text-foreground">{item.ncm}</TableCell>
                  <TableCell className="text-muted-foreground">{item.descricao}</TableCell>
                  <TableCell className="text-right font-medium text-foreground">
                    {formatCurrency(item.valorTotal)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {item.participacao.toFixed(2)}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        )}
      </CardContent>
    </Card>
  );
}
