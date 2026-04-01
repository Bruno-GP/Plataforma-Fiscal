import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';

export default function CadastroEmpresaInterno() {
  const [empresaNome, setEmpresaNome] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [cnpj, setCnpj] = useState('');
  const [temSped, setTemSped] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await register(empresaNome, email, password, cnpj, temSped, false);

      if (result.ok) {
        toast({
          title: 'Cadastro realizado!',
          description: 'Empresa e login cadastrados com sucesso. Redirecionando para o login...',
        });
        navigate('/login', { replace: true });
        return;
      }

      toast({
        variant: 'destructive',
        title: 'Erro no cadastro',
        description: result.message ?? 'Não foi possível cadastrar.',
      });
    } catch {
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: 'Ocorreu um erro ao cadastrar empresa e login.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Cadastro interno</CardTitle>
          <CardDescription>
            Uso exclusivo da equipe interna para cadastrar empresa e primeiro acesso.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="empresaNome">Nome da empresa</Label>
              <Input
                id="empresaNome"
                type="text"
                placeholder="Empresa Exemplo LTDA"
                value={empresaNome}
                onChange={(e) => setEmpresaNome(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cnpj">CNPJ</Label>
              <Input
                id="cnpj"
                type="text"
                placeholder="00.000.000/0000-00"
                value={cnpj}
                onChange={(e) => setCnpj(e.target.value)}
                inputMode="numeric"
                maxLength={18}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="temSped">Origem fiscal</Label>
              <select
                id="temSped"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={temSped ? 'sped' : 'xml'}
                onChange={(e) => setTemSped(e.target.value === 'sped')}
              >
                <option value="xml">Empresa usa XML</option>
                <option value="sped">Empresa usa SPED Fiscal</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email do login</Label>
              <Input
                id="email"
                type="email"
                placeholder="acesso@empresa.com"
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
                minLength={12}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Cadastrar empresa
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
