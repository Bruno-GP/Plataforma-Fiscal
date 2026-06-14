import { useEffect, useState, type FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { atualizarSenhaConfiguracoes, fetchPerfilConfiguracoes } from '@/services/configuracoes';

import { formatCnpj } from '../helpers/formatCnpj';
import type { EmpresaConfiguracoesViewData, PasswordFormState } from '../types';
import { validatePasswordChange } from '../validations/passwordValidation';

export function useConfiguracoesPageData() {
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

  const empresa: EmpresaConfiguracoesViewData = {
    empresaNome: profileQuery.data?.empresa_nome || user?.name || 'Empresa nao identificada',
    cnpj: formatCnpj(profileQuery.data?.cnpj || user?.emitente_cnpj || ''),
    estado: profileQuery.data?.estado || 'Nao informado',
    cidade: profileQuery.data?.cidade || 'Nao informada',
    municipioId: profileQuery.data?.municipio_id || 'Nao informado',
    codigoIbge: profileQuery.data?.codigo_ibge || 'Nao informado',
    localidadeIncompleta: !profileQuery.isLoading && !profileQuery.isError && (
      !profileQuery.data?.estado ||
      !profileQuery.data?.cidade ||
      !profileQuery.data?.municipio_id ||
      !profileQuery.data?.codigo_ibge
    ),
  };

  const handlePasswordSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const validationError = validatePasswordChange(newPassword, confirmPassword);
    if (validationError) {
      setFormError(validationError);
      setFormMessage(null);
      return;
    }

    setFormError(null);
    passwordMutation.mutate(newPassword);
  };

  const togglePasswordVisible = () => {
    setPasswordVisible((current) => !current);
    setFormMessage(null);
    setFormError(null);
  };

  const passwordForm: PasswordFormState = {
    passwordVisible,
    newPassword,
    confirmPassword,
    formMessage,
    formError,
    isPending: passwordMutation.isPending,
    canSubmitPassword: passwordMutation.isPending || !passwordVisible,
    setNewPassword,
    setConfirmPassword,
    togglePasswordVisible,
    handlePasswordSubmit,
  };

  return {
    empresa,
    passwordForm,
    profileQuery,
  };
}
