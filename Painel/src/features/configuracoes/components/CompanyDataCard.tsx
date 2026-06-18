import { Building2, CircleAlert, MapPin } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import type { EmpresaConfiguracoesViewData, PerfilConfiguracoesQuery } from '../types';
import { ReadOnlyField } from './ReadOnlyField';

interface CompanyDataCardProps {
  empresa: EmpresaConfiguracoesViewData;
  profileQuery: PerfilConfiguracoesQuery;
}

export function CompanyDataCard({ empresa, profileQuery }: CompanyDataCardProps) {
  return (
    <Card className="border-slate-800/80 bg-slate-950/80 shadow-[0_24px_80px_-52px_rgba(15,23,42,0.9)]">
      <CardHeader className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-sky-400/25 bg-sky-400/10 text-sky-300">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-xl">Dados da empresa</CardTitle>
            <CardDescription>Informacoes carregadas a partir da sessao autenticada.</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {profileQuery.isLoading ? (
          <div className="space-y-4">
            <div className="h-11 animate-pulse rounded-md bg-slate-800/70" />
            <div className="h-11 animate-pulse rounded-md bg-slate-800/70" />
            <div className="h-11 animate-pulse rounded-md bg-slate-800/70" />
            <div className="h-11 animate-pulse rounded-md bg-slate-800/70" />
          </div>
        ) : profileQuery.isError ? (
          <div className="flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">Não conseguimos carregar os dados da empresa.</p>
              <p className="mt-1 text-rose-100/80">
                {profileQuery.error instanceof Error
                  ? profileQuery.error.message
                  : 'Tente novamente em alguns instantes.'}
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <ReadOnlyField id="cnpj" label="CNPJ" value={empresa.cnpj || 'Nao informado'} />
              <ReadOnlyField id="empresa" label="Nome da empresa" value={empresa.empresaNome} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <ReadOnlyField id="estado" label="Estado / UF" value={empresa.estado} />
              <ReadOnlyField id="cidade" label="Cidade" value={empresa.cidade} />
            </div>
            {/* <div className="grid gap-4 md:grid-cols-2">
              <ReadOnlyField id="municipio-id" label="Municipio ID" value={empresa.municipioId} />
              <ReadOnlyField id="codigo-ibge" label="Codigo IBGE" value={empresa.codigoIbge} />
            </div> */}
            {empresa.localidadeIncompleta ? (
              <Alert variant="destructive">
                <AlertDescription>
                  A localidade desta empresa esta incompleta. UF, cidade, municipio_id e codigo IBGE precisam
                  estar preenchidos para liberar as consultas fiscais mais complexas.
                </AlertDescription>
              </Alert>
            ) : null}
            <div className="rounded-xl border border-slate-800/70 bg-slate-900/60 p-4 text-sm text-slate-300">
              <div className="flex items-center gap-2 font-medium text-slate-100">
                <MapPin className="h-4 w-4 text-sky-300" />
                Localidade vinculada ao cadastro
              </div>
              <p className="mt-2 leading-6 text-slate-400">
                Esses campos sao exibidos apenas para consulta. Nenhum controle de edicao ou salvamento e
                renderizado nesta area.
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
