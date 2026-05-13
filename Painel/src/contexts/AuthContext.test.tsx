import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { API_BASE_URL } from "@/services/api";
import { renderWithProviders, screen, waitFor } from "@/test/utils/render";
import { server } from "@/test/mocks/server";

function AuthStatus() {
  const { isReady, isAuthenticated, user } = useAuth();

  if (!isReady) {
    return <span>Carregando sessao</span>;
  }

  return <span>{isAuthenticated ? `Logado como ${user?.email}` : "Sem sessao"}</span>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    const storage = new Map<string, string>();

    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => {
          storage.set(key, value);
        },
        removeItem: (key: string) => {
          storage.delete(key);
        },
      },
    });
  });

  it("hidrata a sessao autenticada usando MSW", async () => {
    renderWithProviders(
      <AuthProvider>
        <AuthStatus />
      </AuthProvider>,
    );

    expect(await screen.findByText(/logado como teste@empresa.com/i)).toBeInTheDocument();
  });

  it("mostra estado anonimo quando a sessao remota retorna 401", async () => {
    server.use(
      http.get(`${API_BASE_URL}/auth/sessao`, () => HttpResponse.json({ detail: "unauthorized" }, { status: 401 })),
    );

    renderWithProviders(
      <AuthProvider>
        <AuthStatus />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Sem sessao")).toBeInTheDocument();
    });
  });
});
