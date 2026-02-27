import { useMemo, useState } from 'react';
import { AlertTriangle, CalendarDays, CheckCircle2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  UPDATES_STORAGE_KEY,
  UPDATE_LOG,
  getLatestUpdateVersion,
  hasUnreadUpdates,
} from '../contexts/updates.ts';

export default function Atualizacoes() {
  const [hasUnread, setHasUnread] = useState(() => hasUnreadUpdates());

  const latestVersion = useMemo(() => getLatestUpdateVersion(), []);

  const marcarComoLido = () => {
    localStorage.setItem(UPDATES_STORAGE_KEY, latestVersion);
    setHasUnread(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Atualizações</h1>
        <p className="text-sm text-muted-foreground">
          Histórico das últimas melhorias e correções disponibilizadas no painel.
        </p>
      </div>

      {hasUnread && (
        <Alert className="border-yellow-400/70 bg-yellow-50 text-yellow-900 [&>svg]:text-yellow-700">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Novidades disponíveis</AlertTitle>
          <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>Esta página recebeu novas informações desde sua última visita.</span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="border-yellow-500 text-yellow-800 hover:bg-yellow-100 hover:text-yellow-900"
              onClick={marcarComoLido}
            >
              Marcar aviso como lido
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4">
        {UPDATE_LOG.map((update) => (
          <Card key={update.version}>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-lg">{update.title}</CardTitle>
                  <CardDescription className="mt-1 flex items-center gap-2">
                    <CalendarDays className="h-4 w-4" />
                    {update.date} · versão {update.version}
                  </CardDescription>
                </div>
                {update.version === latestVersion && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-800">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Mais recente
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {update.changes.map((change) => (
                  <li key={change}>{change}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}