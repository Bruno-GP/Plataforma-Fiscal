import { useEffect, useState, type FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Building2, CheckCircle2, CircleAlert, EyeOff, LockKeyhole, MapPin, Shield, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { atualizarSenhaConfiguracoes, fetchPerfilConfiguracoes } from '@/services/configuracoes';

const formatCnpj = (value: string) => {
  const digits = value.replace(/\D/g, '').slice(0, 14);
  if (digits.length !== 14) {
    return value;
  }

  return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
};

const ReadOnlyField = ({
  id,
  label,
  value,
}: {
  id: string;
  label: string;
  value: string;
}) => (
  <div className="space-y-2">
    <Label htmlFor={id} className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
      {label}
    </Label>
    <Input
      id={id}
      value={value}
      readOnly
      aria-readonly="true"
      tabIndex={-1}
      className="h-11 cursor-default border-slate-700/80 bg-slate-950/60 text-slate-100 shadow-none pointer-events-none focus-visible:ring-0"
    />
  </div>
);

export default function Configuracoes() {
  const { user, isAuthenticated, isReady } = useAuth();
  const { toast } = useToast();
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const profileQuery = useQuery({
    queryKey: ['auth', 'perfil-configuracoes'],
    queryFn: fetchPerfilConfiguracoes,
    enabled: isReady && isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  const passwordMutation = useMutation({
    mutationFn: atualizarSenhaConfiguracoes,
    onSuccess: (response) => {
      setNewPassword('');
      setConfirmPassword('');
      setPasswordVisible(false);
      setFormError(null);
      setFormMessage(response.message);
      toast({
        title: 'Senha atualizada',
        description: response.message,
      });
    },
    onError: (error: Error) => {
      setFormError(error.message || 'Nao foi possivel atualizar a senha.');
      setFormMessage(null);
      toast({
        variant: 'destructive',
        title: 'Erro ao atualizar senha',
        description: error.message || 'Nao foi possivel atualizar a senha.',
      });
    },
  });

  useEffect(() => {
    if (!passwordVisible) {
      setFormError(null);
    }
  }, [passwordVisible]);

  const empresaNome = profileQuery.data?.empresa_nome || user?.name || 'Empresa nao identificada';
  const cnpj = formatCnpj(profileQuery.data?.cnpj || user?.emitente_cnpj || '');
  const estado = profileQuery.data?.estado || 'Nao informado';
  const cidade = profileQuery.data?.cidade || 'Nao informada';
  const municipioId = profileQuery.data?.municipio_id || 'Nao informado';
  const codigoIbge = profileQuery.data?.codigo_ibge || 'Nao informado';
  const localidadeIncompleta = !profileQuery.isLoading && !profileQuery.isError && (
    !profileQuery.data?.estado ||
    !profileQuery.data?.cidade ||
    !profileQuery.data?.municipio_id ||
    !profileQuery.data?.codigo_ibge
  );

  const handlePasswordSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const novaSenha = newPassword;
    const confirmarNovaSenha = confirmPassword;

    if (!novaSenha.trim()) {
      setFormError('Informe uma nova senha valida.');
      setFormMessage(null);
      return;
    }

    if (!confirmarNovaSenha.trim()) {
      setFormError('Confirme a nova senha antes de continuar.');
      setFormMessage(null);
      return;
    }

    if (novaSenha !== confirmarNovaSenha) {
      setFormError('As duas senhas precisam ser iguais.');
      setFormMessage(null);
      return;
    }

    setFormError(null);
    passwordMutation.mutate(novaSenha);
  };

  const canSubmitPassword = passwordMutation.isPending || !passwordVisible;

  return (
    <div className="space-y-6">
      <div className="mt-4 relative overflow-hidden rounded-3xl border border-slate-800/80 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_36%),linear-gradient(135deg,_rgba(8,15,28,0.94),_rgba(15,23,42,0.92))] p-6 shadow-[0_24px_80px_-48px_rgba(2,132,199,0.6)] sm:p-8">
        <div className="absolute -right-8 top-0 h-32 w-32 rounded-full bg-sky-400/10 blur-3xl" />
        <div className="relative flex flex-col gap-3 pt-2 sm:pt-4">
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-sky-200">
            <Shield className="h-3.5 w-3.5" />
            Configuracoes de conta
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50 sm:text-4xl">
            Dados da empresa
          </h1>
          {/* <p className="max-w-2xl text-sm text-slate-300 sm:text-base">
            Os dados cadastrais exibidos abaixo sao somente leitura. A unica acao disponivel nesta tela e a
            alteracao da senha do usuario autenticado.
          </p> */}
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
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
                  <ReadOnlyField id="cnpj" label="CNPJ" value={cnpj || 'Nao informado'} />
                  <ReadOnlyField id="empresa" label="Nome da empresa" value={empresaNome} />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <ReadOnlyField id="estado" label="Estado / UF" value={estado} />
                  <ReadOnlyField id="cidade" label="Cidade" value={cidade} />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <ReadOnlyField id="municipio-id" label="Municipio ID" value={municipioId} />
                  <ReadOnlyField id="codigo-ibge" label="Codigo IBGE" value={codigoIbge} />
                </div>
                {localidadeIncompleta ? (
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

        <Card className="border-slate-800/80 bg-slate-950/80 shadow-[0_24px_80px_-52px_rgba(15,23,42,0.9)]">
          <CardHeader className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-400/25 bg-emerald-400/10 text-emerald-300">
                <LockKeyhole className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-xl">Alteracao de senha</CardTitle>
                <CardDescription>Use essa area somente para redefinir a senha do usuario logado.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <button
              type="button"
              onClick={() => {
                setPasswordVisible((current) => !current);
                setFormMessage(null);
                setFormError(null);
              }}
              className="inline-flex items-center gap-2 text-sm font-semibold text-sky-300 underline-offset-4 hover:text-sky-200 hover:underline"
            >
              <EyeOff className="h-4 w-4" />
              Esqueceu a senha?
            </button>

            {formMessage ? (
              <div className="flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <p className="font-semibold">Senha atualizada com sucesso.</p>
                  <p className="mt-1 text-emerald-100/80">{formMessage}</p>
                </div>
              </div>
            ) : null}

            {passwordVisible ? (
              <form onSubmit={handlePasswordSubmit} className="space-y-4 rounded-2xl border border-slate-800/80 bg-slate-900/55 p-4">
                <div className="space-y-2">
                  <Label htmlFor="new-password" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                    Nova senha
                  </Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    autoComplete="new-password"
                    className="h-11 border-slate-700/80 bg-slate-950/60 text-slate-100 shadow-none focus-visible:ring-sky-400/70"
                    aria-describedby={formError ? 'password-form-error' : undefined}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm-password" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                    Confirmar nova senha
                  </Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    autoComplete="new-password"
                    className="h-11 border-slate-700/80 bg-slate-950/60 text-slate-100 shadow-none focus-visible:ring-sky-400/70"
                    aria-describedby={formError ? 'password-form-error' : undefined}
                  />
                </div>

                {formError ? (
                  <div id="password-form-error" className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                    {formError}
                  </div>
                ) : null}

                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    type="submit"
                    className="min-w-32"
                    disabled={canSubmitPassword || passwordMutation.isPending}
                  >
                    {passwordMutation.isPending ? 'Confirmando...' : 'Confirmar'}
                  </Button>
                  <Separator orientation="vertical" className="hidden h-8 bg-slate-800 md:block" />
                  <p className="text-xs text-slate-400">
                    A senha so e salva para o usuario logado e nunca altera CNPJ, empresa, UF ou cidade.
                  </p>
                </div>
              </form>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-800/80 bg-slate-900/40 p-4 text-sm text-slate-400">
                Clique em <span className="font-semibold text-slate-200">Esqueceu a senha?</span> para abrir o
                formulario nesta mesma pagina.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
