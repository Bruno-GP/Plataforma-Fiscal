import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { render, screen, within } from '@testing-library/react';

import { ContaAzulSection } from './ContaAzulSection';
import { useContaAzulIntegracao } from './useContaAzulIntegracao';
import type { UseContaAzulIntegracaoReturn } from './useContaAzulIntegracao';

const conectarMock = vi.fn();
const desconectarMock = vi.fn();
const sincronizarAgoraMock = vi.fn();
const refreshMock = vi.fn();

vi.mock('./useContaAzulIntegracao', () => ({
  useContaAzulIntegracao: vi.fn(),
}));

const mockedHook = vi.mocked(useContaAzulIntegracao);

const baseHookReturn: UseContaAzulIntegracaoReturn = {
  integracao: null,
  loading: false,
  sincronizando: false,
  error: null,
  tokenExpiraBreve: false,
  conectar: conectarMock,
  desconectar: desconectarMock,
  sincronizarAgora: sincronizarAgoraMock,
  refresh: refreshMock,
};

describe('ContaAzulSection', () => {
  it('renderiza estado nao conectado quando nao ha integracao', () => {
    mockedHook.mockReturnValue({ ...baseHookReturn, integracao: null });

    render(<ContaAzulSection empresaId={1} />);

    expect(screen.getByText(/integração não conectada/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /conectar ao conta azul/i })).toBeInTheDocument();
  });

  it('renderiza badge verde e painel de sincronizacao quando ativa', () => {
    mockedHook.mockReturnValue({
      ...baseHookReturn,
      integracao: {
        status: 'ATIVA',
        ultima_sync_em: '2026-07-27T17:32:00.000Z',
        token_expira_em: '2026-07-28T15:00:00.000Z',
        entidades: [
          { entidade: 'pessoas', registros_processados: 248, status: 'SUCESSO', fim_em: '2026-07-27T17:32:00.000Z' },
          { entidade: 'financeiro', registros_processados: 891, status: 'SUCESSO_PARCIAL', fim_em: '2026-07-27T17:32:00.000Z' },
        ],
      },
    });

    render(<ContaAzulSection empresaId={1} />);

    expect(screen.getByText(/ativa/i)).toBeInTheDocument();
    expect(screen.getByText(/ultima sincronizacao/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sincronizar agora na conta azul/i })).toBeInTheDocument();
  });

  it('abre modal ao clicar em desconectar e chama desconectar ao confirmar', async () => {
    const user = userEvent.setup();
    mockedHook.mockReturnValue({
      ...baseHookReturn,
      integracao: {
        status: 'ATIVA',
        ultima_sync_em: '2026-07-27T17:32:00.000Z',
        token_expira_em: null,
        entidades: [],
      },
    });

    render(<ContaAzulSection empresaId={1} />);

    await user.click(screen.getByRole('button', { name: /desconectar conta azul/i }));
    const dialog = screen.getByRole('dialog', { name: /desconectar conta azul/i });
    expect(dialog).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: /^desconectar$/i }));
    expect(desconectarMock).toHaveBeenCalledTimes(1);
  });

  it('exibe spinner no botao durante sincronizacao', () => {
    mockedHook.mockReturnValue({
      ...baseHookReturn,
      sincronizando: true,
      integracao: {
        status: 'ATIVA',
        ultima_sync_em: '2026-07-27T17:32:00.000Z',
        token_expira_em: null,
        entidades: [],
      },
    });

    const { container } = render(<ContaAzulSection empresaId={1} />);

    expect(screen.getByRole('button', { name: /sincronizando/i })).toBeDisabled();
    expect(container.querySelector('.animate-spin')).toBeTruthy();
  });

  it('exibe aviso de token quando a expiracao esta proxima', () => {
    mockedHook.mockReturnValue({
      ...baseHookReturn,
      tokenExpiraBreve: true,
      integracao: {
        status: 'ATIVA',
        ultima_sync_em: '2026-07-27T17:32:00.000Z',
        token_expira_em: '2026-07-28T15:00:00.000Z',
        entidades: [],
      },
    });

    render(<ContaAzulSection empresaId={1} />);

    expect(screen.getByText(/token expira em breve/i)).toBeInTheDocument();
  });
});
