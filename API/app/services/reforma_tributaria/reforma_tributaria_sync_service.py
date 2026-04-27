import psycopg

from app.services.nfe.empresa_service import normalizar_cnpj

class ReformaTributariaSyncService:
  TRIBUTOS_LEGADOS_NFE = ("ICMS", "IPI", "PIS", "COFINS")

  def sincronizar_nfe_periodo(
    self,
    conn: psycopg.Connection,
    emitente_cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    cnpj = normalizar_cnpj(emitente_cnpj)
    if not cnpj:
      return

    with conn.cursor() as cur:
      self._remover_tributos_nfe_periodo(cur, cnpj, periodo_ano, periodo_mes)
      self._remover_creditos_debitos_nfe_periodo(cur, cnpj, periodo_ano, periodo_mes)
      self._inserir_documentos_tributos_nfe(cur, cnpj, periodo_ano, periodo_mes)
      self._inserir_itens_tributos_nfe(cur, cnpj, periodo_ano, periodo_mes)
      self._inserir_creditos_debitos_nfe(cur, cnpj, periodo_ano, periodo_mes)
      self._atualizar_apuracao_nfe(cur, cnpj, periodo_ano, periodo_mes)

  def sincronizar_sped_apuracao_icms(
    self,
    conn: psycopg.Connection,
    emitente_cnpj: str,
  ) -> None:
    cnpj = normalizar_cnpj(emitente_cnpj)
    if not cnpj:
      return

    with conn.cursor() as cur:
      cur.execute(
        """
        INSERT INTO public.apuracao_tributaria (
          empresa_cnpj,
          periodo_ano,
          periodo_mes,
          tributo_id,
          total_debitos,
          total_creditos,
          ajustes_debito,
          ajustes_credito,
          saldo_apurado,
          saldo_a_recolher,
          status
        )
        SELECT
          a.empresa_cnpj,
          a.periodo_ano,
          a.periodo_mes,
          t.id AS tributo_id,
          COALESCE(a.total_debitos, 0),
          COALESCE(a.total_creditos, 0),
          COALESCE(a.ajustes_debitos, 0),
          COALESCE(a.ajustes_creditos, 0),
          COALESCE(a.saldo_apurado, 0),
          COALESCE(a.valor_icms_recolher, 0),
          'aberta'
        FROM public.sped_apuracao_icms a
        JOIN public.tributos t ON t.codigo = 'ICMS'
        WHERE regexp_replace(a.empresa_cnpj, '\\D', '', 'g') = %s
        ON CONFLICT (empresa_cnpj, periodo_ano, periodo_mes, tributo_id)
        DO UPDATE SET
          total_debitos = EXCLUDED.total_debitos,
          total_creditos = EXCLUDED.total_creditos,
          ajustes_debito = EXCLUDED.ajustes_debito,
          ajustes_credito = EXCLUDED.ajustes_credito,
          saldo_apurado = EXCLUDED.saldo_apurado,
          saldo_a_recolher = EXCLUDED.saldo_a_recolher,
          atualizado_em = CURRENT_TIMESTAMP;
        """,
        (cnpj,),
      )

  def _remover_tributos_nfe_periodo(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    cur.execute(
      """
      DELETE FROM public.documentos_fiscais_tributos dt
      USING public.notas n, public.tributos t
      WHERE dt.nota_id = n.id
        AND dt.tributo_id = t.id
        AND t.codigo = ANY(%s)
        AND regexp_replace(n.emitente_cnpj, '\\D', '', 'g') = %s
        AND EXTRACT(YEAR FROM n.data_emissao) = %s
        AND EXTRACT(MONTH FROM n.data_emissao) = %s;
      """,
      (list(self.TRIBUTOS_LEGADOS_NFE), cnpj, periodo_ano, periodo_mes),
    )

  def _remover_creditos_debitos_nfe_periodo(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    params = (cnpj, periodo_ano, periodo_mes, list(self.TRIBUTOS_LEGADOS_NFE))
    cur.execute(
      """
      DELETE FROM public.creditos_tributarios c
      USING public.tributos t
      WHERE c.tributo_id = t.id
        AND regexp_replace(c.empresa_cnpj, '\\D', '', 'g') = %s
        AND c.periodo_ano = %s
        AND c.periodo_mes = %s
        AND t.codigo = ANY(%s)
        AND c.origem_credito = 'entrada';
      """,
      params,
    )
    cur.execute(
      """
      DELETE FROM public.debitos_tributarios d
      USING public.tributos t
      WHERE d.tributo_id = t.id
        AND regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
        AND d.periodo_ano = %s
        AND d.periodo_mes = %s
        AND t.codigo = ANY(%s)
        AND d.origem_debito = 'saida';
      """,
      params,
    )

  def _inserir_documentos_tributos_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    cur.execute(
      """
      WITH notas_periodo AS (
        SELECT *
        FROM public.notas n
        WHERE regexp_replace(n.emitente_cnpj, '\\D', '', 'g') = %s
          AND EXTRACT(YEAR FROM n.data_emissao) = %s
          AND EXTRACT(MONTH FROM n.data_emissao) = %s
      ),
      valores AS (
        SELECT
          n.id AS nota_id,
          n.emitente_cnpj AS empresa_cnpj,
          EXTRACT(YEAR FROM n.data_emissao)::int AS periodo_ano,
          EXTRACT(MONTH FROM n.data_emissao)::int AS periodo_mes,
          n.modelo AS modelo_documento,
          n.numero_nf::varchar AS chave_acesso,
          CASE
            WHEN EXISTS (
              SELECT 1
              FROM public.notas_itens i
              WHERE i.nota_id = n.id
                AND LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')
            ) THEN 'saida'
            WHEN EXISTS (
              SELECT 1
              FROM public.notas_itens i
              WHERE i.nota_id = n.id
                AND LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('1','2','3')
            ) THEN 'entrada'
            ELSE NULL
          END AS tipo_operacao,
          n.data_emissao,
          v.codigo_tributo,
          v.valor_tributo
        FROM notas_periodo n
        CROSS JOIN LATERAL (
          VALUES
            ('ICMS', COALESCE(n.valor_icms, 0)),
            ('IPI', COALESCE(n.valor_ipi, 0)),
            ('PIS', COALESCE(n.valor_pis, 0)),
            ('COFINS', COALESCE(n.valor_cofins, 0))
        ) AS v(codigo_tributo, valor_tributo)
        WHERE COALESCE(v.valor_tributo, 0) <> 0
      )
      INSERT INTO public.documentos_fiscais_tributos (
        nota_id,
        tributo_id,
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        modelo_documento,
        chave_acesso,
        tipo_operacao,
        data_emissao,
        base_calculo,
        valor_debito,
        valor_credito,
        valor_tributo,
        natureza,
        origem,
        status
      )
      SELECT
        v.nota_id,
        t.id,
        v.empresa_cnpj,
        v.periodo_ano,
        v.periodo_mes,
        v.modelo_documento,
        v.chave_acesso,
        v.tipo_operacao,
        v.data_emissao,
        0,
        CASE WHEN v.tipo_operacao = 'entrada' THEN 0 ELSE v.valor_tributo END,
        CASE WHEN v.tipo_operacao = 'entrada' THEN v.valor_tributo ELSE 0 END,
        v.valor_tributo,
        CASE WHEN v.tipo_operacao = 'entrada' THEN 'credito' ELSE 'debito' END,
        'xml',
        'ativo'
      FROM valores v
      JOIN public.tributos t ON t.codigo = v.codigo_tributo;
      """,
      (cnpj, periodo_ano, periodo_mes),
    )

  def _inserir_itens_tributos_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    cur.execute(
      """
      WITH itens_base AS (
        SELECT
          i.*,
          n.emitente_cnpj AS empresa_cnpj,
          n.data_emissao,
          EXTRACT(YEAR FROM n.data_emissao)::int AS periodo_ano,
          EXTRACT(MONTH FROM n.data_emissao)::int AS periodo_mes,
          SUM(COALESCE(i.valor_total, 0)) OVER (PARTITION BY i.nota_id) AS total_itens_nota
        FROM public.notas_itens i
        JOIN public.notas n ON n.id = i.nota_id
        WHERE regexp_replace(n.emitente_cnpj, '\\D', '', 'g') = %s
          AND EXTRACT(YEAR FROM n.data_emissao) = %s
          AND EXTRACT(MONTH FROM n.data_emissao) = %s
      )
      INSERT INTO public.itens_documentos_fiscais_tributos (
        documento_tributo_id,
        nota_item_id,
        tributo_id,
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        numero_item,
        produto_codigo,
        ncm_codigo,
        cfop,
        cst_codigo,
        base_calculo,
        aliquota,
        valor_debito,
        valor_credito,
        valor_tributo,
        natureza,
        origem,
        status
      )
      SELECT
        dt.id,
        i.id,
        dt.tributo_id,
        i.empresa_cnpj,
        i.periodo_ano,
        i.periodo_mes,
        i.item_numero,
        i.produto_codigo,
        CASE
          WHEN EXISTS (
            SELECT 1
            FROM public.ncm_catalogo nc
            WHERE nc.codigo = LEFT(regexp_replace(COALESCE(i.ncm, ''), '\\D', '', 'g'), 8)::char(8)
          )
            THEN LEFT(regexp_replace(COALESCE(i.ncm, ''), '\\D', '', 'g'), 8)::char(8)
          ELSE NULL
        END,
        i.cfop,
        CASE WHEN t.codigo = 'ICMS' THEN i.icms_cst_csosn ELSE NULL END,
        CASE WHEN t.codigo = 'ICMS' THEN COALESCE(i.icms_base, 0) ELSE 0 END,
        CASE WHEN t.codigo = 'ICMS' THEN i.icms_aliquota ELSE NULL END,
        CASE WHEN dt.natureza = 'credito' THEN 0 ELSE
          CASE
            WHEN t.codigo = 'ICMS' AND COALESCE(i.icms_valor, 0) <> 0 THEN COALESCE(i.icms_valor, 0)
            WHEN COALESCE(i.total_itens_nota, 0) > 0 THEN ROUND((COALESCE(i.valor_total, 0) / i.total_itens_nota) * dt.valor_tributo, 2)
            ELSE 0
          END
        END,
        CASE WHEN dt.natureza = 'credito' THEN
          CASE
            WHEN t.codigo = 'ICMS' AND COALESCE(i.icms_valor, 0) <> 0 THEN COALESCE(i.icms_valor, 0)
            WHEN COALESCE(i.total_itens_nota, 0) > 0 THEN ROUND((COALESCE(i.valor_total, 0) / i.total_itens_nota) * dt.valor_tributo, 2)
            ELSE 0
          END
        ELSE 0 END,
        CASE
          WHEN t.codigo = 'ICMS' AND COALESCE(i.icms_valor, 0) <> 0 THEN COALESCE(i.icms_valor, 0)
          WHEN COALESCE(i.total_itens_nota, 0) > 0 THEN ROUND((COALESCE(i.valor_total, 0) / i.total_itens_nota) * dt.valor_tributo, 2)
          ELSE 0
        END,
        dt.natureza,
        'xml',
        'ativo'
      FROM itens_base i
      JOIN public.documentos_fiscais_tributos dt ON dt.nota_id = i.nota_id
      JOIN public.tributos t ON t.id = dt.tributo_id
      WHERE t.codigo = ANY(%s);
      """,
      (cnpj, periodo_ano, periodo_mes, list(self.TRIBUTOS_LEGADOS_NFE)),
    )

  def _inserir_creditos_debitos_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    cur.execute(
      """
      INSERT INTO public.creditos_tributarios (
        documento_tributo_id,
        item_tributo_id,
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        tributo_id,
        origem_credito,
        tipo_credito,
        valor_original,
        valor_saldo,
        data_origem,
        status
      )
      SELECT
        it.documento_tributo_id,
        it.id,
        it.empresa_cnpj,
        it.periodo_ano,
        it.periodo_mes,
        it.tributo_id,
        'entrada',
        'basico',
        COALESCE(NULLIF(it.valor_credito, 0), it.valor_tributo, 0),
        COALESCE(NULLIF(it.valor_credito, 0), it.valor_tributo, 0),
        dt.data_emissao,
        'disponivel'
      FROM public.itens_documentos_fiscais_tributos it
      JOIN public.documentos_fiscais_tributos dt ON dt.id = it.documento_tributo_id
      JOIN public.tributos t ON t.id = it.tributo_id
      WHERE regexp_replace(it.empresa_cnpj, '\\D', '', 'g') = %s
        AND it.periodo_ano = %s
        AND it.periodo_mes = %s
        AND it.natureza = 'credito'
        AND t.codigo = ANY(%s)
        AND COALESCE(NULLIF(it.valor_credito, 0), it.valor_tributo, 0) > 0;
      """,
      (cnpj, periodo_ano, periodo_mes, list(self.TRIBUTOS_LEGADOS_NFE)),
    )
    cur.execute(
      """
      INSERT INTO public.debitos_tributarios (
        documento_tributo_id,
        item_tributo_id,
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        tributo_id,
        origem_debito,
        tipo_debito,
        valor_original,
        valor_devido,
        data_fato_gerador,
        status
      )
      SELECT
        it.documento_tributo_id,
        it.id,
        it.empresa_cnpj,
        it.periodo_ano,
        it.periodo_mes,
        it.tributo_id,
        'saida',
        'operacao',
        COALESCE(NULLIF(it.valor_debito, 0), it.valor_tributo, 0),
        COALESCE(NULLIF(it.valor_debito, 0), it.valor_tributo, 0),
        dt.data_emissao,
        'aberto'
      FROM public.itens_documentos_fiscais_tributos it
      JOIN public.documentos_fiscais_tributos dt ON dt.id = it.documento_tributo_id
      JOIN public.tributos t ON t.id = it.tributo_id
      WHERE regexp_replace(it.empresa_cnpj, '\\D', '', 'g') = %s
        AND it.periodo_ano = %s
        AND it.periodo_mes = %s
        AND it.natureza = 'debito'
        AND t.codigo = ANY(%s)
        AND COALESCE(NULLIF(it.valor_debito, 0), it.valor_tributo, 0) > 0;
      """,
      (cnpj, periodo_ano, periodo_mes, list(self.TRIBUTOS_LEGADOS_NFE)),
    )

  def _atualizar_apuracao_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    cur.execute(
      """
      WITH tributos_periodo AS (
        SELECT DISTINCT tributo_id
        FROM public.debitos_tributarios
        WHERE regexp_replace(empresa_cnpj, '\\D', '', 'g') = %s
          AND periodo_ano = %s
          AND periodo_mes = %s
        UNION
        SELECT DISTINCT tributo_id
        FROM public.creditos_tributarios
        WHERE regexp_replace(empresa_cnpj, '\\D', '', 'g') = %s
          AND periodo_ano = %s
          AND periodo_mes = %s
      ),
      totais AS (
        SELECT
          tp.tributo_id,
          COALESCE((
            SELECT SUM(valor_devido)
            FROM public.debitos_tributarios d
            WHERE d.tributo_id = tp.tributo_id
              AND regexp_replace(d.empresa_cnpj, '\\D', '', 'g') = %s
              AND d.periodo_ano = %s
              AND d.periodo_mes = %s
          ), 0) AS total_debitos,
          COALESCE((
            SELECT SUM(valor_saldo)
            FROM public.creditos_tributarios c
            WHERE c.tributo_id = tp.tributo_id
              AND regexp_replace(c.empresa_cnpj, '\\D', '', 'g') = %s
              AND c.periodo_ano = %s
              AND c.periodo_mes = %s
          ), 0) AS total_creditos
        FROM tributos_periodo tp
      )
      INSERT INTO public.apuracao_tributaria (
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        tributo_id,
        total_debitos,
        total_creditos,
        saldo_apurado,
        saldo_a_recolher,
        status
      )
      SELECT
        %s,
        %s,
        %s,
        tributo_id,
        total_debitos,
        total_creditos,
        total_debitos - total_creditos,
        GREATEST(total_debitos - total_creditos, 0),
        'aberta'
      FROM totais
      ON CONFLICT (empresa_cnpj, periodo_ano, periodo_mes, tributo_id)
      DO UPDATE SET
        total_debitos = EXCLUDED.total_debitos,
        total_creditos = EXCLUDED.total_creditos,
        saldo_apurado = EXCLUDED.saldo_apurado,
        saldo_a_recolher = EXCLUDED.saldo_a_recolher,
        atualizado_em = CURRENT_TIMESTAMP;
      """,
      (
        cnpj,
        periodo_ano,
        periodo_mes,
        cnpj,
        periodo_ano,
        periodo_mes,
        cnpj,
        periodo_ano,
        periodo_mes,
        cnpj,
        periodo_ano,
        periodo_mes,
        cnpj,
        periodo_ano,
        periodo_mes,
      ),
    )
