import type { UseQueryResult } from '@tanstack/react-query';
import type { FormEvent } from 'react';

import type { PerfilEmpresaConfiguracoes } from '@/services/configuracoes';

export interface EmpresaConfiguracoesViewData {
  empresaNome: string;
  cnpj: string;
  estado: string;
  cidade: string;
  municipioId: string;
  codigoIbge: string;
  localidadeIncompleta: boolean;
}

export interface PasswordFormState {
  passwordVisible: boolean;
  newPassword: string;
  confirmPassword: string;
  formMessage: string | null;
  formError: string | null;
  isPending: boolean;
  canSubmitPassword: boolean;
  setNewPassword: (value: string) => void;
  setConfirmPassword: (value: string) => void;
  togglePasswordVisible: () => void;
  handlePasswordSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export type PerfilConfiguracoesQuery = UseQueryResult<PerfilEmpresaConfiguracoes, Error>;
