from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Iterable

import psycopg

from app.domain.sped.reader import resumir_registros_sped_bytes
from app.services.sped.postgres_config import carregar_config_postgres_sped

@dataclass
class SpedImportacaoResultado:
  arquivo: str
  cnpj_emitente: str | None
  status: str
  mensagem: str

class SpedImportacaoService:
  def __init__(self):
    self.config = carregar_config_postgres_sped()

  def importar_arquivos(
    self,
    arquivos: Iterable[tuple[str, bytes]],
    cnpj_empresa_origem: str,
  ) -> list[SpedImportacaoResultado]:
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
      self._garantir_tabela(conn)

      for nome_arquivo, conteudo in arquivos:
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
      self._garantir_tabela(conn)

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
      self._garantir_tabela(conn)
      self._garantir_tabelas_analiticas(conn)

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
        self._carregar_sped_em_tabelas(conn, cnpj_normalizado, conteudo)

      if ids_processados:
        self._atualizar_kpis(conn, cnpj_normalizado, ids_processados)

      conn.commit()

    return contador_registros, total_linhas, ids_processados

  def marcar_como_processados(self, ids_sped: list[int]) -> None:
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
      
  def _carregar_sped_em_tabelas(self, conn: psycopg.Connection, cnpj_emitente: str, conteudo: bytes) -> None:
    linhas = conteudo.decode("latin-1", errors="ignore").splitlines()

    participantes: dict[str, tuple[str, str | None, str | None]] = {}
    produtos: dict[str, tuple[str, str | None, str | None, str | None]] = {}
    participante_ids: dict[str, int] = {}
    produto_ids: dict[str, int] = {}
    documento_id_atual: int | None = None
    periodo_ano: int | None = None
    periodo_mes: int | None = None

    with conn.cursor() as cur:
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
          municipio = (partes[8] if len(partes) > 8 else "").strip() or None
          participantes[codigo] = (nome, cnpj_cpf, municipio)
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
              situacao
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
          
          cur.execute(
            """
            INSERT INTO sped_apuracao_icms (
              empresa_cnpj,
              periodo_ano,            
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
            """,
              periodo_mes,
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
            ),
          
          if cur.rowcount == 0:
            cur.execute(
              """
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
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
              """,
              (
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
              desconto
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
              documento_id_atual,
              produto_id,
              self._to_int(partes[2] if len(partes) > 2 else None),
              (partes[11] if len(partes) > 11 else None) or None,
              self._to_decimal(partes[5] if len(partes) > 5 else None),
              self._to_decimal(partes[6] if len(partes) > 6 else None),
              self._to_decimal(partes[7] if len(partes) > 7 else None),
              self._to_decimal(partes[8] if len(partes) > 8 else None),
            ),
          )

  def _upsert_participante(
    self,
    cur,
    cache_ids: dict[str, int],
    participantes: dict[str, tuple[str, str | None, str | None]],
    cnpj_emitente: str,
    codigo: str,
  ) -> int | None:
    if not codigo:
      return None
    if codigo in cache_ids:
      return cache_ids[codigo]

    nome, cnpj_cpf, municipio = participantes.get(codigo, ("Participante não identificado", None, None))
    cur.execute(
      """
      INSERT INTO sped_participantes (empresa_cnpj, codigo, nome, cnpj_cpf, municipio)
      VALUES (%s, %s, %s, %s, %s)
      ON CONFLICT (empresa_cnpj, codigo)
      DO UPDATE SET
        nome = EXCLUDED.nome,
        cnpj_cpf = COALESCE(EXCLUDED.cnpj_cpf, sped_participantes.cnpj_cpf),
        municipio = COALESCE(EXCLUDED.municipio, sped_participantes.municipio)
      RETURNING id
      """,
      (cnpj_emitente, codigo, nome, cnpj_cpf, municipio),
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
            ticket_medio
          )
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
          ),
        )

  def _garantir_tabela(self, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_importados (
          id BIGSERIAL PRIMARY KEY,
          cnpj_emitente VARCHAR(20) NOT NULL,
          nome_arquivo TEXT NOT NULL,
          hash_arquivo VARCHAR(64) NOT NULL,
          tamanho_bytes BIGINT,
          conteudo_txt BYTEA,
          processado_em TIMESTAMPTZ,
          criado_em TIMESTAMPTZ DEFAULT NOW(),
          UNIQUE (cnpj_emitente, hash_arquivo)
        )
        """
      )

      cur.execute("ALTER TABLE sped_importados ADD COLUMN IF NOT EXISTS conteudo_txt BYTEA")
      cur.execute("ALTER TABLE sped_importados ADD COLUMN IF NOT EXISTS processado_em TIMESTAMPTZ")
      
  def _garantir_tabelas_analiticas(self, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_empresas (
          cnpj CHAR(14) PRIMARY KEY,
          razao_social VARCHAR(255)
        )
        """
      )
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_participantes (
          id SERIAL PRIMARY KEY,
          empresa_cnpj CHAR(14),
          codigo VARCHAR(60),
          nome VARCHAR(255),
          cnpj_cpf VARCHAR(14),
          municipio VARCHAR(100),
          UNIQUE (empresa_cnpj, codigo)
        )
        """
      )
      cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_participantes_empresa_codigo
        ON sped_participantes (empresa_cnpj, codigo)
        """
      )
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_produtos (
          id SERIAL PRIMARY KEY,
          empresa_cnpj CHAR(14),
          codigo VARCHAR(60),
          descricao VARCHAR(255),
          ncm VARCHAR(10),
          unidade VARCHAR(10),
          tipo_item VARCHAR(10),
          UNIQUE (empresa_cnpj, codigo)
        )
        """
      )
      cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_empresa_codigo
        ON sped_produtos (empresa_cnpj, codigo)
        """
      )
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_documentos_fiscais (
          id SERIAL PRIMARY KEY,
          empresa_cnpj CHAR(14),
          participante_id INT,
          modelo INT,
          serie VARCHAR(10),
          numero INT,
          chave_acesso VARCHAR(44),
          tipo_operacao VARCHAR(10),
          data_emissao DATE,
          data_movimentacao DATE,
          valor_total NUMERIC(15,2),
          valor_produtos NUMERIC(15,2),
          valor_frete NUMERIC(15,2),
          valor_desconto NUMERIC(15,2),
          situacao VARCHAR(20)
        )
        """
      )
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_documento_itens (
          id SERIAL PRIMARY KEY,
          documento_id INT,
          produto_id INT,
          numero_item INT,
          cfop VARCHAR(4),
          quantidade NUMERIC(15,4),
          valor_unitario NUMERIC(15,6),
          valor_total NUMERIC(15,2),
          desconto NUMERIC(15,2)
        )
        """
      )
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_kpis_fiscal (
          id SERIAL PRIMARY KEY,
          processamento_id INTEGER NOT NULL,
          cnpj_emitente VARCHAR(14) NOT NULL,
          periodo_ano INTEGER NOT NULL,
          periodo_mes INTEGER NOT NULL,
          total_documentos INTEGER DEFAULT 0,
          total_itens INTEGER DEFAULT 0,
          valor_total_saidas NUMERIC(15,2) DEFAULT 0,
          valor_total_produtos NUMERIC(15,2) DEFAULT 0,
          valor_total_frete NUMERIC(15,2) DEFAULT 0,
          valor_total_descontos NUMERIC(15,2) DEFAULT 0,
          icms_valor_debitado NUMERIC(15,2) DEFAULT 0,
          ipi_valor NUMERIC(15,2) DEFAULT 0,
          ticket_medio NUMERIC(15,2) DEFAULT 0,
          data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (cnpj_emitente, periodo_ano, periodo_mes)
        )
        """
      )
      
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sped_apuracao_icms (
          id SERIAL PRIMARY KEY,
          empresa_cnpj CHAR(14) NOT NULL,
          periodo_ano INTEGER NOT NULL,
          periodo_mes INTEGER NOT NULL,
          total_debitos NUMERIC(15,2) DEFAULT 0,
          ajustes_debitos NUMERIC(15,2) DEFAULT 0,
          total_creditos NUMERIC(15,2) DEFAULT 0,
          ajustes_creditos NUMERIC(15,2) DEFAULT 0,
          saldo_apurado NUMERIC(15,2) DEFAULT 0,
          valor_icms_recolher NUMERIC(15,2) DEFAULT 0,
          saldo_credor_transportar NUMERIC(15,2) DEFAULT 0,
          debitos_especiais NUMERIC(15,2) DEFAULT 0,
          atualizado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (empresa_cnpj, periodo_ano, periodo_mes)
        )
        """
      )
      
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS total_debitos NUMERIC(15,2) DEFAULT 0")
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS ajustes_debitos NUMERIC(15,2) DEFAULT 0")
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS total_creditos NUMERIC(15,2) DEFAULT 0")
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS ajustes_creditos NUMERIC(15,2) DEFAULT 0")
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS saldo_apurado NUMERIC(15,2) DEFAULT 0")
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS valor_icms_recolher NUMERIC(15,2) DEFAULT 0")
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS saldo_credor_transportar NUMERIC(15,2) DEFAULT 0")
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS debitos_especiais NUMERIC(15,2) DEFAULT 0")
      cur.execute("ALTER TABLE sped_apuracao_icms ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")

  def _normalizar_cnpj(self, cnpj: str | None) -> str | None:
    if not cnpj:
      return None

    digits = "".join(ch for ch in cnpj if ch.isdigit())
    if len(digits) == 14:
      return digits

    return None
  
  def _normalizar_documento(self, value: str | None) -> str | None:
    if not value:
      return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits or None

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