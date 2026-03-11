import { useState, useMemo } from "react";
import { Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { fetchNfeKpis, parseDecimal } from "@/services/nfe";
import { fetchSpedKpis } from "@/services/sped";
import { useAuth } from "@/contexts/AuthContext";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);

const hasValidEmitenteCnpj = (value: string | undefined) => {
  const digits = (value ?? "").replace(/\D/g, "");
  return digits.length === 14 && ![...digits].every((digit) => digit === "0");
};

export default function Clientes() {
  const [search, setSearch] = useState("");
  const { user } = useAuth();
  const usaSped = Boolean(user?.tem_sped);
  
  const emitenteCnpj = user?.emitente_cnpj;
  const hasEmitenteCnpj = hasValidEmitenteCnpj(emitenteCnpj);

  const kpisQuery = useQuery({
    queryKey: ["kpis-clientes", usaSped ? "sped" : "xml", emitenteCnpj],
    queryFn: () =>
      usaSped
        ? fetchSpedKpis({ emitente_cnpj: emitenteCnpj, limite: 12 })
        : fetchNfeKpis({ emitente_cnpj: emitenteCnpj, limite: 12 }),
    enabled: hasEmitenteCnpj,
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
  const filteredClientes = topClientes
    .filter((client) =>
      (client.cliente ?? "").toLowerCase().includes(search.toLowerCase()),
    )
    .slice(0, 10);
  const totalReceita = parseDecimal(latestKpi?.kpis.total_vendas ?? 0);
  const totalImpostos =
    parseDecimal(latestKpi?.kpis.total_icms ?? 0) +
    parseDecimal(latestKpi?.kpis.total_ipi ?? 0) +
    parseDecimal(latestKpi?.kpis.total_pis ?? 0) +
    parseDecimal(latestKpi?.kpis.total_cofins ?? 0);
  const margem =
    totalReceita > 0
      ? ((totalReceita - totalImpostos) / totalReceita) * 100
      : 0;
  const ticketMedioPorCliente = parseDecimal(latestKpi?.kpis.ticket_medio ?? 0);

  return (
    <div className="space-y-6 py-6">
      <div>
        <h1 className="text-3xl font-bold">Análise de Clientes</h1>
        <p className="text-muted-foreground">
          Visão consolidada de faturamento e desempenho
        </p>
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
              Faturamento por Cliente
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {kpisQuery.isLoading
                ? "Carregando..."
                : formatCurrency(totalReceita)}
            </div>

            <p className="text-xs text-muted-foreground">
              Faturamento total no período
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Ticket Médio
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {kpisQuery.isLoading
                ? "Carregando..."
                : formatCurrency(ticketMedioPorCliente)}
            </div>

            <p className="text-xs text-muted-foreground">
              Ticket médio de vendas no período
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Margem
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {kpisQuery.isLoading ? "Carregando..." : `${margem.toFixed(1)}%`}
            </div>

            <p className="text-xs text-muted-foreground">
              Margem estimada sobre o faturamento
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Ranking de cliente</CardTitle>
              <CardDescription>
                Top 10 clientes por participação no faturamento
              </CardDescription>
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
          <div className="max-h-[420px] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Cliente</TableHead>
                  <TableHead className="text-right">Faturamento</TableHead>
                  <TableHead>Participação</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {kpisQuery.isLoading ? (
                  <TableRow>
                    <TableCell
                      colSpan={3}
                      className="py-8 text-center text-sm text-muted-foreground"
                    >
                      Carregando clientes...
                    </TableCell>
                  </TableRow>
                ) : filteredClientes.length ? (
                  filteredClientes.map((client, index) => (
                    <TableRow key={`${client.cliente}-${index}`}>
                      <TableCell className="font-medium">
                        {client.cliente ?? "Cliente não identificado"}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(parseDecimal(client.valor_total ?? 0))}
                      </TableCell>
                      <TableCell>
                        {totalReceita > 0
                          ? `${((parseDecimal(client.valor_total ?? 0) / totalReceita) * 100).toFixed(1)}% do faturamento`
                          : "--"}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={3}
                      className="py-8 text-center text-sm text-muted-foreground"
                    >
                      Nenhum cliente encontrado.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}