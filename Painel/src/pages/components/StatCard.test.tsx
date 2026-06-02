import { DollarSign } from "lucide-react";
import { describe, expect, it } from "vitest";

import { StatCard } from "@/pages/components/StatCard";
import { renderWithProviders, screen } from "@/test/utils/render";

describe("StatCard", () => {
  it("mostra estado de carregamento sem expor valor antigo", () => {
    renderWithProviders(
      <StatCard
        title="Receita"
        value="R$ 10.000,00"
        description="+12%"
        icon={DollarSign}
        trend="up"
        isLoading
      />,
    );

    expect(screen.getByText("Receita")).toBeInTheDocument();
    expect(screen.getByText("Carregando...")).toBeInTheDocument();
    expect(screen.getByText("--")).toBeInTheDocument();
    expect(screen.queryByText("R$ 10.000,00")).not.toBeInTheDocument();
  });

  it("renderiza valor e comparativo quando os dados estao prontos", () => {
    renderWithProviders(
      <StatCard
        title="Receita"
        value="R$ 10.000,00"
        description="+12%"
        icon={DollarSign}
        trend="up"
        isLoading={false}
      />,
    );

    expect(screen.getByText("R$ 10.000,00")).toBeInTheDocument();
    expect(screen.getByText(/\+12% vs mês anterior/i)).toBeInTheDocument();
  });
});
