import { TrendingUp, Users, Receipt, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const stats = [
  {
    title: 'Faturamento Mensal',
    value: 'R$ 84.750',
    description: '+12.5% vs mês anterior',
    icon: TrendingUp,
    trend: 'up',
  },
  {
    title: 'Clientes Ativos',
    value: '156',
    description: '+8 novos este mês',
    icon: Users,
    trend: 'up',
  },
  {
    title: 'Receitas Pendentes',
    value: 'R$ 12.400',
    description: '18 faturas em aberto',
    icon: Receipt,
    trend: 'neutral',
  },
  {
    title: 'Inadimplência',
    value: '2.8%',
    description: 'Dentro da meta',
    icon: AlertTriangle,
    trend: 'down',
  },
];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Visão geral do seu negócio</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className={`text-xs ${
                stat.trend === 'up' ? 'text-green-600' : 
                stat.trend === 'down' ? 'text-red-600' : 
                'text-muted-foreground'
              }`}>
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Atividade Recente</CardTitle>
            <CardDescription>Últimas movimentações do sistema</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { action: 'Nova venda registrada', time: 'Há 5 minutos', value: 'R$ 1.250,00' },
                { action: 'Pagamento recebido', time: 'Há 23 minutos', value: 'R$ 3.800,00' },
                { action: 'Novo cliente cadastrado', time: 'Há 1 hora', value: 'Tech Corp' },
                { action: 'Fatura enviada', time: 'Há 2 horas', value: 'R$ 5.600,00' },
              ].map((item, index) => (
                <div key={index} className="flex items-center justify-between border-b pb-2 last:border-0">
                  <div>
                    <p className="font-medium">{item.action}</p>
                    <p className="text-sm text-muted-foreground">{item.time}</p>
                  </div>
                  <span className="text-sm font-medium">{item.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Próximos Vencimentos</CardTitle>
            <CardDescription>Faturas a vencer nos próximos 7 dias</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { client: 'ABC Ltda', date: '25/01', value: 'R$ 2.300,00' },
                { client: 'XYZ Corp', date: '26/01', value: 'R$ 4.500,00' },
                { client: 'Tech Solutions', date: '27/01', value: 'R$ 1.800,00' },
                { client: 'Global Inc', date: '28/01', value: 'R$ 3.200,00' },
              ].map((item, index) => (
                <div key={index} className="flex items-center justify-between border-b pb-2 last:border-0">
                  <div>
                    <p className="font-medium">{item.client}</p>
                    <p className="text-sm text-muted-foreground">Vence em {item.date}</p>
                  </div>
                  <span className="text-sm font-medium">{item.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
