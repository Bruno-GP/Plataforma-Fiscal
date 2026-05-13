import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DetalhamentoVendasModeSelector } from "@/pages/components/DetalhamentoVendasModeSelector";
import { renderWithProviders, screen } from "@/test/utils/render";

describe("DetalhamentoVendasModeSelector", () => {
  it("permite alternar o modo de detalhamento por botoes acessiveis", async () => {
    const onChange = vi.fn();

    renderWithProviders(<DetalhamentoVendasModeSelector detailMode="nota" onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /detalhamento por regiao/i }));

    expect(onChange).toHaveBeenCalledWith("regiao");
  });
});
