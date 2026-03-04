from decimal import Decimal
from typing import Optional

import psycopg

from app.models.nfe.schemas import NFeKPI, NFeKPIConsulta
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.sped.postgres_config import carregar_config_postgres_sped


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
      FROM public.sped_kpis_sped_fiscal
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
        AND EXTRACT(YEAR FROM d.data_emissao) = %s
        AND EXTRACT(MONTH FROM d.data_emissao) = %s
      GROUP BY 1
      ORDER BY 2 DESC
      LIMIT 5;
      """,
      (cnpj, ano, mes),
      "cliente",
    )

  def _top_cidades(self, cur, cnpj: str, ano: int, mes: int) -> list[dict]:
    return self._safe_top_query(
      cur,
      """
      SELECT COALESCE(p.municipio, 'Cidade não identificada') AS cidade,
      SUM(d.valor_total) AS valor_total
      FROM public.sped_documentos_fiscais d
      LEFT JOIN public.sped_participantes p ON p.id = d.participante_id
      WHERE regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
        AND EXTRACT(YEAR FROM d.data_emissao) = %s
        AND EXTRACT(MONTH FROM d.data_emissao) = %s
      GROUP BY 1
      ORDER BY 2 DESC
      LIMIT 5;
      """,
      (cnpj, ano, mes),
      "cidade",
    )

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