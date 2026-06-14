import { useDeferredValue, useState, type FormEvent } from 'react';
import { Loader2 } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  fetchMunicipiosPorUf,
  fetchUfsCatalogo,
  type MunicipioCatalogoItem,
  type UFCatalogoItem,
} from '@/services/municipios';
import { CatalogoCombobox } from '../features/cadastroEmpresa/components/CatalogoCombobox';
import { TextInputField } from '../features/cadastroEmpresa/components/TextInputField';
import { getCidadeEmptyMessage } from '../features/cadastroEmpresa/helpers/cidadeMessages';
import { validateCatalogSelection } from '../features/cadastroEmpresa/validations/catalogSelection';

export default function CadastroEmpresaInterno() {
  const [empresaNome, setEmpresaNome] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [cnpj, setCnpj] = useState('');
  const [temSped, setTemSped] = useState(false);
  const [ufSearch, setUfSearch] = useState('');
  const [cidadeSearch, setCidadeSearch] = useState('');
  const [selectedUf, setSelectedUf] = useState<UFCatalogoItem | null>(null);
  const [selectedCidade, setSelectedCidade] = useState<MunicipioCatalogoItem | null>(null);
  const [formError, setFormError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const deferredUfSearch = useDeferredValue(ufSearch);
  const deferredCidadeSearch = useDeferredValue(cidadeSearch);

  const ufsQuery = useQuery({
    queryKey: ['municipios-ufs', deferredUfSearch],
    queryFn: () => fetchUfsCatalogo(deferredUfSearch),
  });

  const cidadesQuery = useQuery({
    queryKey: ['municipios-cidades', selectedUf?.uf ?? '', deferredCidadeSearch],
    queryFn: () => fetchMunicipiosPorUf(selectedUf?.uf ?? '', deferredCidadeSearch),
    enabled: Boolean(selectedUf?.uf),
  });

  const handleUfSelect = (ufItem: UFCatalogoItem) => {
    setSelectedUf(ufItem);
    setUfSearch('');
    setSelectedCidade(null);
    setCidadeSearch('');
    setFormError('');
  };

  const handleCidadeSelect = (cidadeItem: MunicipioCatalogoItem) => {
    setSelectedCidade(cidadeItem);
    setCidadeSearch('');
    setFormError('');
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    const catalogSelection = validateCatalogSelection(selectedUf, selectedCidade);
    if (catalogSelection.isValid === false) {
      setFormError(catalogSelection.error);
      return;
    }

    setFormError('');
    setIsLoading(true);

    try {
      const result = await register(
        empresaNome,
        email,
        password,
        cnpj,
        temSped,
        false,
        catalogSelection.selectedUf.uf,
        catalogSelection.selectedCidade.nome,
        catalogSelection.selectedCidade.municipio_id,
        catalogSelection.selectedCidade.codigo_ibge,
      );

      if (result.ok) {
        toast({
          title: 'Cadastro realizado!',
          description: 'Empresa e login cadastrados com sucesso. Redirecionando para o login...',
        });
        navigate('/login', { replace: true });
        return;
      }

      const errorMessage = result.message ?? 'Nao foi possivel cadastrar.';
      toast({
        variant: 'destructive',
        title: 'Erro no cadastro',
        description: errorMessage,
      });
      setFormError(errorMessage);
    } catch {
      const errorMessage = 'Ocorreu um erro ao cadastrar empresa e login.';
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: errorMessage,
      });
      setFormError(errorMessage);
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
            <TextInputField
              id="empresaNome"
              label="Nome da empresa"
              type="text"
              placeholder="Empresa Exemplo LTDA"
              value={empresaNome}
              onChange={(e) => setEmpresaNome(e.target.value)}
            />
            <TextInputField
              id="cnpj"
              label="CNPJ"
              type="text"
              placeholder="00.000.000/0000-00"
              value={cnpj}
              onChange={(e) => setCnpj(e.target.value)}
              inputMode="numeric"
              maxLength={18}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <CatalogoCombobox
                label="UF da empresa"
                placeholder="Pesquisar UF"
                searchPlaceholder="Digite para pesquisar a UF"
                emptyMessage={ufsQuery.isLoading ? 'Carregando...' : 'Nenhuma UF encontrada.'}
                selectedLabel={selectedUf?.uf ?? ''}
                searchValue={ufSearch}
                onSearchValueChange={setUfSearch}
                onSelectItem={handleUfSelect}
                items={ufsQuery.data ?? []}
                isLoading={ufsQuery.isLoading}
                itemLabel={(item) => item.uf}
                itemDescription={(item) => `${item.quantidade_municipios} municipios`}
              />
              <CatalogoCombobox
                label="Cidade da empresa"
                placeholder={selectedUf ? 'Pesquisar cidade' : 'Selecione a UF primeiro'}
                searchPlaceholder="Digite para pesquisar a cidade"
                emptyMessage={getCidadeEmptyMessage(selectedUf, cidadesQuery.isLoading)}
                disabled={!selectedUf}
                selectedLabel={selectedCidade?.nome ?? ''}
                searchValue={cidadeSearch}
                onSearchValueChange={setCidadeSearch}
                onSelectItem={handleCidadeSelect}
                items={cidadesQuery.data ?? []}
                isLoading={cidadesQuery.isLoading}
                itemLabel={(item) => item.nome}
                itemDescription={(item) => `${item.uf} • ${item.codigo_ibge}`}
              />
            </div>
            {formError ? (
              <Alert variant="destructive">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : null}
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
            <TextInputField
              id="email"
              label="Email do login"
              type="email"
              placeholder="acesso@empresa.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextInputField
              id="password"
              label="Senha"
              type="password"
              placeholder="********"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={12}
            />
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
