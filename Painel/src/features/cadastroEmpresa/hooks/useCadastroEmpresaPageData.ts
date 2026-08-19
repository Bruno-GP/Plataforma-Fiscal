import { useDeferredValue, useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { fetchCnpjEnriquecimento } from '@/services/cnpj';
import { fetchMunicipiosPorUf, fetchUfsCatalogo, type MunicipioCatalogoItem, type UFCatalogoItem } from '@/services/municipios';

import { validateCatalogSelection } from '../validations/catalogSelection';
import type { OrigemFiscal } from '../types';

export function useCadastroEmpresaPageData() {
  const [empresaNome, setEmpresaNome] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [cnpj, setCnpj] = useState('');
  const [origemFiscal, setOrigemFiscal] = useState<OrigemFiscal>('xml');
  const [ufSearch, setUfSearch] = useState('');
  const [cidadeSearch, setCidadeSearch] = useState('');
  const [selectedUf, setSelectedUf] = useState<UFCatalogoItem | null>(null);
  const [selectedCidade, setSelectedCidade] = useState<MunicipioCatalogoItem | null>(null);
  const [formError, setFormError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [cnaeFiscal, setCnaeFiscal] = useState('');
  const [cnaeFiscalDescricao, setCnaeFiscalDescricao] = useState('');
  const [isBuscandoCnpj, setIsBuscandoCnpj] = useState(false);

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

  const handleCnpjChange = (valor: string) => {
    setCnpj(valor);
    setEmpresaNome('');
    setCnaeFiscal('');
    setCnaeFiscalDescricao('');
    setSelectedUf(null);
    setSelectedCidade(null);
  };

  const handleBuscarCnpj = async () => {
    const cnpjDigitos = cnpj.replace(/[^0-9A-Za-z]/g, '');
    if (cnpjDigitos.length !== 14) {
      toast({
        variant: 'destructive',
        title: 'CNPJ invalido',
        description: 'Informe um CNPJ com 14 caracteres antes de buscar.',
      });
      return;
    }

    setIsBuscandoCnpj(true);
    try {
      const dados = await fetchCnpjEnriquecimento(cnpjDigitos);

      if (dados.razao_social) {
        setEmpresaNome(dados.razao_social);
      }
      setCnaeFiscal(dados.cnae_fiscal ?? '');
      setCnaeFiscalDescricao(dados.cnae_fiscal_descricao ?? '');

      if (dados.estado) {
        setSelectedUf({ uf: dados.estado, label: dados.estado, quantidade_municipios: 0 });
      }
      if (dados.cidade && dados.municipio_id && dados.codigo_ibge && dados.estado) {
        setSelectedCidade({
          municipio_id: dados.municipio_id,
          codigo_ibge: dados.codigo_ibge,
          nome: dados.cidade,
          uf: dados.estado,
        });
      } else {
        setSelectedCidade(null);
      }

      toast({
        title: 'Dados encontrados',
        description: dados.cnae_fiscal_descricao ?? 'CNPJ consultado com sucesso.',
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Nao foi possivel buscar os dados do CNPJ.';
      toast({
        variant: 'destructive',
        title: 'Erro na busca',
        description: errorMessage,
      });
    } finally {
      setIsBuscandoCnpj(false);
    }
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
        origemFiscal,
        false,
        catalogSelection.selectedUf.uf,
        catalogSelection.selectedCidade.nome,
        catalogSelection.selectedCidade.municipio_id,
        catalogSelection.selectedCidade.codigo_ibge,
        cnaeFiscal,
        cnaeFiscalDescricao,
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
    origemFiscal,
    setOrigemFiscal,
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
    cnaeFiscal,
    cnaeFiscalDescricao,
    isBuscandoCnpj,
    handleBuscarCnpj,
    handleCnpjChange,
  };
}
