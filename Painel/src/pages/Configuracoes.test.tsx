import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import Configuracoes from '@/pages/Configuracoes';
import { renderWithProviders, screen, waitFor } from '@/test/utils/render';

vi.mock('@/features/cadastroEmpresa/components/ContaAzulSection', () => ({
  ContaAzulSection: () => <div data-testid="conta-azul-section" />,
}));

describe('pagina de configuracoes', () => {
  it('exibe os dados da empresa como somente leitura e permite atualizar a senha', async () => {
    const user = userEvent.setup();

    renderWithProviders(<Configuracoes />);

    expect(await screen.findByRole('heading', { level: 3, name: /dados da empresa/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: /alteracao de senha/i })).toBeInTheDocument();
    expect(await screen.findByDisplayValue('12.345.678/0001-99')).toBeInTheDocument();
    expect(screen.getByLabelText(/^nome da empresa$/i)).toHaveValue('Empresa Teste');
    expect(screen.getByLabelText(/^estado \/ uf$/i)).toHaveValue('SP');
    expect(screen.getByLabelText(/^cidade$/i)).toHaveValue('Sao Paulo');

    await user.click(screen.getByRole('button', { name: /esqueceu a senha\?/i }));
    await user.type(screen.getByLabelText(/^nova senha$/i), 'SenhaNova@123');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'SenhaNova@123');
    await user.click(screen.getByRole('button', { name: /confirmar/i }));

    expect((await screen.findAllByText(/senha atualizada com sucesso/i)).length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(screen.queryByLabelText(/^nova senha$/i)).not.toBeInTheDocument();
    });
  });

  it('valida se as senhas conferem antes de chamar o endpoint', async () => {
    const user = userEvent.setup();

    renderWithProviders(<Configuracoes />);

    await screen.findByRole('heading', { level: 3, name: /dados da empresa/i });
    await user.click(screen.getByRole('button', { name: /esqueceu a senha\?/i }));
    await user.type(screen.getByLabelText(/^nova senha$/i), 'SenhaNova@123');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'SenhaNova@124');
    await user.click(screen.getByRole('button', { name: /confirmar/i }));

    expect(await screen.findByText(/as duas senhas precisam ser iguais/i)).toBeInTheDocument();
  });
});
