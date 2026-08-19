import { http, HttpResponse } from "msw";

import { API_BASE_URL } from "@/services/api";

const sessionResponse = {
  status: "ok",
  login_id: 1,
  empresa_id: 1,
  cnpj: "12345678000199",
  email: "teste@empresa.com",
  empresa_nome: "Empresa Teste",
  tem_sped: false,
  tem_xml_importado_valido: false,
  expires_in: 3600,
};

export const handlers = [
  http.get(`${API_BASE_URL}/auth/sessao`, () => HttpResponse.json(sessionResponse)),
  http.get(`${API_BASE_URL}/auth/perfil`, () =>
    HttpResponse.json({
      status: "ok",
      login_id: 1,
      empresa_id: 1,
      cnpj: "12345678000199",
      empresa_nome: "Empresa Teste",
      estado: "SP",
      cidade: "Sao Paulo",
    }),
  ),
  http.post(`${API_BASE_URL}/auth/entrar`, () => HttpResponse.json(sessionResponse)),
  http.post(`${API_BASE_URL}/auth/registrar`, () => HttpResponse.json(sessionResponse, { status: 201 })),
  http.patch(`${API_BASE_URL}/auth/senha`, () =>
    HttpResponse.json({
      status: "ok",
      message: "Senha atualizada com sucesso.",
    }),
  ),
  http.post(`${API_BASE_URL}/auth/sair`, () => HttpResponse.json({ ok: true })),
  http.get(`${API_BASE_URL}/sefaz/certificados/status`, () =>
    HttpResponse.json({
      ativo: true,
      cnpj_titular: "12345678000190",
      data_validade: "2026-12-31",
      dias_restantes: 136,
    }),
  ),
  http.post(`${API_BASE_URL}/sefaz/certificados`, () =>
    HttpResponse.json({
      ativo: true,
      cnpj_titular: "12345678000190",
      data_validade: "2026-12-31",
      dias_restantes: 136,
    }),
  ),
  http.post(`${API_BASE_URL}/sefaz/sync`, () =>
    HttpResponse.json({
      status: "accepted",
      message: "Sincronizacao SEFAZ enfileirada com sucesso.",
      empresa_id: 1,
    }, { status: 202 }),
  ),
  http.get(`${API_BASE_URL}/sefaz/sync-status`, () =>
    HttpResponse.json({
      disponivel: true,
      bloqueado_ate: null,
      segundos_restantes: 0,
      ultima_sincronizacao_com_notas_em: null,
      documentos_novos_ultima_sync: 0,
    }),
  ),
  http.get(`${API_BASE_URL}/sefaz/documentos`, () =>
    HttpResponse.json({
      total: 1,
      limit: 10,
      offset: 0,
      resultados: [
        {
          id: 10,
          chave_acesso: "35123456789012345678901234567890123456789012",
          tipo_documento: "nfeProc",
          direcao: "recebida",
          cnpj_emitente: "98765432000199",
          cnpj_destinatario: "12345678000190",
          nsu: "000000000000010",
          data_emissao: "2026-08-01",
          valor_total: "123.45",
          situacao: "autorizada",
          manifestacao_status: "pendente",
          criado_em: "2026-08-01T12:00:00Z",
          atualizado_em: "2026-08-01T13:00:00Z",
        },
      ],
    }),
  ),
  http.get(`${API_BASE_URL}/sefaz/documentos/:documentoId`, () =>
    HttpResponse.json({
      id: 10,
      chave_acesso: "35123456789012345678901234567890123456789012",
      tipo_documento: "nfeProc",
      direcao: "recebida",
      cnpj_emitente: "98765432000199",
      cnpj_destinatario: "12345678000190",
      nsu: "000000000000010",
      data_emissao: "2026-08-01",
      valor_total: "123.45",
      situacao: "autorizada",
      manifestacao_status: "pendente",
      criado_em: "2026-08-01T12:00:00Z",
      atualizado_em: "2026-08-01T13:00:00Z",
      xml_armazenado_base64: "PHhtbD50ZXN0ZTwveG1sPg==",
    }),
  ),
  http.post(`${API_BASE_URL}/sefaz/documentos/:documentoId/manifestacao`, () =>
    HttpResponse.json({
      documento_id: 10,
      manifestacao_status: "confirmada",
    }),
  ),
  http.get(`${API_BASE_URL}/sefaz/sync-log`, () =>
    HttpResponse.json({
      total: 1,
      limit: 10,
      offset: 0,
      resultados: [
        {
          id: 1,
          empresa_id: 1,
          iniciado_em: "2026-08-17T02:00:00Z",
          finalizado_em: "2026-08-17T02:05:00Z",
          documentos_novos: 3,
          nsu_inicial: "000000000000000",
          nsu_final: "000000000000123",
          status: "sucesso",
          erro_detalhe: null,
        },
      ],
    }),
  ),
  http.get(`${API_BASE_URL}/nfe/xml/pendencias`, () =>
    HttpResponse.json({
      total_pendentes: 0,
      itens: [],
    }),
  ),
];
