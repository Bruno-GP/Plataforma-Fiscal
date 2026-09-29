import { describe, expect, it, vi } from 'vitest';

import ContaAzulDashboard from '@/pages/ContaAzulDashboard';
import { renderWithProviders, screen } from '@/test/utils/render';

const user = {
  id: '1',
  name: 'Empresa Teste',
  email: 'teste@empresa.com',
  emitente_cnpj: '12345678000199',
  tem_conta_azul: true,
};

const { fetchContaAzulKpisMock } = vi.hoisted(() => ({
  fetchContaAzulKpisMock: vi.fn(),
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user,
    isAuthenticated: true,
    isReady: true,
    refreshSession: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock('@/services/contaAzul', () => ({
  fetchContaAzulKpis: fetchContaAzulKpisMock,
}));

describe('ContaAzulDashboard', () => {
  it('mostra o faturamento do mes mais recente', async () => {
    fetchContaAzulKpisMock.mockResolvedValueOnce({
      resultados: [{ mes: '2026-01-01', receita_total: 12345.67 }],
    });

    renderWithProviders(<ContaAzulDashboard />);

    expect(await screen.findByText('Faturamento Mensal')).toBeInTheDocument();
    expect(await screen.findByText(/12\.345,67/)).toBeInTheDocument();
  });

  it('mostra erro quando a consulta falha', async () => {
    fetchContaAzulKpisMock.mockRejectedValueOnce(new Error('Falha ao consultar KPIs da Conta Azul.'));

    renderWithProviders(<ContaAzulDashboard />);

    expect(await screen.findByText('Erro ao carregar indicadores')).toBeInTheDocument();
  });
});
