import psycopg
from psycopg.rows import dict_row

from app.core.cache import ttl_cache
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.nfe.postres_config import carregar_config_postgres


class ReformaTributariaConsultaService:
  def __init__(self) -> None:
    config = carregar_config_postgres()
    self.conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      "connect_timeout": 5,
    }

    if config.get("conninfo"):
      self.conn_params = {
        "conninfo": config["conninfo"],
        "connect_timeout": 5,
      }

    if config.get("sslmode"):
      self.conn_params["sslmode"] = config["sslmode"]

  @ttl_cache(ttl_seconds=30, maxsize=32)
  def listar_tributos(self, incluir_inativos: bool = False) -> list[dict]:
    filtros = []
    params: list[object] = []

    if not incluir_inativos:
      filtros.append("ativo = TRUE")

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    sql = f"""
      SELECT id, codigo, nome, esfera, tipo, descricao, ativo
      FROM public.tributos
      {where_clause}
      ORDER BY
        CASE tipo
          WHEN 'reforma' THEN 1
          WHEN 'transicao' THEN 2
          ELSE 3
        END,
        codigo;
    """

    with psycopg.connect(**self.conn_params, row_factory=dict_row) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

  def listar_apuracoes(
    self,
    emitente_cnpj: str,
    periodo_ano: int | None = None,
    periodo_mes: int | None = None,
    tributo_codigo: str | None = None,
  ) -> list[dict]:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(a.empresa_cnpj, '\\D', '', 'g') = %s"]
    params: list[object] = [cnpj]

    if periodo_ano is not None:
      filtros.append("a.periodo_ano = %s")
      params.append(periodo_ano)

    if periodo_mes is not None:
      filtros.append("a.periodo_mes = %s")
      params.append(periodo_mes)

    if tributo_codigo:
      filtros.append("UPPER(t.codigo) = UPPER(%s)")
      params.append(tributo_codigo)

    sql = f"""
      SELECT
        a.id,
        a.empresa_cnpj,
        a.periodo_ano,
        a.periodo_mes,
        t.codigo AS tributo_codigo,
        t.nome AS tributo_nome,
        a.total_debitos,
        a.total_creditos,
        a.ajustes_debito,
        a.ajustes_credito,
        a.estornos_debito,
        a.estornos_credito,
        a.compensacoes,
        a.saldo_apurado,
        a.saldo_periodo_anterior,
        a.saldo_a_recolher,
        a.status,
        a.data_fechamento
      FROM public.apuracao_tributaria a
      JOIN public.tributos t ON t.id = a.tributo_id
      WHERE {' AND '.join(filtros)}
      ORDER BY a.periodo_ano DESC, a.periodo_mes DESC, t.codigo;
    """

    with psycopg.connect(**self.conn_params, row_factory=dict_row) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

  def listar_documento_tributos(
    self,
    emitente_cnpj: str,
    origem_documento: str,
    documento_id: int,
  ) -> list[dict]:
    cnpj = normalizar_cnpj(emitente_cnpj)
    origem = self._normalizar_origem_documento(origem_documento)
    coluna = "nota_id" if origem == "nfe" else "sped_documento_id"

    sql = f"""
      SELECT
        dt.id,
        dt.nota_id,
        dt.sped_documento_id,
        t.codigo AS tributo_codigo,
        t.nome AS tributo_nome,
        dt.empresa_cnpj,
        dt.periodo_ano,
        dt.periodo_mes,
        dt.modelo_documento,
        dt.chave_acesso,
        dt.tipo_operacao,
        dt.data_emissao,
        dt.base_calculo,
        dt.valor_debito,
        dt.valor_credito,
        dt.valor_tributo,
        dt.valor_isento,
        dt.valor_outros,
        dt.valor_reducao_base,
        dt.valor_diferido,
        dt.natureza,
        dt.origem,
        dt.status
      FROM public.documentos_fiscais_tributos dt
      JOIN public.tributos t ON t.id = dt.tributo_id
      WHERE dt.{coluna} = %s
        AND regexp_replace(dt.empresa_cnpj, '\\D', '', 'g') = %s
      ORDER BY t.codigo, dt.id;
    """

    with psycopg.connect(**self.conn_params, row_factory=dict_row) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, (documento_id, cnpj))
        return [dict(row) for row in cur.fetchall()]

  def listar_item_tributos(
    self,
    emitente_cnpj: str,
    origem_item: str,
    item_id: int,
  ) -> list[dict]:
    cnpj = normalizar_cnpj(emitente_cnpj)
    origem = self._normalizar_origem_item(origem_item)
    coluna = "nota_item_id" if origem == "nfe" else "sped_item_id"

    sql = f"""
      SELECT
        it.id,
        it.documento_tributo_id,
        it.nota_item_id,
        it.sped_item_id,
        t.codigo AS tributo_codigo,
        t.nome AS tributo_nome,
        it.empresa_cnpj,
        it.periodo_ano,
        it.periodo_mes,
        it.numero_item,
        it.produto_codigo,
        it.ncm_codigo,
        it.cfop,
        it.cst_codigo,
        it.classificacao_tributaria,
        it.base_calculo,
        it.aliquota,
        it.aliquota_federal,
        it.aliquota_estadual,
        it.aliquota_municipal,
        it.percentual_reducao_base,
        it.percentual_diferimento,
        it.valor_debito,
        it.valor_credito,
        it.valor_tributo,
        it.valor_isento,
        it.valor_outros,
        it.valor_reducao_base,
        it.valor_diferido,
        it.valor_credito_presumido,
        it.natureza,
        it.origem,
        it.status
      FROM public.itens_documentos_fiscais_tributos it
      JOIN public.tributos t ON t.id = it.tributo_id
      WHERE it.{coluna} = %s
        AND regexp_replace(it.empresa_cnpj, '\\D', '', 'g') = %s
      ORDER BY it.numero_item NULLS LAST, t.codigo, it.id;
    """

    with psycopg.connect(**self.conn_params, row_factory=dict_row) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, (item_id, cnpj))
        return [dict(row) for row in cur.fetchall()]

  def listar_memoria_calculo(
    self,
    emitente_cnpj: str,
    periodo_ano: int | None = None,
    periodo_mes: int | None = None,
    tributo_codigo: str | None = None,
    documento_tributo_id: int | None = None,
    item_tributo_id: int | None = None,
    limite: int = 100,
    offset: int = 0,
  ) -> list[dict]:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(m.empresa_cnpj, '\\D', '', 'g') = %s"]
    params: list[object] = [cnpj]

    if periodo_ano is not None:
      filtros.append("m.periodo_ano = %s")
      params.append(periodo_ano)

    if periodo_mes is not None:
      filtros.append("m.periodo_mes = %s")
      params.append(periodo_mes)

    if tributo_codigo:
      filtros.append("UPPER(t.codigo) = UPPER(%s)")
      params.append(tributo_codigo)

    if documento_tributo_id is not None:
      filtros.append("m.documento_tributo_id = %s")
      params.append(documento_tributo_id)

    if item_tributo_id is not None:
      filtros.append("m.item_tributo_id = %s")
      params.append(item_tributo_id)

    sql = f"""
      SELECT
        m.id,
        m.documento_tributo_id,
        m.item_tributo_id,
        m.credito_tributario_id,
        m.debito_tributario_id,
        t.codigo AS tributo_codigo,
        t.nome AS tributo_nome,
        m.empresa_cnpj,
        m.periodo_ano,
        m.periodo_mes,
        m.etapa_calculo,
        m.base_origem,
        m.base_calculo,
        m.aliquota_aplicada,
        m.percentual_reducao_base,
        m.percentual_diferimento,
        m.valor_calculado,
        m.formula_calculo,
        m.parametros_calculo,
        m.resultado_calculo,
        m.fonte_dados,
        m.hash_calculo,
        m.criado_em
      FROM public.memoria_calculo_tributaria m
      JOIN public.tributos t ON t.id = m.tributo_id
      WHERE {' AND '.join(filtros)}
      ORDER BY m.criado_em DESC, m.id DESC
      LIMIT %s OFFSET %s;
    """
    params.extend([limite, offset])

    with psycopg.connect(**self.conn_params, row_factory=dict_row) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

  def contar_memoria_calculo(
    self,
    emitente_cnpj: str,
    periodo_ano: int | None = None,
    periodo_mes: int | None = None,
    tributo_codigo: str | None = None,
    documento_tributo_id: int | None = None,
    item_tributo_id: int | None = None,
  ) -> int:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(m.empresa_cnpj, '\\D', '', 'g') = %s"]
    params: list[object] = [cnpj]

    if periodo_ano is not None:
      filtros.append("m.periodo_ano = %s")
      params.append(periodo_ano)

    if periodo_mes is not None:
      filtros.append("m.periodo_mes = %s")
      params.append(periodo_mes)

    if tributo_codigo:
      filtros.append("UPPER(t.codigo) = UPPER(%s)")
      params.append(tributo_codigo)

    if documento_tributo_id is not None:
      filtros.append("m.documento_tributo_id = %s")
      params.append(documento_tributo_id)

    if item_tributo_id is not None:
      filtros.append("m.item_tributo_id = %s")
      params.append(item_tributo_id)

    sql = f"""
      SELECT COUNT(*)
      FROM public.memoria_calculo_tributaria m
      JOIN public.tributos t ON t.id = m.tributo_id
      WHERE {' AND '.join(filtros)};
    """

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row[0] if row else 0)

  @staticmethod
  def _normalizar_origem_documento(origem_documento: str) -> str:
    origem = origem_documento.strip().lower()
    if origem not in {"nfe", "sped"}:
      raise ValueError("Origem do documento deve ser 'nfe' ou 'sped'.")
    return origem

  @staticmethod
  def _normalizar_origem_item(origem_item: str) -> str:
    origem = origem_item.strip().lower()
    if origem not in {"nfe", "sped"}:
      raise ValueError("Origem do item deve ser 'nfe' ou 'sped'.")
    return origem
