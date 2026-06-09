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
  http.post(`${API_BASE_URL}/auth/entrar`, () => HttpResponse.json(sessionResponse)),
  http.post(`${API_BASE_URL}/auth/registrar`, () => HttpResponse.json(sessionResponse, { status: 201 })),
  http.post(`${API_BASE_URL}/auth/sair`, () => HttpResponse.json({ ok: true })),
  http.get(`${API_BASE_URL}/nfe/xml/pendencias`, () =>
    HttpResponse.json({
      total_pendentes: 0,
      itens: [],
    }),
  ),
];
