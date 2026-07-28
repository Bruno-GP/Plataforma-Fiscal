"""CLI da integracao Conta Azul -> Plataforma Fiscal.

Comandos:
  python main.py auth
  python main.py sync --inicio 2026-01-01 --fim 2026-01-31
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Callable, TypeVar

import typer
from dotenv import load_dotenv

from contaazul.auth import ContaAzulAuth, AuthError
from contaazul.client import DEFAULT_PAGE_SIZE, ApiError, ContaAzulClient
from exporters.json_exporter import JsonExporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("contaazul.main")

app = typer.Typer(add_completion=False)

T = TypeVar("T")


def _load_auth() -> ContaAzulAuth:
    load_dotenv()
    client_id = os.environ.get("CONTAAZUL_CLIENT_ID")
    client_secret = os.environ.get("CONTAAZUL_CLIENT_SECRET")
    redirect_uri = os.environ.get("CONTAAZUL_REDIRECT_URI")
    if not all([client_id, client_secret, redirect_uri]):
        typer.secho(
            "Faltam variaveis no .env: CONTAAZUL_CLIENT_ID, CONTAAZUL_CLIENT_SECRET, CONTAAZUL_REDIRECT_URI",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)
    return ContaAzulAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)


def _coletar_todas_paginas(fetch_page: Callable[[int], list[T]]) -> list[T]:
    """Chama fetch_page(pagina) incrementando ate a pagina vir incompleta."""
    todos: list[T] = []
    pagina = 1
    while True:
        pagina_atual = fetch_page(pagina)
        todos.extend(pagina_atual)
        if len(pagina_atual) < DEFAULT_PAGE_SIZE:
            break
        pagina += 1
    return todos


def _detalhar_vendas(client: ContaAzulClient, vendas: list) -> list:
    """Busca o detalhe (GET /v1/venda/{id}) de cada venda. Se uma falhar, loga
    aviso e mantem a venda no formato resumido do /busca em vez de abortar tudo."""
    detalhadas = []
    for v in vendas:
        try:
            detalhadas.append(client.obter_venda_por_id(v.id))
        except ApiError as exc:
            logger.warning("Falha ao detalhar venda id=%s (status %s), mantendo dado resumido do /busca: %s", v.id, exc.status_code, exc.payload)
            detalhadas.append(v)
    return detalhadas


def _listar_vendedores_tolerante(client: ContaAzulClient) -> list:
    """Vendedores e um extra no sync; se falhar, loga aviso e segue sem eles
    em vez de abortar o resto da sincronizacao."""
    try:
        return client.listar_vendedores()
    except ApiError as exc:
        logger.warning("Falha ao listar vendedores (status %s), seguindo sem eles: %s", exc.status_code, exc.payload)
        return []


@app.command()
def auth(
    manual: bool = typer.Option(
        True,
        "--manual/--local",
        help="--manual: cola o code manualmente (redirect_uri fixo do sandbox). --local: sobe servidor local no redirect_uri.",
    ),
):
    """Inicia o fluxo OAuth2 (Authorization Code) e salva os tokens em .tokens.json."""
    auth_client = _load_auth()
    try:
        if manual:
            auth_client.run_manual_authorization_flow()
        else:
            auth_client.run_local_authorization_flow()
    except AuthError as exc:
        typer.secho(f"Falha na autenticacao: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.secho("Autenticado com sucesso. Tokens salvos em .tokens.json", fg=typer.colors.GREEN)


@app.command()
def sync(
    inicio: str = typer.Option(..., "--inicio", help="Data inicial (YYYY-MM-DD)"),
    fim: str = typer.Option(..., "--fim", help="Data final (YYYY-MM-DD)"),
    saida: Path = typer.Option(Path("output"), "--saida", help="Diretorio de saida"),
    detalhar_vendas: bool = typer.Option(
        True,
        "--detalhar-vendas/--sem-detalhar-vendas",
        help="Para cada venda listada, busca o detalhe completo (GET /v1/venda/{id}: cliente, vendedor, contrato). +1 chamada por venda.",
    ),
):
    """Puxa vendas, pessoas, categorias, centros de custo e contas a receber/pagar do periodo e exporta em JSON."""
    inicio = date.fromisoformat(inicio)
    fim = date.fromisoformat(fim)
    auth_client = _load_auth()
    client = ContaAzulClient(auth_client)

    try:
        vendas = _coletar_todas_paginas(lambda p: client.listar_vendas(inicio, fim, p))
        if detalhar_vendas:
            vendas = _detalhar_vendas(client, vendas)

        dados = {
            "vendas": vendas,
            "pessoas": _coletar_todas_paginas(lambda p: client.listar_pessoas(p)),
            "categorias": _coletar_todas_paginas(lambda p: client.listar_categorias(p)),
            "centros_custo": _coletar_todas_paginas(lambda p: client.listar_centro_de_custo(p)),
            "vendedores": _listar_vendedores_tolerante(client),
            "contas_receber": _coletar_todas_paginas(lambda p: client.listar_contas_a_receber(inicio, fim, p)),
            "contas_pagar": _coletar_todas_paginas(lambda p: client.listar_contas_a_pagar(inicio, fim, p)),
        }
    except AuthError as exc:
        typer.secho(f"Erro de autenticacao: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except ApiError as exc:
        typer.secho(f"Erro da API Conta Azul (status {exc.status_code}): {exc.payload}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        client.close()

    JsonExporter().export(dados, saida)

    resumo = ", ".join(f"{nome}={len(itens)}" for nome, itens in dados.items())
    typer.secho(f"Exportado para {saida}/ ({resumo})", fg=typer.colors.GREEN)


@app.command()
def produtos(
    busca: str = typer.Option(None, "--busca", help="Filtra por nome ou código do produto."),
    status: str = typer.Option(None, "--status", help="ATIVO, INATIVO ou TODOS."),
    saida: Path = typer.Option(Path("output"), "--saida", help="Diretorio de saida"),
):
    """Lista produtos (GET /v1/produto/busca). Sem dado fiscal (NCM/CEST) -- a API nao expoe."""
    auth_client = _load_auth()
    client = ContaAzulClient(auth_client)

    try:
        items = _coletar_todas_paginas(lambda p: client.listar_produtos(pagina=p, busca=busca, status=status))
    except AuthError as exc:
        typer.secho(f"Erro de autenticacao: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except ApiError as exc:
        typer.secho(f"Erro da API Conta Azul (status {exc.status_code}): {exc.payload}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        client.close()

    JsonExporter().export({"produtos": items}, saida)
    typer.secho(f"Exportado {len(items)} produtos para {saida}/produtos.json", fg=typer.colors.GREEN)


@app.command(name="itens-venda")
def itens_venda(
    id_venda: str = typer.Option(..., "--id-venda", help="UUID ou id legado da venda."),
    saida: Path = typer.Option(Path("output"), "--saida", help="Diretorio de saida"),
):
    """Lista itens de uma venda + totais agregados (GET /v1/venda/{id_venda}/itens)."""
    auth_client = _load_auth()
    client = ContaAzulClient(auth_client)

    try:
        pagina = 1
        todos_itens = []
        totais = None
        while True:
            itens, totais = client.obter_itens_venda(id_venda, pagina=pagina)
            todos_itens.extend(itens)
            if len(itens) < DEFAULT_PAGE_SIZE:
                break
            pagina += 1
    except AuthError as exc:
        typer.secho(f"Erro de autenticacao: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except ApiError as exc:
        typer.secho(f"Erro da API Conta Azul (status {exc.status_code}): {exc.payload}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        client.close()

    saida.mkdir(parents=True, exist_ok=True)
    payload = {
        "itens": [item.model_dump(mode="json") for item in todos_itens],
        "totais": totais.model_dump(mode="json") if totais else None,
    }
    caminho = saida / f"itens_venda_{id_venda}.json"
    caminho.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    typer.secho(f"Exportado {len(todos_itens)} itens para {caminho}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
