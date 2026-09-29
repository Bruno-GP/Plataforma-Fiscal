import { Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { MainLayout } from '@/components/layout/MainLayout';
import { renderWithProviders, screen } from '@/test/utils/render';

const contaAzulUser = {
  id: '1',
  name: 'Empresa Teste',
  email: 'teste@empresa.com',
  emitente_cnpj: '12345678000199',
  tem_sped: false,
  tem_conta_azul: true,
  tem_xml_importado_valido: false,
};

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: contaAzulUser,
    isAuthenticated: true,
    isReady: true,
    refreshSession: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock('@/services/nfe', () => ({
  consultarPendenciasXmlImportados: vi.fn(() =>
    Promise.resolve({
      status: 'ok',
      cnpj_emitente: contaAzulUser.emitente_cnpj,
      total_pendentes: 0,
      possui_pendentes: false,
    }),
  ),
}));

describe('MainLayout conta azul', () => {
  it('redireciona rotas fora do dashboard para /dashboard quando tem_conta_azul', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/dashboard" element={<div>Dashboard liberado</div>} />
        <Route
          path="*"
          element={
            <MainLayout>
              <div>Conteudo protegido</div>
            </MainLayout>
          }
        />
      </Routes>,
      { route: '/configuracoes' },
    );

    expect(await screen.findByText(/dashboard liberado/i)).toBeInTheDocument();
    expect(screen.queryByText(/conteudo protegido/i)).not.toBeInTheDocument();
  });

  it('libera /dashboard quando tem_conta_azul', async () => {
    renderWithProviders(
      <Routes>
        <Route
          path="/dashboard"
          element={
            <MainLayout>
              <div>Conteudo protegido</div>
            </MainLayout>
          }
        />
      </Routes>,
      { route: '/dashboard' },
    );

    expect(await screen.findByText(/conteudo protegido/i)).toBeInTheDocument();
  });
});
