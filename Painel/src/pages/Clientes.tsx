import { useState } from 'react';
import { Search, MoreHorizontal, Mail, Phone } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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

interface Client {
  id: string;
  name: string;
  email: string;
  phone: string;
  status: 'ativo' | 'inativo' | 'pendente';
  totalRevenue: number;
  lastPurchase: string;
}

const mockClients: Client[] = [
  { id: '1', name: 'ABC Ltda', email: 'contato@abc.com', phone: '(11) 99999-1111', status: 'ativo', totalRevenue: 45000, lastPurchase: '2025-01-20' },
  { id: '2', name: 'XYZ Corp', email: 'comercial@xyz.com', phone: '(11) 99999-2222', status: 'ativo', totalRevenue: 78000, lastPurchase: '2025-01-18' },
  { id: '3', name: 'Tech Solutions', email: 'vendas@tech.com', phone: '(11) 99999-3333', status: 'ativo', totalRevenue: 32000, lastPurchase: '2025-01-15' },
  { id: '4', name: 'Global Inc', email: 'info@global.com', phone: '(11) 99999-4444', status: 'pendente', totalRevenue: 12000, lastPurchase: '2025-01-10' },
  { id: '5', name: 'StartUp Brasil', email: 'contato@startup.com', phone: '(11) 99999-5555', status: 'ativo', totalRevenue: 56000, lastPurchase: '2025-01-22' },
  { id: '6', name: 'Mega Serviços', email: 'atendimento@mega.com', phone: '(11) 99999-6666', status: 'inativo', totalRevenue: 8000, lastPurchase: '2024-12-05' },
  { id: '7', name: 'Prime Business', email: 'comercial@prime.com', phone: '(11) 99999-7777', status: 'ativo', totalRevenue: 92000, lastPurchase: '2025-01-21' },
  { id: '8', name: 'Alpha Consultoria', email: 'contato@alpha.com', phone: '(11) 99999-8888', status: 'ativo', totalRevenue: 67000, lastPurchase: '2025-01-19' },
];

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('pt-BR');
};

const statusVariants = {
  ativo: 'default' as const,
  inativo: 'secondary' as const,
  pendente: 'outline' as const,
};

export default function Clientes() {
  const [search, setSearch] = useState('');

  const filteredClients = mockClients.filter(
    (client) =>
      client.name.toLowerCase().includes(search.toLowerCase()) ||
      client.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Clientes</h1>
        <p className="text-muted-foreground">Gerencie sua base de clientes</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total de Clientes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockClients.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Clientes Ativos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {mockClients.filter((c) => c.status === 'ativo').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Receita Total
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(mockClients.reduce((sum, c) => sum + c.totalRevenue, 0))}
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
                <TableHead>Última Compra</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredClients.map((client) => (
                <TableRow key={client.id}>
                  <TableCell className="font-medium">{client.name}</TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-1 text-sm">
                        <Mail className="h-3 w-3" />
                        {client.email}
                      </div>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Phone className="h-3 w-3" />
                        {client.phone}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariants[client.status]}>
                      {client.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(client.totalRevenue)}
                  </TableCell>
                  <TableCell>{formatDate(client.lastPurchase)}</TableCell>
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
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
