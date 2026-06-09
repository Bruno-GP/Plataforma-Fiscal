import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Login from "@/pages/Login";
import { renderWithProviders, screen, waitFor } from "@/test/utils/render";

const navigateMock = vi.fn();
const toastMock = vi.fn();
const loginMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    login: loginMock,
  }),
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({
    toast: toastMock,
  }),
}));

describe("Login", () => {
  it("envia credenciais e navega para a analise de vendas quando o login tem sucesso", async () => {
    loginMock.mockResolvedValueOnce({ ok: true, redirectTo: "/dashboard" });

    renderWithProviders(<Login />, { route: "/login" });

    await userEvent.type(screen.getByLabelText(/email/i), "teste@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha/i), "SenhaForte123!");
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith("teste@empresa.com", "SenhaForte123!");
    });
    expect(navigateMock).toHaveBeenCalledWith("/dashboard");
    expect(toastMock).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Login realizado!",
      }),
    );
  });

  it("exibe feedback de erro quando a API rejeita as credenciais", async () => {
    loginMock.mockResolvedValueOnce({ ok: false, message: "Email ou senha invalidos." });

    renderWithProviders(<Login />, { route: "/login" });

    await userEvent.type(screen.getByLabelText(/email/i), "erro@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha/i), "senha-incorreta");
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: "destructive",
          title: "Erro no login",
          description: "Email ou senha invalidos.",
        }),
      );
    });
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
