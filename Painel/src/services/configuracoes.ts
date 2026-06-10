import { API_BASE_URL, apiFetch } from '@/services/api';

interface ApiErrorDetail {
  detail?: string | { msg?: string }[];
}

const extractApiErrorMessage = (errorData: ApiErrorDetail | null, fallback: string) => {
  if (!errorData?.detail) {
    return fallback;
  }

  if (typeof errorData.detail === 'string') {
    return errorData.detail;
  }

  const firstDetail = errorData.detail[0];
  if (firstDetail?.msg) {
    return firstDetail.msg;
  }

  return fallback;
};

export interface PerfilEmpresaConfiguracoes {
  status: string;
  login_id: number;
  empresa_id: number;
  cnpj: string;
  empresa_nome: string;
  estado: string;
  cidade: string;
}

export interface AtualizarSenhaResponse {
  status: string;
  message: string;
}

export const fetchPerfilConfiguracoes = async () => {
  const response = await apiFetch(`${API_BASE_URL}/auth/perfil`);

  if (!response.ok) {
    const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    throw new Error(extractApiErrorMessage(errorData, 'Não foi possível carregar os dados da empresa.'));
  }

  return response.json() as Promise<PerfilEmpresaConfiguracoes>;
};

export const atualizarSenhaConfiguracoes = async (novaSenha: string) => {
  const response = await apiFetch(`${API_BASE_URL}/auth/senha`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      nova_senha: novaSenha,
    }),
  });

  if (!response.ok) {
    const errorData = (await response.json().catch(() => null)) as ApiErrorDetail | null;
    throw new Error(extractApiErrorMessage(errorData, 'Não foi possível atualizar a senha.'));
  }

  return response.json() as Promise<AtualizarSenhaResponse>;
};
