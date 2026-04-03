from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres


class MunicipiosCatalogService:
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
