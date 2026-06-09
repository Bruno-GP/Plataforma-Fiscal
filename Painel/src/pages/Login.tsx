import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowRight, Eye, Loader2, LockKeyhole, Mail, ShieldCheck, WalletCards } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await login(email, password);

      if (result.ok) {
        toast({
          title: 'Login realizado!',
          description: 'Bem-vindo ao painel de gestao.',
        });
        navigate(result.redirectTo ?? '/dashboard');
        return;
      }

      toast({
        variant: 'destructive',
        title: 'Erro no login',
        description: result.message ?? 'Email ou senha invalidos.',
      });
    } catch {
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: 'Ocorreu um erro ao fazer login.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-[#08111f] px-4 py-10 text-slate-100">
      <div className="absolute inset-0 opacity-70 [background-image:radial-gradient(circle_at_1px_1px,rgb(56_189_248_/_0.18)_1px,transparent_0)] [background-size:32px_32px]" />
      <div className="absolute right-0 top-0 h-80 w-80 translate-x-1/3 -translate-y-1/3 bg-sky-500/10 blur-3xl" />
      <div className="absolute bottom-0 left-0 h-72 w-72 -translate-x-1/3 translate-y-1/3 bg-emerald-500/10 blur-3xl" />

      <section className="relative z-10 flex w-full max-w-xl flex-col items-center">
        <div className="mb-9 flex flex-col items-center gap-4 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-sky-300/40 bg-sky-500 text-slate-950 shadow-[0_24px_60px_-28px_rgba(56,189,248,0.95)]">
            <WalletCards className="h-7 w-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-sky-300">Painel da Gestão Prática</h1>
            <p className="mt-2 text-base text-slate-300">Acesse a plataforma de análise estratégica do seu negócio</p>
          </div>
        </div>

        <Card className="w-full max-w-md overflow-hidden border-slate-600/80 bg-[#172033]/95">
          <div className="h-1 bg-sky-400" />
          <CardHeader className="pb-4 text-center">
            {/* <CardTitle className="text-xl">Painel de Gestao</CardTitle> */}
            <CardDescription>Entre com suas credenciais corporativas</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                  Email
                </Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="seu@exemplo.com.br"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="h-12 pl-10"
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                  Senha
                </Label>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="********"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="h-12 px-10"
                    required
                  />
                  <Eye className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                </div>
              </div>

              <div className="flex items-center justify-between gap-3 py-1 text-sm">
                <label className="flex items-center gap-2 text-slate-300">
                  <input type="checkbox" className="h-4 w-4 rounded border-slate-600 bg-slate-950 accent-sky-500" />
                  Lembrar de mim
                </label>
                <a href="/login" className="font-semibold text-sky-300 hover:text-sky-200">
                  Esqueci minha senha
                </a>
              </div>

              <Button type="submit" className="h-12 w-full text-base" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Entrar
                {!isLoading && <ArrowRight className="h-5 w-5" />}
              </Button>
            </form>
          </CardContent>
        </Card>

        <footer className="mt-8 space-y-4 text-center text-sm text-slate-400">
          <p>© 2026 Accounting Corp. Todos os direitos reservados.</p>
          <div className="flex items-center justify-center gap-5 text-slate-300">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" />
              Seguranca
            </span>
            <span>Suporte</span>
          </div>
        </footer>
      </section>
    </div>
  );
}
