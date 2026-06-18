import { ArrowRight, FileWarning } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import type { InconsistenciasPendenciasCardProps } from '../types';

export function InconsistenciasPendenciasCard({
  actionLabel,
  actionLink,
  hasPendencias,
  pendingCount,
  usaSped,
}: InconsistenciasPendenciasCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileWarning className="h-5 w-5" />
          Pendencias ativas
        </CardTitle>
        <CardDescription>Status operacional atual da empresa logada.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium">Arquivos aguardando processamento</p>
              <p className="text-3xl font-semibold">{pendingCount}</p>
            </div>
            <Badge variant={hasPendencias ? 'secondary' : 'default'}>{hasPendencias ? 'Atencao' : 'Em dia'}</Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {usaSped
              ? 'Arquivos TXT importados e ainda nao processados no fluxo SPED.'
              : 'XMLs importados e ainda nao consolidados nos indicadores fiscais.'}
          </p>
        </div>

        <Button asChild className="w-full justify-between">
          <Link to={actionLink}>
            {actionLabel}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
