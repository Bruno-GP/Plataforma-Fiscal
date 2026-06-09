import { Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { MainLayout } from '@/components/layout/MainLayout';
import { renderWithProviders, screen } from '@/test/utils/render';

const lockedUser = {
  id: '1',
  name: 'Empresa Teste',
  email: 'teste@empresa.com',
  emitente_cnpj: '12345678000199',
  tem_sped: false,
  tem_xml_importado_valido: false,
};

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: lockedUser,
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
      cnpj_emitente: lockedUser.emitente_cnpj,
      total_pendentes: 0,
      possui_pendentes: false,
    }),
  ),
}));

describe('MainLayout onboarding', () => {
  it('redireciona para importacao-xml quando ainda nao existe XML valido', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/importacao-xml" element={<div>Importacao XML liberada</div>} />
        <Route
          path="*"
          element={
            <MainLayout>
              <div>Conteudo protegido</div>
            </MainLayout>
          }
        />
      </Routes>,
      { route: '/analise-vendas' },
    );

    expect(await screen.findByText(/importacao xml liberada/i)).toBeInTheDocument();
    expect(screen.queryByText(/conteudo protegido/i)).not.toBeInTheDocument();
  });
});
