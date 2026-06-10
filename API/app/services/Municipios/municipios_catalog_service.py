from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres


class MunicipiosCatalogService:
  _UF_ORDEM = (
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
  )

  @staticmethod
  def normalizar_chave(valor: str) -> str:
    texto = " ".join((valor or "").strip().upper().split())
    if not texto:
      return ""
    sem_acentos = unicodedata.normalize("NFD", texto)
    return "".join(ch for ch in sem_acentos if unicodedata.category(ch) != "Mn")

  @staticmethod
  @lru_cache(maxsize=1)
  def carregar_mapas() -> tuple[dict[str, tuple[str, str]], dict[str, str], dict[str, str]]:
    mapas = MunicipiosCatalogService._load_from_db()
    if mapas[0]:
      return mapas
    return MunicipiosCatalogService._load_from_local_geojson()

  @staticmethod
  def normalizar_uf(valor: str | None) -> str:
    texto = "".join((valor or "").strip().upper().split())
    return texto if len(texto) == 2 and texto.isalpha() else ""

  @staticmethod
  def normalizar_codigo_ibge(valor: str | None) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())

  @staticmethod
  def listar_ufs(busca: str | None = None) -> list[dict[str, object]]:
    municipios_por_codigo, _, _ = MunicipiosCatalogService.carregar_mapas()
    termo = MunicipiosCatalogService.normalizar_chave(busca or "")
    contagem_por_uf: dict[str, int] = {}

    for _, uf in municipios_por_codigo.values():
      uf_normalizada = MunicipiosCatalogService.normalizar_uf(uf)
      if not uf_normalizada:
        continue
      contagem_por_uf[uf_normalizada] = contagem_por_uf.get(uf_normalizada, 0) + 1

    ufs = [
      {
        "uf": uf,
        "label": uf,
        "quantidade_municipios": contagem_por_uf.get(uf, 0),
      }
      for uf in MunicipiosCatalogService._UF_ORDEM
      if uf in contagem_por_uf
    ]

    if termo:
      ufs = [
        item
        for item in ufs
        if termo in MunicipiosCatalogService.normalizar_chave(str(item["uf"]))
      ]

    return ufs

  @staticmethod
  def listar_municipios_por_uf(
    uf: str | None,
    busca: str | None = None,
    limite: int | None = None,
  ) -> list[dict[str, str]]:
    uf_normalizada = MunicipiosCatalogService.normalizar_uf(uf)
    if not uf_normalizada:
      return []

    municipios_por_codigo, _, _ = MunicipiosCatalogService.carregar_mapas()
    termo = MunicipiosCatalogService.normalizar_chave(busca or "")

    municipios = [
      {
        "municipio_id": codigo_ibge,
        "codigo_ibge": codigo_ibge,
        "nome": nome,
        "uf": uf_registro,
      }
      for codigo_ibge, (nome, uf_registro) in municipios_por_codigo.items()
      if MunicipiosCatalogService.normalizar_uf(uf_registro) == uf_normalizada
    ]

    if termo:
      municipios = [
        municipio
        for municipio in municipios
        if termo in MunicipiosCatalogService.normalizar_chave(municipio["nome"])
      ]

    municipios.sort(key=lambda item: item["nome"].casefold())

    if limite is not None and limite > 0:
      municipios = municipios[:limite]

    return municipios

  @staticmethod
  def obter_municipio_por_codigo(codigo_ibge: str | None) -> dict[str, str] | None:
    codigo_normalizado = MunicipiosCatalogService.normalizar_codigo_ibge(codigo_ibge)
    if not codigo_normalizado:
      return None

    municipios_por_codigo, _, _ = MunicipiosCatalogService.carregar_mapas()
    municipio = municipios_por_codigo.get(codigo_normalizado)
    if not municipio:
      return None

    nome, uf = municipio
    return {
      "municipio_id": codigo_normalizado,
      "codigo_ibge": codigo_normalizado,
      "nome": nome,
      "uf": uf,
    }

  @staticmethod
  def obter_municipio_por_uf_e_nome(uf: str | None, nome: str | None) -> dict[str, str] | None:
    uf_normalizada = MunicipiosCatalogService.normalizar_uf(uf)
    nome_normalizado = MunicipiosCatalogService.normalizar_chave(nome or "")
    if not uf_normalizada or not nome_normalizado:
      return None

    municipios_por_codigo, _, _ = MunicipiosCatalogService.carregar_mapas()
    for codigo_ibge, (nome_registro, uf_registro) in municipios_por_codigo.items():
      if MunicipiosCatalogService.normalizar_uf(uf_registro) != uf_normalizada:
        continue
      if MunicipiosCatalogService.normalizar_chave(nome_registro) != nome_normalizado:
        continue
      return {
        "municipio_id": codigo_ibge,
        "codigo_ibge": codigo_ibge,
        "nome": nome_registro,
        "uf": uf_registro,
      }

    return None

  @staticmethod
  def resolver_municipio(
    uf: str | None = None,
    nome: str | None = None,
    municipio_id: str | None = None,
    codigo_ibge: str | None = None,
  ) -> dict[str, str] | None:
    candidato_codigo = MunicipiosCatalogService.normalizar_codigo_ibge(municipio_id or codigo_ibge)
    if candidato_codigo:
      return MunicipiosCatalogService.obter_municipio_por_codigo(candidato_codigo)

    if MunicipiosCatalogService.normalizar_uf(uf) and nome:
      return MunicipiosCatalogService.obter_municipio_por_uf_e_nome(uf, nome)

    return None

  @staticmethod
  def _load_from_db() -> tuple[dict[str, tuple[str, str]], dict[str, str], dict[str, str]]:
    config = carregar_config_postgres()
    conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      "connect_timeout": 5,
      **({"sslmode": config["sslmode"]} if config.get("sslmode") else {}),
    }

    try:
      with psycopg.connect(**conn_params) as conn:
        with conn.cursor() as cur:
          cur.execute(
            """
            SELECT codigo_ibge, nome, COALESCE(uf, '')
            FROM municipios_catalogo
            WHERE codigo_ibge IS NOT NULL
              AND nome IS NOT NULL
            ORDER BY codigo_ibge;
            """
          )
          rows = cur.fetchall()
    except psycopg.Error:
      return {}, {}, {}

    municipios_por_codigo: dict[str, tuple[str, str]] = {}
    municipios_por_nome: dict[str, str] = {}
    uf_por_nome: dict[str, str] = {}

    for codigo_ibge, nome, uf in rows:
      codigo = "".join(ch for ch in str(codigo_ibge or "") if ch.isdigit())
      nome_limpo = str(nome or "").strip()
      uf_limpa = str(uf or "").strip().upper()
      nome_normalizado = MunicipiosCatalogService.normalizar_chave(nome_limpo)

      if codigo and nome_limpo:
        municipios_por_codigo[codigo] = (nome_limpo, uf_limpa)
        municipios_por_nome[nome_normalizado] = nome_limpo
        if uf_limpa and nome_normalizado not in uf_por_nome:
          uf_por_nome[nome_normalizado] = uf_limpa

    return municipios_por_codigo, municipios_por_nome, uf_por_nome

  @staticmethod
  def _load_from_local_geojson() -> tuple[dict[str, tuple[str, str]], dict[str, str], dict[str, str]]:
    caminho_municipios = Path(__file__).resolve().parent / "LL-municipios.json"
    try:
      with caminho_municipios.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
      return {}, {}, {}

    municipios_por_codigo: dict[str, tuple[str, str]] = {}
    municipios_por_nome: dict[str, str] = {}
    uf_por_nome: dict[str, str] = {}

    features = dados.get("features", []) if isinstance(dados, dict) else []
    for item in features if isinstance(features, list) else []:
      propriedades = item.get("properties", {}) if isinstance(item, dict) else {}
      codigo = "".join(ch for ch in str(propriedades.get("id", "")) if ch.isdigit())
      nome = str(propriedades.get("name", "")).strip()
      nome_normalizado = MunicipiosCatalogService.normalizar_chave(nome)
      uf = MunicipiosCatalogService._uf_por_prefixo_ibge(codigo)

      if codigo and nome:
        municipios_por_codigo[codigo] = (nome, uf)
        municipios_por_nome[nome_normalizado] = nome
        if uf and nome_normalizado not in uf_por_nome:
          uf_por_nome[nome_normalizado] = uf

    return municipios_por_codigo, municipios_por_nome, uf_por_nome

  @staticmethod
  def _uf_por_prefixo_ibge(codigo: str) -> str:
    mapa = {
      "11": "RO",
      "12": "AC",
      "13": "AM",
      "14": "RR",
      "15": "PA",
      "16": "AP",
      "17": "TO",
      "21": "MA",
      "22": "PI",
      "23": "CE",
      "24": "RN",
      "25": "PB",
      "26": "PE",
      "27": "AL",
      "28": "SE",
      "29": "BA",
      "31": "MG",
      "32": "ES",
      "33": "RJ",
      "35": "SP",
      "41": "PR",
      "42": "SC",
      "43": "RS",
      "50": "MS",
      "51": "MT",
      "52": "GO",
      "53": "DF",
    }
    return mapa.get(codigo[:2], "") if len(codigo) >= 2 else ""
