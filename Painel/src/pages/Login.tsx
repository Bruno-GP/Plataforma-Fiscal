import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

import logo from '@/assets/Nova Logo.jpg';

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
        navigate('/analise-vendas');
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
    <div className="grid min-h-screen bg-muted/50 lg:grid-cols-[minmax(0,1.15fr)_minmax(24rem,0.85fr)]">
      <section className="flex min-h-[40vh] items-center justify-center overflow-hidden bg-white px-6 py-10 sm:px-10 lg:min-h-screen lg:px-12">
        <img
          src={logo}
          alt="Logo Gestao Pratica"
          className="h-auto w-full max-w-[36rem] object-contain lg:max-w-[44rem] xl:max-w-[52rem]"
        />
      </section>

      <section className="flex items-center justify-center px-4 py-8 sm:px-6 lg:min-h-screen lg:px-8">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Painel de Gestao</CardTitle>
            <CardDescription>Entre com suas credenciais para acessar</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="seu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Senha</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="********"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Entrar
              </Button>
            </form>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
