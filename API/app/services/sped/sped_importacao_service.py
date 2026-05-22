from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

import psycopg

from app.domain.sped.reader import resumir_registros_sped_bytes
from app.services.reforma_tributaria.reforma_tributaria_sync_service import ReformaTributariaSyncService
from app.services.sped.postgres_config import carregar_config_postgres_sped

@dataclass
class SpedImportacaoResultado:
  arquivo: str
  cnpj_emitente: str | None
  status: str
  mensagem: str

class SpedImportacaoService:
  """Gerencia staging, carga analítica e pós-processamento de arquivos SPED importados."""

  _required_analytic_columns_by_table = {
    "sped_empresas": {
      "cnpj",
      "razao_social",
    },
    "sped_participantes": {
      "id",
      "empresa_cnpj",
      "codigo",
      "nome",
      "cnpj_cpf",
      "municipio",
      "municipio_nome",
      "uf",
    },
    "sped_produtos": {
      "id",
      "empresa_cnpj",
      "codigo",
      "descricao",
      "ncm",
      "unidade",
      "tipo_item",
    },
    "sped_documentos_fiscais": {
      "id",
      "empresa_cnpj",
      "participante_id",
      "modelo",
      "serie",
      "numero",
      "chave_acesso",
      "tipo_operacao",
      "data_emissao",
      "data_movimentacao",
      "valor_total",
      "valor_produtos",
      "valor_frete",
      "valor_desconto",
      "situacao",
      "origem_importacao_id",
    },
    "sped_documento_itens": {
      "id",
      "documento_id",
      "produto_id",
      "numero_item",
      "cfop",
      "quantidade",
      "valor_unitario",
      "valor_total",
      "desconto",
      "cst_icms",
      "valor_bc_icms",
      "aliquota_icms",
      "valor_icms",
      "valor_bc_ipi",
      "aliquota_ipi",
      "valor_ipi",
      "valor_pis",
      "valor_cofins",
    },
    "sped_kpis_fiscal": {
      "id",
      "processamento_id",
      "cnpj_emitente",
      "periodo_ano",
      "periodo_mes",
      "total_documentos",
      "total_itens",
      "valor_total_saidas",
      "valor_total_produtos",
      "valor_total_frete",
      "valor_total_descontos",
      "icms_valor_debitado",
      "ipi_valor",
      "pis_valor",
      "cofins_valor",
      "ticket_medio",
      "data_calculo",
    },
    "sped_apuracao_icms": {
      "id",
      "empresa_cnpj",
      "periodo_ano",
      "periodo_mes",
      "total_debitos",
      "ajustes_debitos",
      "total_creditos",
      "ajustes_creditos",
      "saldo_apurado",
      "valor_icms_recolher",
      "saldo_credor_transportar",
      "debitos_especiais",
      "atualizado_em",
    },
  }
  def __init__(self):
    self.config = carregar_config_postgres_sped()
    self._cache_municipios: dict[str, str | None] = {}
    self._municipios_por_codigo = self._carregar_municipios_locais()

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

    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      self._validar_tabela_staging(conn)

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

        with conn.cursor() as cur:
          cur.execute(
            """
            SELECT id
            FROM sped_importados
            WHERE cnpj_emitente = %s
              AND hash_arquivo = %s
            LIMIT 1
            """,
            (cnpj_normalizado, hash_arquivo),
          )
          existente = cur.fetchone()

          if existente:
            resultados.append(
              SpedImportacaoResultado(
                arquivo=nome_arquivo,
                cnpj_emitente=cnpj_normalizado,
                status="duplicado",
                mensagem="Esse arquivo SPED já foi importado para este CNPJ.",
              )
            )
            continue

          cur.execute(
            """
            INSERT INTO sped_importados (
              cnpj_emitente,
              nome_arquivo,
              hash_arquivo,
              tamanho_bytes,
              conteudo_txt
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (cnpj_normalizado, nome_arquivo, hash_arquivo, len(conteudo), conteudo),
          )

        resultados.append(
          SpedImportacaoResultado(
            arquivo=nome_arquivo,
            cnpj_emitente=cnpj_normalizado,
            status="importado",
            mensagem="Arquivo SPED importado com sucesso.",
          )
        )

      conn.commit()

    return resultados

  def contar_pendentes(self, cnpj_emitente: str) -> int:
    cnpj_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_normalizado:
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
          FROM sped_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          """,
          (cnpj_normalizado,),
        )
        row = cur.fetchone()

    return int(row[0] or 0) if row else 0

  def processar_importados(self, cnpj_emitente: str) -> tuple[Counter, int, list[int]]:
    """Carrega arquivos pendentes nas tabelas analíticas e retorna IDs aptos a finalização."""

    cnpj_normalizado = self._normalizar_cnpj(cnpj_emitente)
    if not cnpj_normalizado:
      raise ValueError("CNPJ emitente inválido.")

    contador_registros: Counter = Counter()
    total_linhas = 0
    ids_processados: list[int] = []

    with psycopg.connect(
      host=self.config["host"],
      port=self.config["port"],
      dbname=self.config["database"],
      user=self.config["user"],
      password=self.config["password"],
    ) as conn:
      self._validar_tabela_staging(conn)
      self._validar_tabelas_analiticas(conn)

      with conn.cursor() as cur:
        cur.execute(
          """
          SELECT id, conteudo_txt
          FROM sped_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          ORDER BY id ASC
          """,
          (cnpj_normalizado,),
        )
        rows = cur.fetchall()

      for row in rows:
        sped_id = int(row[0])
        conteudo = bytes(row[1]) if row[1] else b""
        registros, linhas = resumir_registros_sped_bytes(conteudo)
        contador_registros.update(registros)
        total_linhas += linhas
        ids_processados.append(sped_id)
        self._carregar_sped_em_tabelas(conn, cnpj_normalizado, conteudo, sped_id)

      if ids_processados:
        self._atualizar_kpis(conn, cnpj_normalizado, ids_processados)
        reforma_sync_service = ReformaTributariaSyncService()
        reforma_sync_service.sincronizar_sped_apuracao_icms(conn, cnpj_normalizado)
        reforma_sync_service.sincronizar_sped_documentos_itens_icms(conn, cnpj_normalizado)
        
      self._atualizar_nomes_municipios_participantes(conn, cnpj_normalizado)

      conn.commit()

    return contador_registros, total_linhas, ids_processados

  def marcar_como_processados(self, ids_sped: list[int]) -> None:
    """Marca SPEDs como processados após a carga analítica e sincronização fiscal concluírem."""

    if not ids_sped:
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
          UPDATE sped_importados
          SET processado_em = NOW()
          WHERE id = ANY(%s)
          """,
          (ids_sped,),
        )
      conn.commit()
      
  def _carregar_sped_em_tabelas(
    self,
    conn: psycopg.Connection,
    cnpj_emitente: str,
    conteudo: bytes,
    importacao_id: int,
  ) -> None:
    linhas = conteudo.decode("latin-1", errors="ignore").splitlines()

    participantes: dict[str, tuple[str, str | None, str | None, str | None, str | None]] = {}
    produtos: dict[str, tuple[str, str | None, str | None, str | None]] = {}
    participante_ids: dict[str, int] = {}
    produto_ids: dict[str, int] = {}
    documento_id_atual: int | None = None
    periodo_ano: int | None = None
    periodo_mes: int | None = None

    with conn.cursor() as cur:
      cur.execute(
        """
        DELETE FROM sped_documento_itens i
        USING sped_documentos_fiscais d
        WHERE i.documento_id = d.id
          AND d.origem_importacao_id = %s
        """,
        (importacao_id,),
      )
      cur.execute(
        """
        DELETE FROM sped_documentos_fiscais
        WHERE origem_importacao_id = %s
        """,
        (importacao_id,),
      )

      cur.execute(
        """
        INSERT INTO sped_empresas (cnpj, razao_social)
        VALUES (%s, %s)
        ON CONFLICT (cnpj) DO NOTHING
        """,
        (cnpj_emitente, "Empresa SPED"),
      )

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
          participante_id = self._upsert_participante(cur, participante_ids, participantes, cnpj_emitente, cod_part)

          data_emissao = self._to_date(partes[10] if len(partes) > 10 else None)
          data_movimentacao = self._to_date(partes[11] if len(partes) > 11 else None)

          cur.execute(
            """
            INSERT INTO sped_documentos_fiscais (
              empresa_cnpj,
              participante_id,
              modelo,
              serie,
              numero,
              chave_acesso,
              tipo_operacao,
              data_emissao,
              data_movimentacao,
              valor_total,
              valor_produtos,
              valor_frete,
              valor_desconto,
              situacao,
              origem_importacao_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
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
              "normal",
              importacao_id,
            ),
          )
          documento_id_atual = int(cur.fetchone()[0])
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
          
          cur.execute (
            """
            WITH updated AS (
              UPDATE sped_apuracao_icms
              SET
                total_debitos = %s,
                ajustes_debitos = %s,
                total_creditos = %s,
                ajustes_creditos = %s,
                saldo_apurado = %s,
                valor_icms_recolher = %s,
                saldo_credor_transportar = %s,
                debitos_especiais = %s,
                atualizado_em = CURRENT_TIMESTAMP
              WHERE empresa_cnpj = %s
                AND periodo_ano = %s
                AND periodo_mes = %s
              RETURNING id
            )
            
            INSERT INTO sped_apuracao_icms (
              empresa_cnpj,
              periodo_ano,
              periodo_mes,
              total_debitos,
              ajustes_debitos,
              total_creditos,
              ajustes_creditos,
              saldo_apurado,
              valor_icms_recolher,
              saldo_credor_transportar,
              debitos_especiais
            )
            
            SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            WHERE NOT EXISTS (SELECT 1 FROM updated)
            """,
            (
              total_debitos,
              ajustes_debitos,
              total_creditos,
              ajustes_creditos,
              saldo_apurado,
              valor_icms_recolher,
              saldo_credor_transportar,
              debitos_especiais,
              cnpj_emitente,
              periodo_ano,
              periodo_mes,
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
            ),
          )
          
          continue

        if registro == "C170" and documento_id_atual:
          codigo_item = (partes[3] if len(partes) > 3 else "").strip()
          produto_id = self._upsert_produto(cur, produto_ids, produtos, cnpj_emitente, codigo_item)
          quantidade = self._to_decimal(partes[5] if len(partes) > 5 else None)
          valor_total_item = self._to_decimal(partes[7] if len(partes) > 7 else None)

          cur.execute(
            """
            INSERT INTO sped_documento_itens (
              documento_id,
              produto_id,
              numero_item,
              cfop,
              quantidade,
              valor_unitario,
              valor_total,
              desconto,
              cst_icms,
              valor_bc_icms,
              aliquota_icms,
              valor_icms,
              valor_bc_ipi,
              aliquota_ipi,
              valor_ipi,
              valor_pis,
              valor_cofins
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
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
            ),
          )

  def _upsert_participante(
    self,
    cur,
    cache_ids: dict[str, int],
    participantes: dict[str, tuple[str, str | None, str | None, str | None, str | None]],
    cnpj_emitente: str,
    codigo: str,
  ) -> int | None:
    if not codigo:
      return None
    if codigo in cache_ids:
      return cache_ids[codigo]

    nome, cnpj_cpf, municipio, municipio_nome, uf = participantes.get(codigo, ("Participante não identificado", None, None, None, None))
    cur.execute(
      """
      INSERT INTO sped_participantes (empresa_cnpj, codigo, nome, cnpj_cpf, municipio, municipio_nome, uf)
      VALUES (%s, %s, %s, %s, %s, %s, %s)
      ON CONFLICT (empresa_cnpj, codigo)
      DO UPDATE SET
        nome = EXCLUDED.nome,
        cnpj_cpf = COALESCE(EXCLUDED.cnpj_cpf, sped_participantes.cnpj_cpf),
        municipio = COALESCE(EXCLUDED.municipio, sped_participantes.municipio),
        municipio_nome = COALESCE(EXCLUDED.municipio_nome, sped_participantes.municipio_nome),
        uf = COALESCE(EXCLUDED.uf, sped_participantes.uf)
      RETURNING id
      """,
      (cnpj_emitente, codigo, nome, cnpj_cpf, municipio, municipio_nome, uf)
    )
    participante_id = int(cur.fetchone()[0])
    cache_ids[codigo] = participante_id
    return participante_id

  def _upsert_produto(
    self,
    cur,
    cache_ids: dict[str, int],
    produtos: dict[str, tuple[str, str | None, str | None, str | None]],
    cnpj_emitente: str,
    codigo_item: str,
  ) -> int | None:
    if not codigo_item:
      return None
    if codigo_item in cache_ids:
      return cache_ids[codigo_item]

    descricao, ncm, unidade, tipo_item = produtos.get(codigo_item, ("Produto não identificado", None, None, None))
    cur.execute(
      """
      INSERT INTO sped_produtos (empresa_cnpj, codigo, descricao, ncm, unidade, tipo_item)
      VALUES (%s, %s, %s, %s, %s, %s)
      ON CONFLICT (empresa_cnpj, codigo)
      DO UPDATE SET
        descricao = EXCLUDED.descricao,
        ncm = COALESCE(EXCLUDED.ncm, sped_produtos.ncm),
        unidade = COALESCE(EXCLUDED.unidade, sped_produtos.unidade),
        tipo_item = COALESCE(EXCLUDED.tipo_item, sped_produtos.tipo_item)
      RETURNING id
      """,
      (cnpj_emitente, codigo_item, descricao, ncm, unidade, tipo_item),
    )
    produto_id = int(cur.fetchone()[0])
    cache_ids[codigo_item] = produto_id
    return produto_id
  
  def _atualizar_nomes_municipios_participantes(self, conn: psycopg.Connection, cnpj_emitente: str) -> None:
    self._carregar_base_municipios_ibge()

    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT id, municipio
        FROM sped_participantes
        WHERE empresa_cnpj = %s
          AND municipio IS NOT NULL
          AND (
            municipio_nome IS NULL
            OR NULLIF(TRIM(municipio_nome), '') IS NULL
            OR TRIM(municipio_nome) = 'Cidade não identificada'
          )
        """,
        (cnpj_emitente,),
      )
      rows = cur.fetchall()

      atualizacoes: list[tuple[str, int]] = []
      for participante_id, codigo_municipio in rows:
        nome_municipio = self._obter_nome_municipio(str(codigo_municipio or ""))
        if nome_municipio:
          atualizacoes.append((nome_municipio, int(participante_id)))

      if atualizacoes:
        cur.executemany(
          """
          UPDATE sped_participantes
          SET municipio_nome = %s
          WHERE id = %s
          """,
          atualizacoes,
        )

  def _atualizar_kpis(self, conn: psycopg.Connection, cnpj_emitente: str, ids_sped: list[int]) -> None:
    processamento_id = max(ids_sped)
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT
          EXTRACT(YEAR FROM data_emissao)::int AS ano,
          EXTRACT(MONTH FROM data_emissao)::int AS mes,
          COUNT(*) AS total_documentos,
          COALESCE(SUM(valor_total), 0) AS valor_total,
          COALESCE(SUM(CASE WHEN tipo_operacao = 'saida' THEN valor_total ELSE 0 END), 0) AS valor_total_saidas,
          COALESCE(SUM(valor_produtos), 0) AS valor_total_produtos,
          COALESCE(SUM(valor_frete), 0) AS valor_total_frete,
          COALESCE(SUM(valor_desconto), 0) AS valor_total_descontos,
          CASE WHEN COUNT(*) > 0 THEN COALESCE(SUM(valor_total), 0) / COUNT(*) ELSE 0 END AS ticket_medio
        FROM sped_documentos_fiscais
        WHERE regexp_replace(empresa_cnpj, '\\D', '', 'g') = %s
          AND data_emissao IS NOT NULL
        GROUP BY 1, 2
        """,
        (cnpj_emitente,),
      )
      periodos = cur.fetchall()

      for ano, mes, total_documentos, valor_total, valor_total_saidas, valor_total_produtos, valor_total_frete, valor_total_descontos, ticket_medio in periodos:
        cur.execute(
          """
          SELECT COALESCE(total_debitos, 0)
          FROM sped_apuracao_icms
          WHERE regexp_replace(empresa_cnpj, '\\D', '', 'g') = %s
            AND periodo_ano = %s
            AND periodo_mes = %s
          LIMIT 1
          """,
          (cnpj_emitente, ano, mes),
        )
        row_icms = cur.fetchone()
        valor_icms_debitado = row_icms[0] if row_icms else Decimal("0")
        
        cur.execute(
          """
          SELECT COUNT(*)
          FROM sped_documento_itens i
          JOIN sped_documentos_fiscais d ON d.id = i.documento_id
          WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
            AND EXTRACT(YEAR FROM d.data_emissao) = %s
            AND EXTRACT(MONTH FROM d.data_emissao) = %s
          """,
          (cnpj_emitente, ano, mes),
        )
        total_itens = int(cur.fetchone()[0] or 0)

        cur.execute(
          """
          SELECT
            COALESCE(SUM(i.valor_ipi), 0),
            COALESCE(SUM(i.valor_pis), 0),
            COALESCE(SUM(i.valor_cofins), 0)
          FROM sped_documento_itens i
          JOIN sped_documentos_fiscais d ON d.id = i.documento_id
          WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
            AND EXTRACT(YEAR FROM d.data_emissao) = %s
            AND EXTRACT(MONTH FROM d.data_emissao) = %s
          """,
          (cnpj_emitente, ano, mes),
        )
        row_impostos_itens = cur.fetchone()
        valor_ipi = row_impostos_itens[0] if row_impostos_itens else Decimal("0")
        valor_pis = row_impostos_itens[1] if row_impostos_itens else Decimal("0")
        valor_cofins = row_impostos_itens[2] if row_impostos_itens else Decimal("0")

        cur.execute(
          """
          INSERT INTO sped_kpis_fiscal (
            processamento_id,
            cnpj_emitente,
            periodo_ano,
            periodo_mes,
            total_documentos,
            total_itens,
            valor_total_saidas,
            valor_total_produtos,
            valor_total_frete,
            valor_total_descontos,
            icms_valor_debitado,
            ticket_medio,
            ipi_valor,
            pis_valor,
            cofins_valor
          )
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
          ON CONFLICT (cnpj_emitente, periodo_ano, periodo_mes)
          DO UPDATE SET
            processamento_id = EXCLUDED.processamento_id,
            total_documentos = EXCLUDED.total_documentos,
            total_itens = EXCLUDED.total_itens,
            valor_total_saidas = EXCLUDED.valor_total_saidas,
            valor_total_produtos = EXCLUDED.valor_total_produtos,
            valor_total_frete = EXCLUDED.valor_total_frete,
            valor_total_descontos = EXCLUDED.valor_total_descontos,
            icms_valor_debitado = EXCLUDED.icms_valor_debitado,
            ticket_medio = EXCLUDED.ticket_medio,
            ipi_valor = EXCLUDED.ipi_valor,
            pis_valor = EXCLUDED.pis_valor,
            cofins_valor = EXCLUDED.cofins_valor,
            data_calculo = CURRENT_TIMESTAMP
          """,
          (
            processamento_id,
            cnpj_emitente,
            int(ano),
            int(mes),
            int(total_documentos or 0),
            total_itens,
            valor_total_saidas,
            valor_total_produtos,
            valor_total_frete,
            valor_total_descontos,
            valor_icms_debitado,
            ticket_medio,
            valor_ipi,
            valor_pis,
            valor_cofins,
          ),
        )

  def _validar_tabela_staging(self, conn: psycopg.Connection) -> None:
    required_columns = {
      "id",
      "cnpj_emitente",
      "nome_arquivo",
      "hash_arquivo",
      "tamanho_bytes",
      "conteudo_txt",
      "processado_em",
      "criado_em",
    }

    with conn.cursor() as cur:
      cur.execute("SELECT to_regclass('public.sped_importados')")
      if cur.fetchone()[0] is None:
        raise RuntimeError(
          "Tabela public.sped_importados nao encontrada. Execute as migrations Alembic antes de importar SPED."
        )

      cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'sped_importados'
        """
      )
      existing_columns = {row[0] for row in cur.fetchall()}

    missing_columns = sorted(required_columns - existing_columns)
    if missing_columns:
      raise RuntimeError(
        "Tabela public.sped_importados incompleta. Execute as migrations Alembic. "
        f"Colunas ausentes: {', '.join(missing_columns)}."
      )
      
  def _validar_tabelas_analiticas(self, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        """,
        (list(self._required_analytic_columns_by_table),),
      )
      existing_columns: dict[str, set[str]] = {
        table_name: set()
        for table_name in self._required_analytic_columns_by_table
      }
      for table_name, column_name in cur.fetchall():
        existing_columns[str(table_name)].add(str(column_name))

      cur.execute(
        """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
          AND constraint_type IN ('PRIMARY KEY', 'UNIQUE')
        """,
        (list(self._required_analytic_columns_by_table),),
      )
      existing_constraints = {str(row[0]) for row in cur.fetchall()}

      cur.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = ANY(%s)
        """,
        (list(self._required_analytic_columns_by_table),),
      )
      existing_unique_guards = existing_constraints | {str(row[0]) for row in cur.fetchall()}

    missing_parts = []
    for table_name, required_columns in self._required_analytic_columns_by_table.items():
      missing_columns = sorted(required_columns - existing_columns[table_name])
      if missing_columns:
        missing_parts.append(f"{table_name}: {', '.join(missing_columns)}")

    if missing_parts:
      raise RuntimeError(
        "Schema analitico SPED incompleto. Execute as migrations Alembic. "
        f"Colunas ausentes em public: {'; '.join(missing_parts)}."
      )

    required_unique_groups = [
      {"sped_empresas_pkey"},
      {"sped_participantes_empresa_cnpj_codigo_key", "ux_participantes_empresa_codigo"},
      {"sped_produtos_empresa_cnpj_codigo_key", "ux_produtos_empresa_codigo"},
      {"sped_kpis_fiscal_cnpj_emitente_periodo_ano_periodo_mes_key", "ux_sped_kpis_fiscal_periodo"},
      {"sped_apuracao_icms_empresa_cnpj_periodo_ano_periodo_mes_key", "ux_sped_apuracao_icms_periodo"},
    ]
    missing_unique_guards = [
      " ou ".join(sorted(group))
      for group in required_unique_groups
      if not group & existing_unique_guards
    ]
    if missing_unique_guards:
      raise RuntimeError(
        "Schema analitico SPED sem unicidade esperada. Execute as migrations Alembic. "
        f"Constraints/indices ausentes em public: {', '.join(missing_unique_guards)}."
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
