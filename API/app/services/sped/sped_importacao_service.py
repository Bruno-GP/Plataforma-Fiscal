from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

from app.domain.sped.reader import resumir_registros_sped_bytes
from app.repositories.sped.sped_importacao_repository import SpedImportacaoRepository
from app.services.reforma_tributaria.reforma_tributaria_sync_service import ReformaTributariaSyncService


@dataclass
class SpedImportacaoResultado:
  arquivo: str
  cnpj_emitente: str | None
  status: str
  mensagem: str


class SpedImportacaoService:
  """Gerencia staging, carga analítica e pós-processamento de arquivos SPED importados."""

  def __init__(self):
    self.repository = SpedImportacaoRepository()
    self.config = self.repository.config
    self._cache_municipios: dict[str, str | None] = {}
    self._municipios_por_codigo = self._carregar_municipios_locais()

  def _obter_repository(self) -> SpedImportacaoRepository:
    repository = getattr(self, "repository", None)
    if repository is None:
      repository = SpedImportacaoRepository()
      self.repository = repository
    return repository

  def importar_arquivos(
    self,
    arquivos: Iterable[tuple[str, bytes]],
    cnpj_empresa_origem: str,
  ) -> list[SpedImportacaoResultado]:
    """Valida o registro 0000, evita duplicidade por hash e guarda o TXT no staging."""

    resultados: list[SpedImportacaoResultado] = []
    cnpj_normalizado = self._normalizar_cnpj(cnpj_empresa_origem)

    if not cnpj_normalizado:
      raise ValueError("CNPJ de origem inválido.")

    repository = self._obter_repository()
    with repository.transacao() as conn:
      repository.validar_tabela_staging(conn)

      for nome_arquivo, conteudo in arquivos:
        cnpj_arquivo = self._extrair_cnpj_sped(conteudo)
        if not cnpj_arquivo:
          resultados.append(
            SpedImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=None,
              status="erro",
              mensagem="Arquivo SPED rejeitado: registro 0000 sem CNPJ valido.",
            )
          )
          continue

        if cnpj_arquivo != cnpj_normalizado:
          resultados.append(
            SpedImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=cnpj_arquivo,
              status="erro",
              mensagem="Arquivo SPED rejeitado: o CNPJ do registro 0000 difere do CNPJ da empresa autenticada.",
            )
          )
          continue

        hash_arquivo = sha256(conteudo).hexdigest()

        if repository.importacao_existe(conn, cnpj_normalizado, hash_arquivo):
          resultados.append(
            SpedImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=cnpj_normalizado,
              status="duplicado",
              mensagem="Esse arquivo SPED já foi importado para este CNPJ.",
            )
          )
          continue

        repository.inserir_importacao(
          conn,
          cnpj_normalizado,
          nome_arquivo,
          hash_arquivo,
          len(conteudo),
          conteudo,
        )

        resultados.append(
          SpedImportacaoResultado(
            arquivo=nome_arquivo,
            cnpj_emitente=cnpj_normalizado,
            status="importado",
            mensagem="Arquivo SPED importado com sucesso.",
          )
        )

    return resultados

  def contar_pendentes(self, cnpj_emitente: str) -> int:
    cnpj_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_normalizado:
      return 0

    repository = self._obter_repository()
    with repository.transacao() as conn:
      repository.validar_tabela_staging(conn)
      return repository.contar_pendentes(cnpj_normalizado, conn)

  def processar_importados(self, cnpj_emitente: str) -> tuple[Counter, int, list[int]]:
    """Carrega arquivos pendentes nas tabelas analíticas e retorna IDs aptos a finalização."""

    cnpj_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_normalizado:
      raise ValueError("CNPJ emitente inválido.")

    contador_registros: Counter = Counter()
    total_linhas = 0
    ids_processados: list[int] = []

    repository = self._obter_repository()
    with repository.transacao() as conn:
      repository.validar_tabela_staging(conn)
      repository.validar_tabelas_analiticas(conn)
      rows = repository.listar_importacoes_pendentes(conn, cnpj_normalizado)

      for row in rows:
        sped_id = int(row[0])
        conteudo = bytes(row[1]) if row[1] else b""
        registros, linhas = resumir_registros_sped_bytes(conteudo)
        contador_registros.update(registros)
        total_linhas += linhas
        ids_processados.append(sped_id)
        self._carregar_sped_em_tabelas(conn, cnpj_normalizado, conteudo, sped_id)

      if ids_processados:
        repository.atualizar_kpis(conn, cnpj_normalizado, ids_processados)
        reforma_sync_service = ReformaTributariaSyncService()
        reforma_sync_service.sincronizar_sped_apuracao_icms(conn, cnpj_normalizado)
        reforma_sync_service.sincronizar_sped_documentos_itens_icms(conn, cnpj_normalizado)

      repository.atualizar_nomes_municipios_participantes(
        conn,
        cnpj_normalizado,
        self._obter_nome_municipio,
      )

    return contador_registros, total_linhas, ids_processados

  def marcar_como_processados(self, ids_sped: list[int]) -> None:
    """Marca SPEDs como processados após a carga analítica e sincronização fiscal concluírem."""

    if not ids_sped:
      return

    self._obter_repository().marcar_como_processados(ids_sped)

  def _carregar_sped_em_tabelas(
    self,
    conn: object,
    cnpj_emitente: str,
    conteudo: bytes,
    importacao_id: int,
  ) -> None:
    linhas = conteudo.decode("latin-1", errors="ignore").splitlines()

    repository = self._obter_repository()
    participantes: dict[str, tuple[str, str | None, str | None, str | None, str | None]] = {}
    produtos: dict[str, tuple[str, str | None, str | None, str | None]] = {}
    participante_ids: dict[str, int] = {}
    produto_ids: dict[str, int] = {}
    documento_id_atual: int | None = None
    periodo_ano: int | None = None
    periodo_mes: int | None = None

    repository.remover_dados_importacao(conn, importacao_id)
    repository.garantir_empresa(conn, cnpj_emitente)

    for linha in linhas:
      partes = linha.strip().split("|")
      if len(partes) < 2 or not partes[1]:
        continue

      registro = partes[1]

      if registro == "0150":
        codigo = (partes[2] if len(partes) > 2 else "").strip()
        if not codigo:
          continue
        nome = (partes[3] if len(partes) > 3 else "").strip() or "Participante não identificado"
        cnpj_cpf = self._normalizar_documento((partes[5] if len(partes) > 5 else "").strip())
        codigo_municipio = (partes[8] if len(partes) > 8 else "").strip()
        municipio = codigo_municipio or None
        municipio_nome = self._obter_nome_municipio(codigo_municipio) or "Cidade não identificada"
        uf = self._extrair_uf_de_cod_municipio(codigo_municipio)
        participantes[codigo] = (nome, cnpj_cpf, municipio, municipio_nome, uf)
        continue

      if registro == "0200":
        codigo_item = (partes[2] if len(partes) > 2 else "").strip()
        if not codigo_item:
          continue
        descricao = (partes[3] if len(partes) > 3 else "").strip() or "Produto não identificado"
        unidade = (partes[6] if len(partes) > 6 else "").strip() or None
        tipo_item = (partes[7] if len(partes) > 7 else "").strip() or None
        ncm = (partes[8] if len(partes) > 8 else "").strip() or None
        produtos[codigo_item] = (descricao, ncm, unidade, tipo_item)
        continue

      if registro == "C100":
        cod_part = (partes[4] if len(partes) > 4 else "").strip()
        participante_id = repository.upsert_participante(
          conn,
          participante_ids,
          participantes,
          cnpj_emitente,
          cod_part,
        )

        data_emissao = self._to_date(partes[10] if len(partes) > 10 else None)
        data_movimentacao = self._to_date(partes[11] if len(partes) > 11 else None)

        documento_id_atual = repository.salvar_documento(
          conn,
          cnpj_emitente,
          participante_id,
          self._to_int(partes[5] if len(partes) > 5 else None),
          (partes[7] if len(partes) > 7 else None) or None,
          self._to_int(partes[8] if len(partes) > 8 else None),
          (partes[9] if len(partes) > 9 else None) or None,
          "saida" if (partes[2] if len(partes) > 2 else "") == "1" else "entrada",
          data_emissao,
          data_movimentacao,
          self._to_decimal(partes[12] if len(partes) > 12 else None),
          self._to_decimal(partes[16] if len(partes) > 16 else None),
          self._to_decimal(partes[18] if len(partes) > 18 else None),
          self._to_decimal(partes[14] if len(partes) > 14 else None),
          importacao_id,
        )
        continue

      if registro == "E100":
        data_inicio = self._to_date(partes[2] if len(partes) > 2 else None)
        if data_inicio:
          periodo_ano = int(data_inicio.year)
          periodo_mes = int(data_inicio.month)
        continue

      if registro == "E110" and periodo_ano and periodo_mes:
        total_debitos = self._to_decimal(partes[2] if len(partes) > 2 else None)
        ajustes_debitos = self._to_decimal(partes[3] if len(partes) > 3 else None)
        total_creditos = self._to_decimal(partes[6] if len(partes) > 6 else None)
        ajustes_creditos = self._to_decimal(partes[7] if len(partes) > 7 else None)
        saldo_apurado = self._to_decimal(partes[11] if len(partes) > 11 else None)
        valor_icms_recolher = self._to_decimal(partes[13] if len(partes) > 13 else None)
        saldo_credor_transportar = self._to_decimal(partes[14] if len(partes) > 14 else None)
        debitos_especiais = self._to_decimal(partes[15] if len(partes) > 15 else None)

        repository.upsert_apuracao_icms(
          conn,
          cnpj_emitente,
          periodo_ano,
          periodo_mes,
          total_debitos,
          ajustes_debitos,
          total_creditos,
          ajustes_creditos,
          saldo_apurado,
          valor_icms_recolher,
          saldo_credor_transportar,
          debitos_especiais,
        )
        continue

      if registro == "C170" and documento_id_atual:
        codigo_item = (partes[3] if len(partes) > 3 else "").strip()
        produto_id = repository.upsert_produto(
          conn,
          produto_ids,
          produtos,
          cnpj_emitente,
          codigo_item,
        )
        quantidade = self._to_decimal(partes[5] if len(partes) > 5 else None)
        valor_total_item = self._to_decimal(partes[7] if len(partes) > 7 else None)

        repository.salvar_item(
          conn,
          documento_id_atual,
          produto_id,
          self._to_int(partes[2] if len(partes) > 2 else None),
          (partes[11] if len(partes) > 11 else None) or None,
          quantidade,
          self._calcular_valor_unitario(valor_total_item, quantidade),
          valor_total_item,
          self._to_decimal(partes[8] if len(partes) > 8 else None),
          (partes[10] if len(partes) > 10 else None) or None,
          self._to_decimal(partes[13] if len(partes) > 13 else None),
          self._to_decimal(partes[14] if len(partes) > 14 else None),
          self._to_decimal(partes[15] if len(partes) > 15 else None),
          self._to_decimal(partes[22] if len(partes) > 22 else None),
          self._to_decimal(partes[23] if len(partes) > 23 else None),
          self._to_decimal(partes[24] if len(partes) > 24 else None),
          self._to_decimal(partes[30] if len(partes) > 30 else None),
          self._to_decimal(partes[36] if len(partes) > 36 else None),
        )

  def _normalizar_cnpj(self, cnpj: str | None) -> str | None:
    if not cnpj:
      return None

    digits = "".join(ch for ch in cnpj if ch.isdigit())
    if len(digits) == 14:
      return digits

    return None

  def _extrair_cnpj_sped(self, conteudo: bytes) -> str | None:
    for linha in conteudo.decode("latin-1", errors="ignore").splitlines():
      partes = linha.strip().split("|")
      if len(partes) < 8 or partes[1] != "0000":
        continue

      return self._normalizar_cnpj(partes[7])

    return None

  def _normalizar_documento(self, value: str | None) -> str | None:
    if not value:
      return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits or None

  def _extrair_uf_de_cod_municipio(self, codigo_municipio: str | None) -> str | None:
    if not codigo_municipio:
      return None

    codigo_numerico = "".join(ch for ch in codigo_municipio if ch.isdigit())
    if len(codigo_numerico) < 2:
      return None

    uf_por_codigo: dict[str, str] = {
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

    return uf_por_codigo.get(codigo_numerico[:2])

  def _obter_nome_municipio(self, codigo_municipio: str | None) -> str | None:
    codigo_numerico = "".join(ch for ch in str(codigo_municipio or "") if ch.isdigit())
    if len(codigo_numerico) not in {6, 7}:
      return None

    self._carregar_base_municipios_ibge()

    if codigo_numerico in self._cache_municipios:
      return self._cache_municipios[codigo_numerico]

    nome_municipio = self._municipios_por_codigo.get(codigo_numerico)
    self._cache_municipios[codigo_numerico] = nome_municipio
    return nome_municipio

  def _carregar_base_municipios_ibge(self) -> None:
    if self._municipios_por_codigo:
      return

    self._municipios_por_codigo = self._carregar_municipios_locais()

  def _carregar_municipios_locais(self) -> dict[str, str]:
    caminho_municipios = Path(__file__).resolve().parent.parent / "Municipios" / "municipios.json"

    try:
      with caminho_municipios.open(encoding="utf-8") as arquivo:
        payload = json.load(arquivo)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
      return {}

    if not isinstance(payload, list):
      return {}

    municipios: dict[str, str] = {}
    for item in payload:
      if not isinstance(item, dict):
        continue

      codigo = "".join(ch for ch in str(item.get("id") or "") if ch.isdigit())
      nome = str(item.get("nome") or "").strip()
      if len(codigo) in {6, 7} and nome:
        municipios[codigo] = nome

    return municipios

  def _to_int(self, value: str | None) -> int | None:
    if not value:
      return None
    value = value.strip()
    if not value:
      return None
    try:
      return int(value)
    except ValueError:
      return None

  def _to_decimal(self, value: str | None) -> Decimal:
    if not value:
      return Decimal("0")

    normalizado = value.strip().replace(".", "").replace(",", ".")
    if not normalizado:
      return Decimal("0")

    try:
      return Decimal(normalizado)
    except InvalidOperation:
      return Decimal("0")

  def _calcular_valor_unitario(self, valor_total: Decimal, quantidade: Decimal) -> Decimal:
    if quantidade == 0:
      return Decimal("0")

    return valor_total / quantidade

  def _to_date(self, value: str | None):
    if not value:
      return None

    bruto = value.strip()
    if len(bruto) != 8:
      return None

    try:
      return datetime.strptime(bruto, "%d%m%Y").date()
    except ValueError:
      return None
