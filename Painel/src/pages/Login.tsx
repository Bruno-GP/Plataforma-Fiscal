import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [cnpj, setCnpj] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = isRegistering
        ? await register(email, password, cnpj)
        : await login(email, password);

      if (result.ok) {
        toast({
          title: isRegistering ? 'Cadastro realizado!' : 'Login realizado!',
          description: isRegistering
            ? 'Sua conta foi criada e você já pode acessar o painel.'
            : 'Bem-vindo ao painel de gestão.',
        });
        navigate('/dashboard');
        return;
      }
      toast({
        variant: 'destructive',
        title: isRegistering ? 'Erro no cadastro' : 'Erro no login',
        description:
          result.message ??
          (isRegistering ? 'Não foi possível cadastrar.' : 'Email ou senha inválidos.'),
      });
    } catch  {
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
    <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-primary-foreground text-xl font-bold">
            G
          </div>
          <CardTitle className="text-2xl">Painel de Gestão</CardTitle>
          <CardDescription>
            {isRegistering
              ? 'Crie sua conta para acessar o painel'
              : 'Entre com suas credenciais para acessar'}
          </CardDescription>
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
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {isRegistering && (
              <div className="space-y-2">
                <Label htmlFor="cnpj">CNPJ da empresa</Label>
                <Input
                  id="cnpj"
                  type="text"
                  placeholder="00.000.000/0000-00"
                  value={cnpj}
                  onChange={(e) => setCnpj(e.target.value)}
                  required
                />
              </div>
            )}
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isRegistering ? 'Cadastrar' : 'Entrar'}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm text-muted-foreground">
            {isRegistering ? 'Já tem conta?' : 'Ainda não tem conta?'}{' '}
            <button
              type="button"
              className="font-medium text-primary underline-offset-4 hover:underline"
              onClick={() => {
                setIsRegistering((prev) => !prev);
              }}
            >
              {isRegistering ? 'Fazer login' : 'Cadastre-se'}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
