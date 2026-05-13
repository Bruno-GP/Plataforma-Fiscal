import { describe, expect, it, vi } from "vitest";

import AnaliseCompras from "@/pages/AnaliseCompras";
import AnaliseFiscalCfop from "@/pages/AnaliseFiscalCfop";
import AnaliseVendas from "@/pages/AnaliseVendas";
import CadastroEmpresa from "@/pages/CadastroEmpresa";
import Clientes from "@/pages/Clientes";
import DetalhamentoCompras from "@/pages/DetalhamentoCompras";
import DetalhamentoVendas from "@/pages/DetalhamentoVendas";
import ImportacaoSPED from "@/pages/ImportacaoSPED";
import ImportacaoXML from "@/pages/ImportacaoXML";
import Inconsistencias from "@/pages/Inconsistencias";
import ReformaTributaria from "@/pages/ReformaTributaria";
import RelatoriosIA from "@/pages/RelatoriosIA";
import { renderWithProviders, screen, waitFor } from "@/test/utils/render";

const mockUser = {
  id: "1",
  name: "Empresa Teste",
  email: "teste@empresa.com",
  emitente_cnpj: "12345678000199",
  tem_sped: false,
};

const loginMock = vi.fn();
const registerMock = vi.fn();
const logoutMock = vi.fn();
const toastMock = vi.fn();
const navigateMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: mockUser,
    login: loginMock,
    register: registerMock,
    logout: logoutMock,
    isAuthenticated: true,
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: toastMock }),
}));

vi.mock("@/components/reports/IAReportPreview", () => ({
  IAReportPreview: ({ report }: { report: string }) => <div>Preview IA: {report}</div>,
}));

vi.mock("@/pages/components/SalesRegionCityMap", () => ({
  SalesRegionCityMap: ({ totalFaturamento }: { totalFaturamento: number }) => (
    <section aria-label="Mapa de vendas">Mapa carregado: {totalFaturamento}</section>
  ),
}));

vi.mock("@/pages/components/EvolucaoChart", () => ({
  EvolucaoChart: ({ title }: { title: string }) => <section aria-label={title}>{title}</section>,
}));

const makeKpiResult = (month: number, multiplier = 1) => ({
  periodo_ano: 2026,
  periodo_mes: month,
  kpis: {
    total_vendas: 10_000 * multiplier,
    quantidade_notas: 10 * multiplier,
    ticket_medio: 1_000,
    maior_nota: 2_000,
    menor_nota: 100,
    total_icms: 900 * multiplier,
    total_ipi: 120 * multiplier,
    total_pis: 90 * multiplier,
    total_cofins: 400 * multiplier,
    top_clientes: Array.from({ length: 8 }, (_, index) => ({
      cliente: `Cliente ${index + 1}`,
      valor_total: 1_000 - index * 50,
      percentual: 20 - index,
    })),
    top_produtos: Array.from({ length: 8 }, (_, index) => ({
      produto: `Produto ${index + 1}`,
      valor_total: 800 - index * 35,
    })),
    top_cidades: Array.from({ length: 8 }, (_, index) => ({
      cidade: `Cidade ${index + 1}`,
      valor_total: 600 - index * 25,
    })),
  },
});

const kpisResponse = {
  status: "ok",
  total: 24,
  resultados: Array.from({ length: 12 }, (_, index) => makeKpiResult(index + 1, index + 1)),
};

const comprasResumo = {
  status: "ok",
  emitente_cnpj: mockUser.emitente_cnpj,
  total_comprado: 72_500,
  total_tributos_reforma: 4_200,
  top_fornecedores_valor: Array.from({ length: 12 }, (_, index) => ({
    fornecedor: `Fornecedor ${index + 1}`,
    valor_total: 9_000 - index * 300,
    quantidade_documentos: 12 - index,
  })),
  top_fornecedores_quantidade: Array.from({ length: 12 }, (_, index) => ({
    fornecedor: `Fornecedor ${index + 1}`,
    valor_total: 7_000 - index * 250,
    quantidade_documentos: 14 - index,
  })),
  top_produtos_valor: Array.from({ length: 12 }, (_, index) => ({
    produto: `Insumo ${index + 1}`,
    valor_total: 6_000 - index * 200,
    quantidade_total: 25 - index,
  })),
  top_produtos_quantidade: Array.from({ length: 12 }, (_, index) => ({
    produto: `Insumo ${index + 1}`,
    valor_total: 5_000 - index * 150,
    quantidade_total: 40 - index,
  })),
};

const dashboardComprasResponse = {
  status: "ok",
  emitente_cnpj: mockUser.emitente_cnpj,
  anos_disponiveis: [2026, 2025],
  resumo_atual: comprasResumo,
  resumo_anterior: { ...comprasResumo, total_comprado: 55_000, total_tributos_reforma: 2_000 },
  serie_mensal: Array.from({ length: 12 }, (_, index) => ({
    periodo_ano: 2026,
    periodo_mes: index + 1,
    total_comprado: 4_000 + index * 1_000,
  })),
};

const dashboardVendasResponse = {
  status: "ok",
  emitente_cnpj: mockUser.emitente_cnpj,
  anos_disponiveis: [2026, 2025],
  resumo_atual: {
    total_vendido: 125_000,
    quantidade_notas: 80,
    total_impostos: 18_300,
    total_tributos_reforma: 5_600,
    ticket_medio: 1_562.5,
    top_clientes: Array.from({ length: 10 }, (_, index) => ({
      cliente: `Cliente ${index + 1}`,
      valor_total: 20_000 - index * 1_000,
    })),
    top_produtos: Array.from({ length: 10 }, (_, index) => ({
      produto: `Produto ${index + 1}`,
      valor_total: 15_000 - index * 900,
    })),
    top_cidades: Array.from({ length: 10 }, (_, index) => ({
      cidade: `Cidade ${index + 1}`,
      valor_total: 12_000 - index * 750,
    })),
  },
  resumo_anterior: {
    total_vendido: 100_000,
    quantidade_notas: 70,
    total_impostos: 15_000,
    total_tributos_reforma: 4_000,
    ticket_medio: 1_428.57,
    top_clientes: [],
    top_produtos: [],
    top_cidades: [],
  },
  serie_mensal: Array.from({ length: 12 }, (_, index) => ({
    periodo_ano: 2026,
    periodo_mes: index + 1,
    total_vendido: 8_000 + index * 1_200,
    quantidade_notas: 6 + index,
    total_impostos: 900 + index * 100,
  })),
};

const analiseVendasResponse = {
  status: "ok",
  emitente_cnpj: mockUser.emitente_cnpj,
  total_vendido: 125_000,
  total_tributos_reforma: 5_600,
  top_cfops_valor: [{ cfop: "5102", descricao: "Venda", valor_total: 90_000, participacao_percentual: 72 }],
  top_regioes_valor: [{ regiao: "Sudeste", valor_total: 90_000, quantidade_documentos: 50 }],
  top_cidades_valor: [{ cidade: "Sao Paulo", uf: "SP", valor_total: 50_000, quantidade_documentos: 25 }],
  top_clientes_valor: [{ cliente: "Cliente Estrategico", valor_total: 45_000, quantidade_documentos: 10 }],
  top_clientes_quantidade: [{ cliente: "Cliente Estrategico", valor_total: 45_000, quantidade_documentos: 10 }],
  top_produtos_valor: [{ produto: "Produto Fiscal", valor_total: 35_000, quantidade_total: 15 }],
  top_produtos_quantidade: [{ produto: "Produto Fiscal", valor_total: 35_000, quantidade_total: 15 }],
};

const analiseComprasResponse = {
  ...comprasResumo,
  relatorio_ia: "Relatorio executivo de compras gerado para o teste.",
};

const analiseClientesResponse = {
  status: "ok",
  emitente_cnpj: mockUser.emitente_cnpj,
  total_vendido: 125_000,
  total_clientes: 8,
  top_clientes_valor: [{ cliente: "Cliente Estrategico", valor_total: 45_000, quantidade_documentos: 10, ticket_medio: 4_500, percentual_participacao: 36 }],
  top_clientes_quantidade: [{ cliente: "Cliente Estrategico", valor_total: 45_000, quantidade_documentos: 10, ticket_medio: 4_500, percentual_participacao: 36 }],
  relatorio_ia: "Relatorio executivo de clientes gerado para o teste.",
};

const fiscalCfopResponse = {
  status: "ok",
  emitente_cnpj: mockUser.emitente_cnpj,
  total_movimentado: 125_000,
  total_tributos_reforma: 5_600,
  quantidade_documentos: 80,
  quantidade_cfops: 4,
  top_categorias: [{ categoria: "Venda", valor_total: 90_000, participacao_percentual: 72, quantidade_documentos: 60 }],
  top_cfops: [{ cfop: "5102", descricao: "Venda de mercadoria", valor_total: 90_000, participacao_percentual: 72 }],
};

const hierarchyResponse = {
  status: "ok",
  emitente_cnpj: mockUser.emitente_cnpj,
  nivel_atual: "estado",
  offset: 0,
  limite: 50,
  total_registros_nivel: 2,
  possui_mais_registros: false,
  total_faturamento: 125_000,
  total_impostos: 18_300,
  percentual_impostos_sobre_faturamento: 14.64,
  quantidade_documentos: 80,
  total_estados: 2,
  total_cidades: 3,
  total_ncms: 4,
  total_produtos: 5,
  hierarquia: [],
  itens_nivel_atual: [],
  por_estado: [
    { estado: "SP", faturamento: 90_000, imposto_valor: 12_000, imposto_percentual: 13.33 },
    { estado: "RJ", faturamento: 35_000, imposto_valor: 6_300, imposto_percentual: 18 },
  ],
  por_cidade: [],
  por_ncm: [],
  por_produto: [],
};

const notasDetalhadasResponse = {
  status: "ok",
  total: 2,
  notas: [
    {
      id: 1,
      numero_nf: "1001",
      emitente_cnpj: mockUser.emitente_cnpj,
      modelo: "55",
      data_emissao: "2026-03-10",
      natureza_operacao: "Venda",
      destinatario_documento: "11111111000199",
      destinatario_nome: "Cliente Estrategico",
      destinatario_cidade: "Sao Paulo",
      destinatario_uf: "SP",
      valor_produtos: 10_000,
      valor_desconto: 0,
      valor_frete: 0,
      valor_icms: 1_200,
      valor_ipi: 0,
      valor_pis: 165,
      valor_cofins: 760,
      valor_total_nf: 10_000,
      itens: [
        {
          item_numero: 1,
          produto_codigo: "P001",
          descricao: "Produto Fiscal",
          ncm: "01012100",
          descricao_ncm: "Animais vivos",
          cfop: "5102",
          quantidade: 2,
          valor_unitario: 5_000,
          valor_total: 10_000,
          tributos: [],
        },
      ],
    },
    {
      id: 2,
      numero_nf: "1002",
      emitente_cnpj: mockUser.emitente_cnpj,
      modelo: "55",
      data_emissao: "2026-03-11",
      natureza_operacao: "Compra",
      destinatario_documento: "22222222000199",
      destinatario_nome: "Fornecedor 1",
      destinatario_cidade: "Rio de Janeiro",
      destinatario_uf: "RJ",
      valor_produtos: 8_000,
      valor_desconto: 0,
      valor_frete: 0,
      valor_icms: 900,
      valor_ipi: 0,
      valor_pis: 120,
      valor_cofins: 550,
      valor_total_nf: 8_000,
      itens: [],
    },
  ],
};

vi.mock("@/services/nfe", async () => {
  const fiscal = await vi.importActual<typeof import("@/services/fiscal")>("@/services/fiscal");
  return {
    parseDecimal: fiscal.parseDecimal,
    fetchNfeKpis: vi.fn(() => Promise.resolve(kpisResponse)),
    fetchNfeDashboardCompras: vi.fn(() => Promise.resolve(dashboardComprasResponse)),
    fetchNfeDashboardVendas: vi.fn(() => Promise.resolve(dashboardVendasResponse)),
    fetchNfeAnaliseCompras: vi.fn(() => Promise.resolve(analiseComprasResponse)),
    fetchNfeAnaliseVendas: vi.fn(() => Promise.resolve(analiseVendasResponse)),
    fetchNfeAnaliseClientes: vi.fn(() => Promise.resolve(analiseClientesResponse)),
    fetchNfeAnaliseFiscalCfop: vi.fn(() => Promise.resolve(fiscalCfopResponse)),
    fetchNfeAnaliseFiscalHierarquica: vi.fn(() => Promise.resolve(hierarchyResponse)),
    fetchNfeNotasDetalhadas: vi.fn(() => Promise.resolve(notasDetalhadasResponse)),
    consultarPendenciasXmlImportados: vi.fn(() =>
      Promise.resolve({ status: "ok", cnpj_emitente: mockUser.emitente_cnpj, total_pendentes: 0, possui_pendentes: false }),
    ),
    importarXmlArquivos: vi.fn(),
    listarCnpjsXmlImportados: vi.fn(() => [mockUser.emitente_cnpj]),
    processarXmlsImportados: vi.fn(),
  };
});

vi.mock("@/services/sped", () => ({
  fetchSpedKpis: vi.fn(() => Promise.resolve(kpisResponse)),
  fetchSpedDashboardCompras: vi.fn(() => Promise.resolve(dashboardComprasResponse)),
  fetchSpedDashboardVendas: vi.fn(() => Promise.resolve(dashboardVendasResponse)),
  fetchSpedAnaliseCompras: vi.fn(() => Promise.resolve(analiseComprasResponse)),
  fetchSpedAnaliseVendas: vi.fn(() => Promise.resolve(analiseVendasResponse)),
  fetchSpedAnaliseClientes: vi.fn(() => Promise.resolve(analiseClientesResponse)),
  fetchSpedAnaliseFiscalCfop: vi.fn(() => Promise.resolve(fiscalCfopResponse)),
  fetchSpedAnaliseFiscalHierarquica: vi.fn(() => Promise.resolve(hierarchyResponse)),
  consultarPendenciasSped: vi.fn(() =>
    Promise.resolve({ status: "ok", cnpj_emitente: mockUser.emitente_cnpj, total_pendentes: 0, possui_pendentes: false }),
  ),
  importarSpedArquivo: vi.fn(),
  processarSpedsImportados: vi.fn(),
}));

vi.mock("@/services/jobs", () => ({
  fetchJobs: vi.fn(() => Promise.resolve({ status: "ok", total: 0, resultados: [] })),
  waitForJob: vi.fn(),
}));

vi.mock("@/services/operations", () => ({
  readFiscalOperations: vi.fn(() => []),
  saveFiscalOperation: vi.fn(),
}));

vi.mock("@/services/reformaTributaria", async () => {
  const actual = await vi.importActual<typeof import("@/services/reformaTributaria")>("@/services/reformaTributaria");
  return {
    ...actual,
    fetchReformaTributos: vi.fn(() =>
      Promise.resolve({
        status: "ok",
        total: 3,
        resultados: [
          { codigo: "CBS", nome: "Contribuicao sobre Bens e Servicos", tipo: "reforma", aliquota_padrao: 0.9, vigencia_inicio: "2026-01-01", status: "ativo" },
          { codigo: "IBS", nome: "Imposto sobre Bens e Servicos", tipo: "reforma", aliquota_padrao: 0.1, vigencia_inicio: "2026-01-01", status: "ativo" },
        ],
      }),
    ),
    fetchReformaApuracao: vi.fn(() =>
      Promise.resolve({
        status: "ok",
        total: 2,
        resultados: [
          {
            id: 1,
            tributo_codigo: "CBS",
            tributo_nome: "Contribuicao sobre Bens e Servicos",
            periodo_ano: 2026,
            periodo_mes: 3,
            total_debitos: 900,
            total_creditos: 150,
            ajustes_debito: 0,
            ajustes_credito: 0,
            saldo_apurado: 750,
            status: "apurado",
          },
        ],
      }),
    ),
    fetchReformaMemoriaCalculo: vi.fn(() =>
      Promise.resolve({
        status: "ok",
        total: 1,
        resultados: [
          {
            id: 1,
            tributo_codigo: "CBS",
            tributo_nome: "Contribuicao sobre Bens e Servicos",
            periodo_ano: 2026,
            periodo_mes: 3,
            etapa_calculo: "Debito",
            fonte_dados: "NFe",
            base_calculo: 100_000,
            aliquota: 0.9,
            valor_debito: 900,
            valor_credito: 0,
            valor_tributo: 900,
            formula_calculo: "base * aliquota",
            hash_calculo: "hash-cbs",
          },
        ],
      }),
    ),
    backfillReformaTributaria: vi.fn(() => Promise.resolve({ status: "ok", periodos_processados: 1 })),
  };
});

describe("renderizacao por pagina do frontend", () => {
  it("renderiza a analise de vendas com rankings, grafico e mapa a partir de uma massa grande", async () => {
    renderWithProviders(<AnaliseVendas />);

    expect(await screen.findByRole("heading", { level: 1, name: /^vendas$/i })).toBeInTheDocument();
    expect(await screen.findByText(/cliente estrategico/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText(/mapa de vendas/i)).toHaveTextContent("125000");
    });
  });

  it("renderiza a analise de compras com ranking de fornecedores e evolucao mensal", async () => {
    renderWithProviders(<AnaliseCompras />);

    expect(await screen.findByRole("heading", { level: 1, name: /^compras$/i })).toBeInTheDocument();
    expect(screen.getByText(/top fornecedores/i)).toBeInTheDocument();
    expect(await screen.findByText(/evolução das compras/i)).toBeInTheDocument();
  });

  it("agrega clientes por periodo e mostra busca/ranking da pagina", async () => {
    renderWithProviders(<Clientes />);

    expect(await screen.findByRole("heading", { level: 1, name: /^clientes$/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/buscar clientes/i)).toBeInTheDocument();
    expect(screen.getByText(/ranking de clientes/i)).toBeInTheDocument();
  });

  it("renderiza analise fiscal por CFOP com drill-down inicial por estado", async () => {
    renderWithProviders(<AnaliseFiscalCfop />);

    expect(await screen.findByRole("heading", { level: 1, name: /^analise fiscal$/i })).toBeInTheDocument();
    expect(screen.getByText(/estado > cidade > ncm > produto/i)).toBeInTheDocument();
    expect(await screen.findByText(/exibindo 2 estados/i)).toBeInTheDocument();
  });

  it("renderiza detalhamento de vendas com alternancia de modos e notas detalhadas", async () => {
    renderWithProviders(<DetalhamentoVendas />);

    expect(await screen.findByRole("heading", { level: 1, name: /^detalhamento de vendas$/i })).toBeInTheDocument();
    expect(screen.getByText(/faturamento mensal/i)).toBeInTheDocument();
    expect(screen.getByText(/impostos sobre vendas/i)).toBeInTheDocument();
  });

  it("renderiza detalhamento de compras com notas e hierarquia de produtos", async () => {
    renderWithProviders(<DetalhamentoCompras />);

    expect(await screen.findByRole("heading", { level: 1, name: /^detalhamento de compras$/i })).toBeInTheDocument();
    expect(await screen.findByText(/total comprado/i)).toBeInTheDocument();
  });

  it("renderiza importacao XML com pendencias e acoes principais", async () => {
    renderWithProviders(<ImportacaoXML />);

    expect(await screen.findByRole("heading", { name: /importação de xml/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /importar e processar/i })).toBeDisabled();
  });

  it("renderiza importacao SPED com pendencias e acoes principais", async () => {
    renderWithProviders(<ImportacaoSPED />);

    expect(await screen.findByRole("heading", { name: /importações sped fiscal/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /importar para banco/i })).toBeDisabled();
  });

  it("renderiza central de inconsistencias em estado sem pendencias", async () => {
    renderWithProviders(<Inconsistencias />);

    expect(await screen.findByRole("heading", { name: /central de inconsistencias/i })).toBeInTheDocument();
    expect(screen.getByText(/operacao sem inconsistencias abertas/i)).toBeInTheDocument();
  });

  it("renderiza reforma tributaria com apuracao e memoria de calculo", async () => {
    renderWithProviders(<ReformaTributaria />);

    expect(await screen.findByRole("heading", { level: 1, name: /^reforma tributaria$/i })).toBeInTheDocument();
    expect(screen.getByText(/apuracao por tributo/i)).toBeInTheDocument();
    expect(screen.getAllByText(/memoria de calculo/i).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("CBS")).length).toBeGreaterThan(0);
  });

  it("renderiza parametros de relatorios com IA usando anos retornados da API", async () => {
    renderWithProviders(<RelatoriosIA />);

    expect(await screen.findByRole("heading", { name: /relatórios com ia/i })).toBeInTheDocument();
    expect(screen.getByText(/parâmetros do relatório/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^gerar$/i })).toBeInTheDocument();
  });

  it("renderiza cadastro interno com todos os campos obrigatorios", async () => {
    renderWithProviders(<CadastroEmpresa />, { route: "/interno/cadastro-empresa" });

    expect(screen.getByRole("heading", { name: /cadastro interno/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/nome da empresa/i)).toBeRequired();
    expect(screen.getByLabelText(/cnpj/i)).toBeRequired();
    expect(screen.getByLabelText(/email do login/i)).toBeRequired();
    expect(screen.getByLabelText(/senha/i)).toBeRequired();
  });

  it("mantem a suite estavel esperando queries assíncronas terminarem", async () => {
    renderWithProviders(<AnaliseVendas />);

    await waitFor(() => {
      expect(screen.queryByText(/carregando dados/i)).not.toBeInTheDocument();
    });
    expect(await screen.findByText(/cliente estrategico/i)).toBeInTheDocument();
  });
});
