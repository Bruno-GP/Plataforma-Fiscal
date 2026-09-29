"""Testes com mocks (respx) — nunca chamam a API real da Conta Azul."""

from __future__ import annotations

import time
from datetime import date

import httpx
import pytest
import respx

from contaazul.auth import AuthError, ContaAzulAuth, ReauthorizationRequired, TokenSet, TOKEN_URL
from contaazul.client import ApiError, BASE_URL, ContaAzulClient, ENDPOINTS


class StubAuth:
    """Substitui ContaAzulAuth nos testes do client: sempre devolve um token fixo."""

    def get_valid_access_token(self) -> str:
        return "fake-access-token"


# ---------- ContaAzulClient ----------


@respx.mock
def test_listar_pessoas_normaliza_itens():
    respx.get(f"{BASE_URL}{ENDPOINTS['pessoas']}").mock(
        return_value=httpx.Response(
            200,
            json={"items": [{"id": "1", "nome": "Cliente Um", "documento": "123"}]},
        )
    )
    client = ContaAzulClient(auth=StubAuth())

    pessoas = client.listar_pessoas(pagina=1)

    assert len(pessoas) == 1
    assert pessoas[0].id == "1"
    assert pessoas[0].nome == "Cliente Um"
    assert pessoas[0].raw["documento"] == "123"


@respx.mock
def test_listar_vendas_normaliza_campos():
    payload = {
        "itens": [
            {
                "id": "v1",
                "numero": 100,
                "total": 50.0,
                "situacao": {"nome": "APROVADO", "descricao": "Aprovado"},
                "cliente": {"id": "c1", "nome": "Cliente Um"},
            }
        ]
    }
    respx.get(f"{BASE_URL}{ENDPOINTS['vendas']}").mock(return_value=httpx.Response(200, json=payload))
    client = ContaAzulClient(auth=StubAuth())

    vendas = client.listar_vendas(date(2026, 1, 1), date(2026, 1, 31), pagina=1)

    assert len(vendas) == 1
    assert vendas[0].numero == 100
    assert vendas[0].total == 50.0
    assert vendas[0].cliente["nome"] == "Cliente Um"


@respx.mock
def test_obter_venda_por_id():
    payload = {
        "cliente": {"uuid": "c1", "nome": "Cliente Um", "documento": "123"},
        "venda": {"id": "v1", "numero": 100},
        "vendedor": {"id": "vend1", "nome": "Vendedor Um"},
    }
    respx.get(f"{BASE_URL}/v1/venda/v1").mock(return_value=httpx.Response(200, json=payload))
    client = ContaAzulClient(auth=StubAuth())

    venda = client.obter_venda_por_id("v1")

    assert venda.cliente["nome"] == "Cliente Um"
    assert venda.vendedor["nome"] == "Vendedor Um"
    assert venda.raw["venda"]["numero"] == 100


@respx.mock
def test_retry_em_429_ate_sucesso():
    route = respx.get(f"{BASE_URL}{ENDPOINTS['categorias']}")
    route.side_effect = [
        httpx.Response(429, json={"erro": "rate limit"}),
        httpx.Response(200, json={"itens": [{"id": "c1", "nome": "Vendas"}]}),
    ]
    client = ContaAzulClient(auth=StubAuth())

    categorias = client.listar_categorias(pagina=1)

    assert route.call_count == 2
    assert categorias[0].nome == "Vendas"


@respx.mock
def test_endpoint_nao_encontrado_levanta_api_error():
    respx.get(f"{BASE_URL}{ENDPOINTS['centros_custo']}").mock(
        return_value=httpx.Response(404, json={"erro": "not found"})
    )
    client = ContaAzulClient(auth=StubAuth())

    with pytest.raises(ApiError) as exc_info:
        client.listar_centro_de_custo(pagina=1)
    assert exc_info.value.status_code == 404


@respx.mock
def test_token_rejeitado_levanta_auth_error():
    respx.get(f"{BASE_URL}{ENDPOINTS['pessoas']}").mock(return_value=httpx.Response(401, json={}))
    client = ContaAzulClient(auth=StubAuth())

    with pytest.raises(AuthError):
        client.listar_pessoas(pagina=1)


@respx.mock
def test_listar_produtos_normaliza_campos():
    payload = {
        "itens": [
            {
                "id": "p1",
                "id_legado": 12345,
                "nome": "Produto Exemplo",
                "codigo_sku": "SKU123",
                "codigo_ean": "1234567890123",
                "tipo": "PRODUTO",
                "status": "ATIVO",
                "estoque": 50,
                "valor_venda": 99.99,
                "custo_medio": 50,
            }
        ],
        "itens_totais": 1,
    }
    respx.get(f"{BASE_URL}{ENDPOINTS['produtos']}").mock(return_value=httpx.Response(200, json=payload))
    client = ContaAzulClient(auth=StubAuth())

    produtos = client.listar_produtos(pagina=1, busca="Exemplo", status="ATIVO")

    assert len(produtos) == 1
    assert produtos[0].id == "p1"
    assert produtos[0].nome == "Produto Exemplo"
    assert produtos[0].valor_venda == 99.99
    assert produtos[0].raw["codigo_ean"] == "1234567890123"


@respx.mock
def test_listar_produtos_so_envia_filtros_informados():
    route = respx.get(f"{BASE_URL}{ENDPOINTS['produtos']}").mock(
        return_value=httpx.Response(200, json={"itens": []})
    )
    client = ContaAzulClient(auth=StubAuth())

    client.listar_produtos(pagina=2)

    sent_params = dict(route.calls[0].request.url.params)
    assert sent_params["pagina"] == "2"
    assert "busca" not in sent_params
    assert "status" not in sent_params


@respx.mock
def test_listar_vendedores_aceita_array_bruto():
    payload = [
        {"id": "vend1", "nome": "João da Silva", "id_legado": 123456},
        {"id": "vend2", "nome": "Maria Souza"},
    ]
    respx.get(f"{BASE_URL}{ENDPOINTS['vendedores']}").mock(return_value=httpx.Response(200, json=payload))
    client = ContaAzulClient(auth=StubAuth())

    vendedores = client.listar_vendedores()

    assert len(vendedores) == 2
    assert vendedores[0].nome == "João da Silva"
    assert vendedores[0].id_legado == 123456
    assert vendedores[1].id_legado is None


@respx.mock
def test_listar_vendedores_payload_em_formato_inesperado_levanta_api_error():
    respx.get(f"{BASE_URL}{ENDPOINTS['vendedores']}").mock(
        return_value=httpx.Response(200, json={"itens": [{"id": "vend1", "nome": "João"}]})
    )
    client = ContaAzulClient(auth=StubAuth())

    with pytest.raises(ApiError):
        client.listar_vendedores()


@respx.mock
def test_obter_itens_venda_payload_em_formato_inesperado_levanta_api_error():
    respx.get(f"{BASE_URL}/v1/venda/venda-123/itens").mock(
        return_value=httpx.Response(200, json=[{"id": "i1", "nome": "Produto 1"}])
    )
    client = ContaAzulClient(auth=StubAuth())

    with pytest.raises(ApiError):
        client.obter_itens_venda("venda-123")


@respx.mock
def test_obter_itens_venda_retorna_itens_e_totais():
    payload = {
        "itens": [
            {"id": "i1", "id_item": "prod1", "nome": "Produto 1", "tipo": "PRODUTO", "quantidade": 2, "valor": 100.0, "custo": 60.0},
        ],
        "itens_totais": 1,
        "totais": {"quantidade_produtos": 1, "quantidade_servicos": 0, "quantidade_nao_conciliados": 0},
    }
    respx.get(f"{BASE_URL}/v1/venda/venda-123/itens").mock(return_value=httpx.Response(200, json=payload))
    client = ContaAzulClient(auth=StubAuth())

    itens, totais = client.obter_itens_venda("venda-123")

    assert len(itens) == 1
    assert itens[0].nome == "Produto 1"
    assert itens[0].quantidade == 2
    assert totais.quantidade_produtos == 1
    assert totais.quantidade_nao_conciliados == 0


# ---------- ContaAzulAuth ----------


def _make_auth(tmp_path):
    from contaazul.auth import TokenStore

    return ContaAzulAuth(
        client_id="id123",
        client_secret="secret123",
        redirect_uri="http://localhost:8765/callback",
        token_store=TokenStore(tmp_path / ".tokens.json"),
    )


@respx.mock
def test_exchange_code_for_token_salva_tokens(tmp_path):
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "at", "refresh_token": "rt", "expires_in": 3600, "token_type": "Bearer"},
        )
    )
    auth = _make_auth(tmp_path)

    tokens = auth.exchange_code_for_token("codigo-recebido")

    assert tokens.access_token == "at"
    assert auth.token_store.load().refresh_token == "rt"


@respx.mock
def test_refresh_token_expirado_levanta_reauthorization_required(tmp_path):
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    auth = _make_auth(tmp_path)

    with pytest.raises(ReauthorizationRequired):
        auth.refresh_access_token("refresh-expirado")


def test_token_set_is_expired():
    expirado = TokenSet(access_token="a", refresh_token="r", expires_in=3600, obtained_at=time.time() - 4000)
    valido = TokenSet(access_token="a", refresh_token="r", expires_in=3600, obtained_at=time.time())

    assert expirado.is_expired is True
    assert valido.is_expired is False


@respx.mock
def test_get_valid_access_token_renova_quando_expirado(tmp_path):
    auth = _make_auth(tmp_path)
    auth.token_store.save(
        TokenSet(access_token="antigo", refresh_token="rt", expires_in=3600, obtained_at=time.time() - 4000)
    )
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "novo", "refresh_token": "rt2", "expires_in": 3600, "token_type": "Bearer"},
        )
    )

    token = auth.get_valid_access_token()

    assert token == "novo"


def test_get_valid_access_token_sem_tokens_salvos_pede_reautenticacao(tmp_path):
    auth = _make_auth(tmp_path)

    with pytest.raises(ReauthorizationRequired):
        auth.get_valid_access_token()
