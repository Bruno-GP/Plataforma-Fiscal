import { useState, useMemo } from 'react';
import { Search, MoreHorizontal } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { fetchNfeKpis, parseDecimal } from '@/services/nfe';
import { useAuth } from '@/contexts/AuthContext';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);

export default function Clientes() {
  const [search, setSearch] = useState('');
  const { user } = useAuth();
  const email = user?.email;

  const kpisQuery = useQuery({
    queryKey: ['nfe-kpis-clientes', email],
    queryFn: () => fetchNfeKpis({ email, limite: 12 }),
    staleTime: 5 * 60 * 1000,
  });

  const latestKpi = useMemo(() => {
    const resultados = kpisQuery.data?.resultados ?? [];
    return [...resultados].sort((a, b) => {
      const anoA = a.periodo_ano ?? 0;
      const anoB = b.periodo_ano ?? 0;
      if (anoA !== anoB) {
        return anoB - anoA;
      }
      return (b.periodo_mes ?? 0) - (a.periodo_mes ?? 0);
    })[0];
  }, [kpisQuery.data]);

  const topClientes = latestKpi?.kpis.top_clientes ?? [];
  const filteredClientes = topClientes.filter((client) =>
    (client.cliente ?? '').toLowerCase().includes(search.toLowerCase())
  );
  const totalClientes = topClientes.length;
  const totalReceita = parseDecimal(latestKpi?.kpis.total_vendas ?? 0);
  const totalPercentual = filteredClientes.reduce((sum, client) => sum + parseDecimal(client.percentual ?? 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Clientes</h1>
        <p className="text-muted-foreground">Gerencie sua base de clientes</p>
      </div>

      {kpisQuery.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar clientes</AlertTitle>
          <AlertDescription>
            Não foi possível buscar o ranking de clientes na API.
          </AlertDescription>
        </Alert>
      )}

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Clientes no ranking
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {kpisQuery.isLoading ? 'Carregando...' : totalClientes}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Receita total do período
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {kpisQuery.isLoading ? 'Carregando...' : formatCurrency(totalReceita)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Participação filtrada
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {kpisQuery.isLoading ? 'Carregando...' : `${totalPercentual.toFixed(1)}%`}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Lista de Clientes</CardTitle>
              <CardDescription>Visualize e gerencie todos os clientes</CardDescription>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar clientes..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cliente</TableHead>
                <TableHead>Contato</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Receita Total</TableHead>
                <TableHead>Participação</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {kpisQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center text-sm text-muted-foreground">
                    Carregando clientes...
                  </TableCell>
                </TableRow>
              ) : filteredClientes.length ? (
                filteredClientes.map((client, index) => (
                  <TableRow key={`${client.cliente}-${index}`}>
                    <TableCell className="font-medium">{client.cliente ?? 'Cliente não identificado'}</TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(parseDecimal(client.valor_total ?? 0))}
                    </TableCell>
                    <TableCell>
                      {client.percentual !== undefined
                        ? `${parseDecimal(client.percentual).toFixed(1)}%`
                        : '--'}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>Ver detalhes</DropdownMenuItem>
                          <DropdownMenuItem>Editar</DropdownMenuItem>
                          <DropdownMenuItem>Histórico</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center text-sm text-muted-foreground">
                    Nenhum cliente encontrado.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
