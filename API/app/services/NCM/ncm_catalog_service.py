from __future__ import annotations

import html
import json
import re
from functools import lru_cache
from pathlib import Path

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres


class NCMCatalogService:
  def __init__(self) -> None:
    self._catalog = self._load_catalog()

  @staticmethod
  @lru_cache(maxsize=1)
  def _load_catalog() -> dict[str, str]:
    catalog = NCMCatalogService._load_catalog_from_db()
    if catalog:
      return catalog
    return NCMCatalogService._load_catalog_from_json()

  @staticmethod
  def _load_catalog_from_db() -> dict[str, str]:
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
            SELECT codigo, descricao
            FROM ncm_catalogo
            WHERE codigo IS NOT NULL
              AND descricao IS NOT NULL
            ORDER BY codigo;
            """
          )
          rows = cur.fetchall()
    except psycopg.Error:
      return {}

    catalog: dict[str, str] = {}
    for codigo, descricao in rows:
      codigo_normalizado = NCMCatalogService.normalizar_codigo(codigo)
      descricao_normalizada = NCMCatalogService.normalizar_descricao(descricao)
      if len(codigo_normalizado) == 8 and descricao_normalizada:
        catalog[codigo_normalizado] = descricao_normalizada

    return catalog

  @staticmethod
  def _load_catalog_from_json() -> dict[str, str]:
    base_path = Path(__file__).resolve().parent
    json_files = sorted(base_path.glob("Tabela_NCM_Vigente_*.json"), reverse=True)
    if not json_files:
      return {}

    try:
      payload = json.loads(json_files[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
      return {}

    catalog: dict[str, str] = {}
    for entry in payload.get("Nomenclaturas", []):
      codigo = NCMCatalogService.normalizar_codigo(entry.get("Codigo"))
      descricao = NCMCatalogService.normalizar_descricao(entry.get("Descricao"))
      if len(codigo) == 8 and descricao:
        catalog[codigo] = descricao

    return catalog

  @staticmethod
  def normalizar_codigo(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())

  @staticmethod
  def normalizar_descricao(value: str | None) -> str:
    texto = html.unescape(str(value or ""))
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"^[\-\s]+", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto.rstrip(".:;")

  def obter_descricao(self, codigo_ncm: str | None) -> str | None:
    codigo_normalizado = self.normalizar_codigo(codigo_ncm)
    if not codigo_normalizado:
      return None

    codigo_normalizado = codigo_normalizado[:8]
    descricao = self._catalog.get(codigo_normalizado)
    if descricao:
      return descricao

    for tamanho in range(min(len(codigo_normalizado), 7), 1, -1):
      prefixo = codigo_normalizado[:tamanho]
      for codigo_catalogo, descricao_catalogo in self._catalog.items():
        if codigo_catalogo.startswith(prefixo):
          return descricao_catalogo

    return None
