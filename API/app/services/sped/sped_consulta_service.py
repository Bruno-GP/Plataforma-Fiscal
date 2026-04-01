from decimal import Decimal
from typing import Optional

import psycopg

from app.models.nfe.schemas import NFeKPI, NFeKPIConsulta
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.sped.postgres_config import carregar_config_postgres_sped

UF_PARA_REGIAO = {
  "AC": "Norte", "AL": "Nordeste", "AP": "Norte", "AM": "Norte", "BA": "Nordeste",
  "CE": "Nordeste", "DF": "Centro-Oeste", "ES": "Sudeste", "GO": "Centro-Oeste",
  "MA": "Nordeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste", "MG": "Sudeste",
  "PA": "Norte", "PB": "Nordeste", "PR": "Sul", "PE": "Nordeste", "PI": "Nordeste",
  "RJ": "Sudeste", "RN": "Nordeste", "RS": "Sul", "RO": "Norte", "RR": "Norte",
  "SC": "Sul", "SP": "Sudeste", "SE": "Nordeste", "TO": "Norte",
}

def _parece_codigo_municipio(valor: object) -> bool:
  codigo = "".join(ch for ch in str(valor or "") if ch.isdigit())
  return len(codigo) in {6, 7}

def _normalizar_nome_cidade(valor: object) -> str:
  cidade = str(valor or "").strip()
  if not cidade:
    return "Cidade não identificada"

  cidade_upper = cidade.upper()
  if len(cidade_upper) == 2 and cidade_upper.isalpha():
    return "Cidade não identificada"
  
  if _parece_codigo_municipio(cidade):
    return "Cidade não identificada"

  for separador in ("/", "-"):
    if separador in cidade:
      partes = [p.strip() for p in cidade.split(separador) if p.strip()]
      if len(partes) >= 2:
        ultimo = partes[-1].upper()
        if len(ultimo) == 2 and ultimo.isalpha():
          return f"{partes[0]} - {ultimo}"

  return cidade

def _obter_regiao_por_uf(uf: object) -> str | None:
  uf_normalizada = str(uf or "").strip().upper()
  return UF_PARA_REGIAO.get(uf_normalizada)

class SpedConsultaService:
  def __init__(self) -> None:
    config = carregar_config_postgres_sped()
    self.conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      "connect_timeout": 5,
    }

  def listar_kpis(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 100,
    offset: int = 0,
  ) -> list[NFeKPIConsulta]:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(cnpj_emitente, '\\D', '', 'g') = %s"]
    params: list[object] = [cnpj]

    if periodo_ano:
      filtros.append("periodo_ano = %s")
      params.append(periodo_ano)
    if periodo_mes:
      filtros.append("periodo_mes = %s")
      params.append(periodo_mes)

    where_clause = " AND ".join(filtros)

    sql_kpis = f"""
      SELECT id,
            processamento_id,
            cnpj_emitente,
            periodo_ano,
            periodo_mes,
            valor_total_saidas,
            total_documentos,
            ticket_medio,
            0::numeric AS maior_nota,
            0::numeric AS menor_nota,
            icms_valor_debitado,
            ipi_valor
      FROM public.sped_kpis_fiscal
      WHERE {where_clause}
      ORDER BY periodo_ano DESC, periodo_mes DESC, id DESC
      LIMIT %s OFFSET %s;
    """

    params.extend([limite, offset])

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
          cur.execute(sql_kpis, params)
          rows = cur.fetchall()

          resultados: list[NFeKPIConsulta] = []
          for row in rows:
            kpi_id, processamento_id, cnpj_emitente, ano, mes, total_vendas, total_docs, ticket_medio, maior_nota, menor_nota, total_icms, total_ipi = row
            top_clientes = self._top_clientes(cur, cnpj, ano, mes)
            top_cidades = self._top_cidades(cur, cnpj, ano, mes)
            top_produtos = self._top_produtos(cur, cnpj, ano, mes)

            resultados.append(
              NFeKPIConsulta(
                  periodo_ano=ano,
                  periodo_mes=mes,
                  emitente_cnpj=cnpj_emitente,
                  kpis=NFeKPI(
                    id=kpi_id,
                    processamento_id=processamento_id,
                    emitente_cnpj=cnpj_emitente,
                    total_vendas=total_vendas or Decimal("0.00"),
                    quantidade_notas=total_docs or 0,
                    ticket_medio=ticket_medio or Decimal("0.00"),
                    maior_nota=maior_nota or Decimal("0.00"),
                    menor_nota=menor_nota or Decimal("0.00"),
                    total_icms=total_icms or Decimal("0.00"),
                    total_ipi=total_ipi or Decimal("0.00"),
                    total_pis=Decimal("0.00"),
                    total_cofins=Decimal("0.00"),
                    top_clientes=top_clientes,
                    top_produtos=top_produtos,
                    top_cidades=top_cidades,
                  ),
                )
              )

          return resultados

  def _top_clientes(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    return self._safe_top_query(
      cur,
      """
      SELECT COALESCE(p.nome, 'Cliente não identificado') AS cliente,
      SUM(d.valor_total) AS valor_total
      FROM public.sped_documentos_fiscais d
      LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
      WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
        AND d.tipo_operacao = 'saida'
        AND EXTRACT(YEAR FROM d.data_emissao) = %s
        AND EXTRACT(MONTH FROM d.data_emissao) = %s
      GROUP BY 1
      ORDER BY 2 DESC;
      """,
      (cnpj, ano, mes),
      "cliente",
    )

  def _top_cidades(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    sql_cidades_sped = """
      SELECT CONCAT(
        COALESCE(
          NULLIF(TRIM(p.municipio_nome), ''),
          NULLIF(TRIM(p.municipio), ''),
          'Cidade não identificada'
        ),
        CASE
          WHEN NULLIF(TRIM(p.uf), '') IS NOT NULL THEN CONCAT(' - ', UPPER(TRIM(p.uf)))
          ELSE ''
        END
      ) AS cidade,
      SUM(d.valor_total) AS valor_total
      FROM public.sped_documentos_fiscais d
      LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
      WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
        AND d.tipo_operacao = 'saida'
        AND EXTRACT(YEAR FROM d.data_emissao) = %s
        AND EXTRACT(MONTH FROM d.data_emissao) = %s
      GROUP BY 1
      ORDER BY 2 DESC;
    """

    cidades = self._safe_top_query(cur, sql_cidades_sped, (cnpj, ano, mes), "cidade")
    
    cidades_agrupadas: dict[str, Decimal] = {}
    for item in cidades:
      if not isinstance(item, dict):
        continue

      cidade = _normalizar_nome_cidade(item.get("cidade"))
      valor_total = item.get("valor_total") or Decimal("0.00")
      cidades_agrupadas[cidade] = cidades_agrupadas.get(cidade, Decimal("0.00")) + Decimal(valor_total)

    return [
      {"cidade": cidade, "valor_total": valor_total}
      for cidade, valor_total in sorted(
        cidades_agrupadas.items(),
        key=lambda x: x[1],
        reverse=True,
      )
    ]

  def _top_produtos(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    return self._safe_top_query(
      cur,
      """
      SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
      SUM(i.valor_total) AS valor_total
      FROM public.sped_documentos_fiscais d
      JOIN public.sped_documento_itens i ON i.documento_id = d.id
      LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
      WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
        AND EXTRACT(YEAR FROM d.data_emissao) = %s
        AND EXTRACT(MONTH FROM d.data_emissao) = %s
      GROUP BY 1
      ORDER BY 2 DESC
      LIMIT 5;
      """,
      (cnpj, ano, mes),
      "produto",
    )

  def _safe_top_query(self, cur, sql: str, params: tuple[object, ...], label: str) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [{label: nome, "valor_total": valor or Decimal("0.00")} for nome, valor in cur.fetchall()]
    except psycopg.errors.UndefinedTable:
      return []
    
  def listar_clientes(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
    offset: int = 0,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(d.empresa_cnpj, \'\\D\', \'\', \'g\') = %s", "d.tipo_operacao = 'saida'"]
    params: list[object] = [cnpj]

    if periodo_ano:
      filtros.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
      params.append(periodo_ano)
    if periodo_mes:
      filtros.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
      params.append(periodo_mes)

    where_clause = " AND ".join(filtros)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        total_vendas = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(SUM(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        ticket_medio = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(AVG(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        sql_clientes = f"""
          SELECT
            COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente não identificado') AS cliente,
            COALESCE(SUM(d.valor_total), 0) AS valor_total
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
        """
        query_params: list[object] = [*params]
        if limite is not None:
          sql_clientes += "\n LIMIT %s OFFSET %s"
          query_params.extend([limite, offset])

        cur.execute(sql_clientes, tuple(query_params))

        clientes_rows = cur.fetchall()

        total_clientes = self._safe_scalar_query(
          cur,
          f"""
          SELECT COUNT(*)
          FROM (
            SELECT 1
            FROM public.sped_documentos_fiscais d
            LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
            WHERE {where_clause}
            GROUP BY COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente não identificado')
          ) clientes
          """,
          tuple(params),
        )

    total_vendas_decimal = Decimal(total_vendas or 0)
    resultados = []
    for cliente, valor_total in clientes_rows:
      valor_total_decimal = Decimal(valor_total or 0)
      percentual = Decimal("0.00")
      if total_vendas_decimal > 0:
        percentual = (valor_total_decimal / total_vendas_decimal) * Decimal("100")

      resultados.append({
        "cliente": cliente,
        "valor_total": valor_total_decimal,
        "percentual": percentual,
      })

    return {
      "emitente_cnpj": cnpj,
      "periodo_ano": periodo_ano,
      "periodo_mes": periodo_mes,
      "total_clientes": int(total_clientes or 0),
      "total_vendas": total_vendas_decimal,
      "ticket_medio": Decimal(ticket_medio or 0),
      "resultados": resultados,
    }
    
  def analisar_compras(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: int = 5,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s", "d.tipo_operacao = 'entrada'"]
    params: list[object] = [cnpj]

    if periodo_ano:
      filtros.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
      params.append(periodo_ano)
    if periodo_mes:
      filtros.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
      params.append(periodo_mes)

    where_clause = " AND ".join(filtros)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        total_comprado = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(SUM(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        top_fornecedores_valor = self._safe_top_fornecedor_query(
          cur,
          f"""
          SELECT COALESCE(p.nome, 'Fornecedor não identificado') AS fornecedor,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_fornecedores_quantidade = self._safe_top_fornecedor_query(
          cur,
          f"""
          SELECT COALESCE(p.nome, 'Fornecedor não identificado') AS fornecedor,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_produtos_valor = self._safe_top_produto_query(
          cur,
          f"""
          SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
                COALESCE(SUM(i.valor_total), 0) AS valor_total,
                COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_produtos_quantidade = self._safe_top_produto_query(
          cur,
          f"""
          SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
                COALESCE(SUM(i.valor_total), 0) AS valor_total,
                COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        return {
          "emitente_cnpj": cnpj,
          "periodo_ano": periodo_ano,
          "periodo_mes": periodo_mes,
          "total_comprado": total_comprado,
          "top_fornecedores_valor": top_fornecedores_valor,
          "top_fornecedores_quantidade": top_fornecedores_quantidade,
          "top_produtos_valor": top_produtos_valor,
          "top_produtos_quantidade": top_produtos_quantidade,
        }
        
  def analisar_vendas(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s", "d.tipo_operacao = 'saida'"]
    params: list[object] = [cnpj]

    if periodo_ano:
      filtros.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
      params.append(periodo_ano)
    if periodo_mes:
      filtros.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
      params.append(periodo_mes)

    where_clause = " AND ".join(filtros)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        total_vendido = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(SUM(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        top_clientes_valor = self._safe_top_cliente_query(
          cur,
          f"""
          SELECT COALESCE(p.nome, 'Cliente não identificado') AS cliente,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_clientes_quantidade = self._safe_top_cliente_query(
          cur,
          f"""
          SELECT COALESCE(p.nome, 'Cliente não identificado') AS cliente,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC, 1 ASC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_produtos_valor = self._safe_top_produto_query(
          cur,
          f"""
          SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
                COALESCE(SUM(i.valor_total), 0) AS valor_total,
                COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        top_produtos_quantidade = self._safe_top_produto_query(
          cur,
          f"""
          SELECT COALESCE(pr.descricao, 'Produto não identificado') AS produto,
                COALESCE(SUM(i.valor_total), 0) AS valor_total,
                COALESCE(SUM(i.quantidade), 0) AS quantidade_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.sped_produtos pr ON pr.id = i.produto_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 3 DESC, 2 DESC, 1 ASC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )

        cur.execute(
          f"""
          SELECT COALESCE(NULLIF(TRIM(i.cfop), ''), '0000') AS cfop,
                COALESCE(NULLIF(TRIM(cf.descricao), ''), 'CFOP sem descrição') AS descricao,
                COALESCE(SUM(i.valor_total), 0) AS valor_total
          FROM public.sped_documentos_fiscais d
          JOIN public.sped_documento_itens i ON i.documento_id = d.id
          LEFT JOIN public.notas_cfops cf
            ON regexp_replace(COALESCE(cf.codigo, ''), '\\D', '', 'g')
               = regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g')
          WHERE {where_clause}
          GROUP BY 1, 2
          ORDER BY 3 DESC, 1 ASC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )
        top_cfops_valor = [
          {
            "cfop": cfop,
            "descricao": descricao,
            "valor_total": valor_total or Decimal("0.00"),
            "participacao_percentual": (
              ((valor_total or Decimal("0.00")) / total_vendido) * Decimal("100")
              if total_vendido
              else Decimal("0.00")
            ),
          }
          for cfop, descricao, valor_total in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT CONCAT(
                  COALESCE(
                    NULLIF(TRIM(p.municipio_nome), ''),
                    NULLIF(TRIM(p.municipio), ''),
                    'Cidade não identificada'
                  ),
                  CASE
                    WHEN NULLIF(TRIM(p.uf), '') IS NOT NULL THEN CONCAT(' - ', UPPER(TRIM(p.uf)))
                    ELSE ''
                  END
                ) AS cidade,
                COALESCE(NULLIF(TRIM(p.uf), ''), '') AS uf,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1, 2
          ORDER BY 3 DESC, 1 ASC
          LIMIT %s
          """,
          tuple([*params, limite]),
        )
        top_cidades_valor = [
          {
            "cidade": _normalizar_nome_cidade(cidade),
            "uf": uf,
            "valor_total": valor_total or Decimal("0.00"),
            "quantidade_documentos": quantidade_documentos or 0,
          }
          for cidade, uf, valor_total, quantidade_documentos in cur.fetchall()
        ]

        cur.execute(
          f"""
          SELECT COALESCE(NULLIF(TRIM(p.uf), ''), '') AS uf,
                COALESCE(SUM(d.valor_total), 0) AS valor_total,
                COUNT(*) AS quantidade_documentos
          FROM public.sped_documentos_fiscais d
          LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
          WHERE {where_clause}
          GROUP BY 1
          ORDER BY 2 DESC, 1 ASC
          """,
          tuple(params),
        )
        top_regioes_map: dict[str, dict[str, Decimal | int | str]] = {}
        for uf, valor_total, quantidade_documentos in cur.fetchall():
          regiao = _obter_regiao_por_uf(uf)
          if not regiao:
            continue

          acumulado = top_regioes_map.setdefault(
            regiao,
            {
              "regiao": regiao,
              "valor_total": Decimal("0.00"),
              "quantidade_documentos": 0,
            },
          )
          acumulado["valor_total"] = Decimal(str(acumulado["valor_total"])) + (valor_total or Decimal("0.00"))
          acumulado["quantidade_documentos"] = int(acumulado["quantidade_documentos"]) + (quantidade_documentos or 0)

        top_regioes_valor = sorted(
          top_regioes_map.values(),
          key=lambda item: Decimal(str(item["valor_total"])),
          reverse=True,
        )[:limite]

        return {
          "emitente_cnpj": cnpj,
          "periodo_ano": periodo_ano,
          "periodo_mes": periodo_mes,
          "total_vendido": total_vendido,
          "top_clientes_valor": top_clientes_valor,
          "top_clientes_quantidade": top_clientes_quantidade,
          "top_produtos_valor": top_produtos_valor,
          "top_produtos_quantidade": top_produtos_quantidade,
          "top_cfops_valor": top_cfops_valor,
          "top_regioes_valor": top_regioes_valor,
          "top_cidades_valor": top_cidades_valor,
        }

  def analisar_clientes(
    self,
    emitente_cnpj: str,
    periodo_ano: Optional[int] = None,
    periodo_mes: Optional[int] = None,
    limite: Optional[int] = None,
  ) -> dict:
    cnpj = normalizar_cnpj(emitente_cnpj)
    filtros = ["regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s", "d.tipo_operacao = 'saida'"]
    params: list[object] = [cnpj]

    if periodo_ano:
      filtros.append("EXTRACT(YEAR FROM d.data_emissao) = %s")
      params.append(periodo_ano)
    if periodo_mes:
      filtros.append("EXTRACT(MONTH FROM d.data_emissao) = %s")
      params.append(periodo_mes)

    where_clause = " AND ".join(filtros)

    with psycopg.connect(**self.conn_params) as conn:
      with conn.cursor() as cur:
        total_vendido = self._safe_scalar_query(
          cur,
          f"""
          SELECT COALESCE(SUM(d.valor_total), 0)
          FROM public.sped_documentos_fiscais d
          WHERE {where_clause}
          """,
          tuple(params),
        )

        total_clientes = self._safe_scalar_query(
          cur,
          f"""
          SELECT COUNT(*)
          FROM (
            SELECT 1
            FROM public.sped_documentos_fiscais d
            LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
            WHERE {where_clause}
            GROUP BY COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente nÃ£o identificado')
          ) clientes
          """,
          tuple(params),
        )

        top_clientes_valor = self._safe_top_cliente_analise_query(
          cur,
          f"""
          SELECT
            cliente,
            valor_total,
            quantidade_documentos,
            ticket_medio,
            CASE
              WHEN %s = 0 THEN 0
              ELSE ROUND((valor_total * 100.0) / %s, 2)
            END AS percentual_participacao
          FROM (
            SELECT
              COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente nÃ£o identificado') AS cliente,
              COALESCE(SUM(d.valor_total), 0) AS valor_total,
              COUNT(*) AS quantidade_documentos,
              CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE COALESCE(SUM(d.valor_total), 0) / COUNT(*)
              END AS ticket_medio
            FROM public.sped_documentos_fiscais d
            LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
            WHERE {where_clause}
            GROUP BY 1
          ) base
          ORDER BY valor_total DESC, cliente ASC
          LIMIT %s
          """,
          tuple([total_vendido or Decimal("0.00"), total_vendido or Decimal("0.00"), *params, limite]),
        )

        top_clientes_quantidade = self._safe_top_cliente_analise_query(
          cur,
          f"""
          SELECT
            cliente,
            valor_total,
            quantidade_documentos,
            ticket_medio,
            CASE
              WHEN %s = 0 THEN 0
              ELSE ROUND((valor_total * 100.0) / %s, 2)
            END AS percentual_participacao
          FROM (
            SELECT
              COALESCE(NULLIF(TRIM(p.nome), ''), 'Cliente nÃ£o identificado') AS cliente,
              COALESCE(SUM(d.valor_total), 0) AS valor_total,
              COUNT(*) AS quantidade_documentos,
              CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE COALESCE(SUM(d.valor_total), 0) / COUNT(*)
              END AS ticket_medio
            FROM public.sped_documentos_fiscais d
            LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
            WHERE {where_clause}
            GROUP BY 1
          ) base
          ORDER BY quantidade_documentos DESC, valor_total DESC, cliente ASC
          LIMIT %s
          """,
          tuple([total_vendido or Decimal("0.00"), total_vendido or Decimal("0.00"), *params, limite]),
        )

        return {
          "emitente_cnpj": cnpj,
          "periodo_ano": periodo_ano,
          "periodo_mes": periodo_mes,
          "total_vendido": total_vendido or Decimal("0.00"),
          "total_clientes": int(total_clientes or 0),
          "top_clientes_valor": top_clientes_valor,
          "top_clientes_quantidade": top_clientes_quantidade,
        }

  def _safe_scalar_query(self, cur, sql: str, params: tuple[object, ...]) -> Decimal:
    try:
      cur.execute(sql, params)
      row = cur.fetchone()
      return row[0] if row else Decimal("0.00")
    except psycopg.errors.UndefinedTable:
      return Decimal("0.00")

  def _safe_top_fornecedor_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [
        {
          "fornecedor": fornecedor,
          "valor_total": valor_total or Decimal("0.00"),
          "quantidade_documentos": quantidade_documentos or 0,
        }
        for fornecedor, valor_total, quantidade_documentos in cur.fetchall()
      ]
    except psycopg.errors.UndefinedTable:
      return []
    
  def _safe_top_cliente_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [
        {
          "cliente": cliente,
          "valor_total": valor_total or Decimal("0.00"),
          "quantidade_documentos": quantidade_documentos or 0,
        }
        for cliente, valor_total, quantidade_documentos in cur.fetchall()
      ]
    except psycopg.errors.UndefinedTable:
      return []

  def _safe_top_produto_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [
        {
          "produto": produto,
          "valor_total": valor_total or Decimal("0.00"),
          "quantidade_total": quantidade_total or Decimal("0.00"),
        }
        for produto, valor_total, quantidade_total in cur.fetchall()
      ]
    except psycopg.errors.UndefinedTable:
      return []

  def _safe_top_cliente_analise_query(self, cur, sql: str, params: tuple[object, ...]) -> list[dict]:
    try:
      cur.execute(sql, params)
      return [
        {
          "cliente": cliente,
          "valor_total": valor_total or Decimal("0.00"),
          "quantidade_documentos": quantidade_documentos or 0,
          "ticket_medio": ticket_medio or Decimal("0.00"),
          "percentual_participacao": percentual_participacao or Decimal("0.00"),
        }
        for cliente, valor_total, quantidade_documentos, ticket_medio, percentual_participacao in cur.fetchall()
      ]
    except psycopg.errors.UndefinedTable:
      return []
