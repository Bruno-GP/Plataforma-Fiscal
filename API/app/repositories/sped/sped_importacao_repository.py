from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from typing import Callable, Iterator

import psycopg

from app.services.sped.postgres_config import carregar_config_postgres_sped


class SpedImportacaoRepository:
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

  def __init__(self, conn_params: dict | None = None):
    self.config = conn_params or carregar_config_postgres_sped()
    self.conn_params = self._normalizar_conn_params(self.config)

  def _normalizar_conn_params(self, config: dict) -> dict:
    return {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      **({"sslmode": config["sslmode"]} if config.get("sslmode") else {}),
    }

  @contextmanager
  def transacao(self) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(**self.conn_params)
    try:
      yield conn
      conn.commit()
    except Exception:
      conn.rollback()
      raise
    finally:
      conn.close()

  def contar_pendentes(self, cnpj_emitente: str, conn: psycopg.Connection | None = None) -> int:
    if conn is not None:
      with conn.cursor() as cur:
        cur.execute(
          """
          SELECT COUNT(*)
          FROM sped_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          """,
          (cnpj_emitente,),
        )
        row = cur.fetchone()

      return int(row[0] or 0) if row else 0

    with psycopg.connect(**self.conn_params) as conn_aberta:
      with conn_aberta.cursor() as cur:
        cur.execute(
          """
          SELECT COUNT(*)
          FROM sped_importados
          WHERE cnpj_emitente = %s
            AND processado_em IS NULL
          """,
          (cnpj_emitente,),
        )
        row = cur.fetchone()

    return int(row[0] or 0) if row else 0

  def validar_tabela_staging(self, conn: psycopg.Connection) -> None:
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

  def validar_tabelas_analiticas(self, conn: psycopg.Connection) -> None:
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

  def importacao_existe(self, conn: psycopg.Connection, cnpj_emitente: str, hash_arquivo: str) -> bool:
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT id
        FROM sped_importados
        WHERE cnpj_emitente = %s
          AND hash_arquivo = %s
        LIMIT 1
        """,
        (cnpj_emitente, hash_arquivo),
      )
      return cur.fetchone() is not None

  def inserir_importacao(
    self,
    conn: psycopg.Connection,
    cnpj_emitente: str,
    nome_arquivo: str,
    hash_arquivo: str,
    tamanho_bytes: int,
    conteudo_txt: bytes,
  ) -> None:
    with conn.cursor() as cur:
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
        (cnpj_emitente, nome_arquivo, hash_arquivo, tamanho_bytes, conteudo_txt),
      )

  def listar_importacoes_pendentes(self, conn: psycopg.Connection, cnpj_emitente: str) -> list[tuple[int, bytes]]:
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT id, conteudo_txt
        FROM sped_importados
        WHERE cnpj_emitente = %s
          AND processado_em IS NULL
        ORDER BY id ASC
        """,
        (cnpj_emitente,),
      )
      return cur.fetchall()

  def remover_dados_importacao(self, conn: psycopg.Connection, importacao_id: int) -> None:
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

  def garantir_empresa(self, conn: psycopg.Connection, cnpj_emitente: str) -> None:
    with conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO sped_empresas (cnpj, razao_social)
        VALUES (%s, %s)
        ON CONFLICT (cnpj) DO NOTHING
        """,
        (cnpj_emitente, "Empresa SPED"),
      )

  def upsert_participante(
    self,
    conn: psycopg.Connection,
    cache_ids: dict[str, int],
    participantes: dict[str, tuple[str, str | None, str | None, str | None, str | None]],
    cnpj_emitente: str,
    codigo: str,
  ) -> int | None:
    if not codigo:
      return None
    if codigo in cache_ids:
      return cache_ids[codigo]

    nome, cnpj_cpf, municipio, municipio_nome, uf = participantes.get(
      codigo,
      ("Participante não identificado", None, None, None, None),
    )
    with conn.cursor() as cur:
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
        (cnpj_emitente, codigo, nome, cnpj_cpf, municipio, municipio_nome, uf),
      )
      participante_id = int(cur.fetchone()[0])

    cache_ids[codigo] = participante_id
    return participante_id

  def upsert_produto(
    self,
    conn: psycopg.Connection,
    cache_ids: dict[str, int],
    produtos: dict[str, tuple[str, str | None, str | None, str | None]],
    cnpj_emitente: str,
    codigo_item: str,
  ) -> int | None:
    if not codigo_item:
      return None
    if codigo_item in cache_ids:
      return cache_ids[codigo_item]

    descricao, ncm, unidade, tipo_item = produtos.get(
      codigo_item,
      ("Produto não identificado", None, None, None),
    )
    with conn.cursor() as cur:
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

  def salvar_documento(
    self,
    conn: psycopg.Connection,
    cnpj_emitente: str,
    participante_id: int | None,
    modelo: int | None,
    serie: str | None,
    numero: int | None,
    chave_acesso: str | None,
    tipo_operacao: str,
    data_emissao,
    data_movimentacao,
    valor_total: Decimal,
    valor_produtos: Decimal,
    valor_frete: Decimal,
    valor_desconto: Decimal,
    importacao_id: int,
  ) -> int:
    with conn.cursor() as cur:
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
          "normal",
          importacao_id,
        ),
      )
      return int(cur.fetchone()[0])

  def salvar_item(
    self,
    conn: psycopg.Connection,
    documento_id: int,
    produto_id: int | None,
    numero_item: int | None,
    cfop: str | None,
    quantidade: Decimal,
    valor_unitario: Decimal,
    valor_total: Decimal,
    desconto: Decimal,
    cst_icms: str | None,
    valor_bc_icms: Decimal,
    aliquota_icms: Decimal,
    valor_icms: Decimal,
    valor_bc_ipi: Decimal,
    aliquota_ipi: Decimal,
    valor_ipi: Decimal,
    valor_pis: Decimal,
    valor_cofins: Decimal,
  ) -> None:
    with conn.cursor() as cur:
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
          valor_cofins,
        ),
      )

  def upsert_apuracao_icms(
    self,
    conn: psycopg.Connection,
    cnpj_emitente: str,
    periodo_ano: int,
    periodo_mes: int,
    total_debitos: Decimal,
    ajustes_debitos: Decimal,
    total_creditos: Decimal,
    ajustes_creditos: Decimal,
    saldo_apurado: Decimal,
    valor_icms_recolher: Decimal,
    saldo_credor_transportar: Decimal,
    debitos_especiais: Decimal,
  ) -> None:
    with conn.cursor() as cur:
      cur.execute(
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

  def atualizar_nomes_municipios_participantes(
    self,
    conn: psycopg.Connection,
    cnpj_emitente: str,
    resolver_nome_municipio: Callable[[str | None], str | None],
  ) -> None:
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
        nome_municipio = resolver_nome_municipio(str(codigo_municipio or ""))
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

  def atualizar_kpis(self, conn: psycopg.Connection, cnpj_emitente: str, ids_sped: list[int]) -> None:
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

  def marcar_como_processados(self, ids_sped: list[int]) -> None:
    if not ids_sped:
      return

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(
          """
          UPDATE sped_importados
          SET processado_em = NOW()
          WHERE id = ANY(%s)
          """,
          (ids_sped,),
        )
