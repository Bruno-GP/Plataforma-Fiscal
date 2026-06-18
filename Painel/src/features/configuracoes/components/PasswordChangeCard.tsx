import { CheckCircle2, EyeOff, LockKeyhole } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';

import type { PasswordFormState } from '../types';

interface PasswordChangeCardProps {
  passwordForm: PasswordFormState;
}

export function PasswordChangeCard({ passwordForm }: PasswordChangeCardProps) {
  return (
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
          onClick={passwordForm.togglePasswordVisible}
          className="inline-flex items-center gap-2 text-sm font-semibold text-sky-300 underline-offset-4 hover:text-sky-200 hover:underline"
        >
          <EyeOff className="h-4 w-4" />
          Esqueceu a senha?
        </button>

        {passwordForm.formMessage ? (
          <div className="flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">Senha atualizada com sucesso.</p>
              <p className="mt-1 text-emerald-100/80">{passwordForm.formMessage}</p>
            </div>
          </div>
        ) : null}

        {passwordForm.passwordVisible ? (
          <form onSubmit={passwordForm.handlePasswordSubmit} className="space-y-4 rounded-2xl border border-slate-800/80 bg-slate-900/55 p-4">
            <div className="space-y-2">
              <Label htmlFor="new-password" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                Nova senha
              </Label>
              <Input
                id="new-password"
                type="password"
                value={passwordForm.newPassword}
                onChange={(event) => passwordForm.setNewPassword(event.target.value)}
                autoComplete="new-password"
                className="h-11 border-slate-700/80 bg-slate-950/60 text-slate-100 shadow-none focus-visible:ring-sky-400/70"
                aria-describedby={passwordForm.formError ? 'password-form-error' : undefined}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-password" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                Confirmar nova senha
              </Label>
              <Input
                id="confirm-password"
                type="password"
                value={passwordForm.confirmPassword}
                onChange={(event) => passwordForm.setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                className="h-11 border-slate-700/80 bg-slate-950/60 text-slate-100 shadow-none focus-visible:ring-sky-400/70"
                aria-describedby={passwordForm.formError ? 'password-form-error' : undefined}
              />
            </div>

            {passwordForm.formError ? (
              <div id="password-form-error" className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {passwordForm.formError}
              </div>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="submit"
                className="min-w-32"
                disabled={passwordForm.canSubmitPassword || passwordForm.isPending}
              >
                {passwordForm.isPending ? 'Confirmando...' : 'Confirmar'}
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
  );
}
