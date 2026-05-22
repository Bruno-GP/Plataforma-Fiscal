from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable
from xml.etree import ElementTree as ET

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres

@dataclass
class XMLImportacaoResultado:
  arquivo: str
  cnpj_emitente: str | None
  status: str
  mensagem: str


class XMLImportacaoService:
  """Gerencia o staging de XMLs antes do processamento assíncrono de KPIs."""

  def __init__(self):
    self.config = carregar_config_postgres()

  def importar_arquivos(
    self,
    arquivos: Iterable[tuple[str, bytes]],
    cnpj_empresa_origem: str,
  ) -> list[XMLImportacaoResultado]:
    """Valida CNPJ/autorização e persiste XMLs únicos por hash no staging."""

    resultados: list[XMLImportacaoResultado] = []
    
    cnpj_empresa_origem_normalizado = self._normalizar_cnpj(cnpj_empresa_origem)

    if not cnpj_empresa_origem_normalizado:
      raise ValueError("CNPJ de origem inválido.")

    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      self._validar_tabela_staging(conn)

      for nome_arquivo, conteudo in arquivos:
        cnpj_emitente = self._extrair_cnpj_emitente(conteudo)
        if not cnpj_emitente:
          resultados.append(
            XMLImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=None,
              status="erro",
              mensagem="XML não foi processado por não ser compativel",
            )
          )
          continue
        
        valido, motivo_rejeicao = self._validar_documento_autorizado(conteudo)
        if not valido:
          resultados.append(
            XMLImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=cnpj_emitente,
              status="erro",
              mensagem=motivo_rejeicao,
            )
          )
          continue
        
        if cnpj_emitente != cnpj_empresa_origem_normalizado:
          resultados.append(
            XMLImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=cnpj_emitente,
              status="erro",
              mensagem="XML rejeitado: o CNPJ emitente difere do CNPJ da empresa autenticada.",
            )
          )
          continue

        hash_arquivo = sha256(conteudo).hexdigest()

        with conn.cursor() as cur:
          cur.execute(
            """
            SELECT id
            FROM notas_xml_importados
            WHERE cnpj_emitente = %s
              AND hash_arquivo = %s
            LIMIT 1
            """,
            (cnpj_emitente, hash_arquivo),
          )
          existente = cur.fetchone()

          if existente:
            resultados.append(
              XMLImportacaoResultado(
                arquivo=nome_arquivo,
                cnpj_emitente=cnpj_emitente,
                status="duplicado",
                mensagem="Esse XML já foi importado para este CNPJ.",
              )
            )
            continue

          cur.execute(
            """
            INSERT INTO notas_xml_importados (
              cnpj_emitente,
              nome_arquivo,
              hash_arquivo,
              tamanho_bytes,
              conteudo_xml
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (cnpj_emitente, nome_arquivo, hash_arquivo, len(conteudo), conteudo),
          )

          resultados.append(
            XMLImportacaoResultado(
              arquivo=nome_arquivo,
              cnpj_emitente=cnpj_emitente,
              status="importado",
              mensagem="XML importado com sucesso.",
            )
          )

      conn.commit()

    return resultados

  def _validar_tabela_staging(self, conn: psycopg.Connection) -> None:
    required_columns = {
      "id",
      "cnpj_emitente",
      "nome_arquivo",
      "hash_arquivo",
      "tamanho_bytes",
      "conteudo_xml",
      "processado_em",
      "criado_em",
    }

    with conn.cursor() as cur:
      cur.execute("SELECT to_regclass('public.notas_xml_importados')")
      if cur.fetchone()[0] is None:
        raise RuntimeError(
          "Tabela public.notas_xml_importados nao encontrada. Execute as migrations Alembic antes de importar XML."
        )

      cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'notas_xml_importados'
        """
      )
      existing_columns = {row[0] for row in cur.fetchall()}

    missing_columns = sorted(required_columns - existing_columns)
    if missing_columns:
      raise RuntimeError(
        "Tabela public.notas_xml_importados incompleta. Execute as migrations Alembic. "
        f"Colunas ausentes: {', '.join(missing_columns)}."
      )

  def listar_xmls_importados_nao_processados(self, cnpj_emitente: str) -> list[tuple[int, str, bytes]]:
    """Retorna XMLs pendentes em ordem estável para o worker processar em lote."""

    cnpj_emitente_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_emitente_normalizado:
      return []
    
    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      self._validar_tabela_staging(conn)

      with conn.cursor() as cur:
        cur.execute(
          """
          SELECT id, nome_arquivo, conteudo_xml
          FROM notas_xml_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          ORDER BY id ASC
          """,
          (cnpj_emitente_normalizado,),
        )
        rows = cur.fetchall()

      return [(row[0], row[1], bytes(row[2]) if row[2] else b"") for row in rows]

  def marcar_como_processados(self, ids_xml: list[int]) -> None:
    """Marca XMLs como processados somente após o job concluir a consolidação com sucesso."""

    if not ids_xml:
      return

    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      with conn.cursor() as cur:
        cur.execute(
          """
          UPDATE notas_xml_importados
          SET processado_em = NOW()
          WHERE id = ANY(%s)
          """,
          (ids_xml,),
        )
      conn.commit()
      
  def contar_xmls_pendentes(self, cnpj_emitente: str) -> int:
    cnpj_emitente_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_emitente_normalizado:
      return 0
    
    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      self._validar_tabela_staging(conn)

      with conn.cursor() as cur:
        cur.execute(
          """
          SELECT COUNT(*)
          FROM notas_xml_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          """,
          (cnpj_emitente_normalizado,),
        )
        row = cur.fetchone()

      return int(row[0] or 0) if row else 0

  def _extrair_cnpj_emitente(self, conteudo: bytes) -> str | None:
    try:
      root = ET.fromstring(conteudo)
    except ET.ParseError:
      return None

    emitente = next(
      (
        element
        for element in root.iter()
        if element.tag.split("}")[-1].lower() == "emit"
      ),
      None,
    )
    
    if emitente is None:
      prestador = next(
        (
          element
          for element in root.iter()
          if element.tag.split("}")[-1].lower() == "identificacaoprestador"
        ),
        None,
      )
      if prestador is not None:
        emitente = prestador
    
    if emitente is None:
      return None

    cnpj_emitente = next(
      (
        element
        for element in emitente.iter()
        if element.tag.split("}")[-1].lower() == "cnpj"
      ),
      None,
    )
    if cnpj_emitente is None or not cnpj_emitente.text:
      return None

    return self._normalizar_cnpj(cnpj_emitente.text)

  def _normalizar_cnpj(self, cnpj: str | None) -> str | None:
    if not cnpj:
      return None

    digits = "".join(ch for ch in cnpj if ch.isdigit())
    if len(digits) == 14:
      return digits

    return None
  
  def _validar_documento_autorizado(self, conteudo: bytes) -> tuple[bool, str]:
    try:
      root = ET.fromstring(conteudo)
    except ET.ParseError:
      return False, "XML inválido: não foi possível interpretar o conteúdo."

    nome_tag_raiz = root.tag.split("}")[-1].lower()

    if nome_tag_raiz in {"inutnfe", "procinutnfe"}:
      return False, "XML rejeitado: NFC-e inutilizada não pode ser importada."
    
    tipo_documento = self._identificar_tipo_documento(root)

    if tipo_documento == "nfse":
      return self._validar_nfse_autorizada(root)

    return self._validar_nfe_nfce_autorizada(root)

  def _identificar_tipo_documento(self, root: ET.Element) -> str:
    if self._encontrar_texto_por_tag(root, "InfNfse") is not None:
      return "nfse"

    modelo = self._encontrar_texto_por_tag(root, "mod")
    if modelo == "65":
      return "nfce"
    return "nfe"

  def _validar_nfe_nfce_autorizada(self, root: ET.Element) -> tuple[bool, str]:

    tp_evento = self._encontrar_texto_por_tag(root, "tpEvento")
    if tp_evento == "110111":
      return False, "XML rejeitado: NFC-e cancelada não pode ser importada."

    modelo = self._encontrar_texto_por_tag(root, "mod")
    if modelo != "65":
      return True, ""

    status = self._encontrar_texto_por_tag(root, "cStat")
    if status in {"100", "150"}:
      return True, ""

    if status == "101":
      return False, "XML rejeitado: NFC-e cancelada não pode ser importada."

    return False, "XML rejeitado: somente NFC-e autorizada pode ser importada."
  
  def _validar_nfse_autorizada(self, root: ET.Element) -> tuple[bool, str]:
    numero_nfse = self._encontrar_texto_por_tag(root, "Numero")
    data_emissao = self._encontrar_texto_por_tag(root, "DataEmissao")
    if not numero_nfse or not data_emissao:
      return False, "XML rejeitado: NFSe inválida sem número ou data de emissão."

    sucesso_cancelamento = self._encontrar_texto_por_tag(root, "Sucesso")
    if sucesso_cancelamento and sucesso_cancelamento.lower() == "true":
      return False, "XML rejeitado: NFSe cancelada não pode ser importada."

    return True, ""

  def _encontrar_texto_por_tag(self, root: ET.Element, nome_tag: str) -> str | None:
    elemento = next(
      (element for element in root.iter() if element.tag.split("}")[-1] == nome_tag),
      None,
    )
    if elemento is None:
      return None

    if elemento.text is None:
      return ""

    return elemento.text.strip()
