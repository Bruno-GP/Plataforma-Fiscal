import { useDeferredValue, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { fetchMunicipiosPorUf, fetchUfsCatalogo, type MunicipioCatalogoItem, type UFCatalogoItem } from '@/services/municipios';

import { validateCatalogSelection } from '../validations/catalogSelection';

export function useCadastroEmpresaPageData() {
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

  return {
    empresaNome,
    setEmpresaNome,
    email,
    setEmail,
    password,
    setPassword,
    cnpj,
    setCnpj,
    temSped,
    setTemSped,
    ufSearch,
    setUfSearch,
    cidadeSearch,
    setCidadeSearch,
    selectedUf,
    selectedCidade,
    formError,
    isLoading,
    ufsQuery,
    cidadesQuery,
    handleUfSelect,
    handleCidadeSelect,
    handleSubmit,
  };
}
