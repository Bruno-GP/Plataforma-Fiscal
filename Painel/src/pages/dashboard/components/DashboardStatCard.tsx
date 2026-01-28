import type { LucideIcon } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DashboardStatCardProps {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend: 'up' | 'down' | 'neutral';
  isLoading: boolean;
}

export function DashboardStatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
  isLoading,
}: DashboardStatCardProps) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{isLoading ? 'Carregando...' : value}</div>
        <p
          className={`text-xs ${
            trend === 'up'
              ? 'text-green-600'
              : trend === 'down'
                ? 'text-red-600'
                : 'text-muted-foreground'
          }`}
        >
          {isLoading ? '--' : `${description} vs mês anterior`}
        </p>
      </CardContent>
    </Card>
  );
}