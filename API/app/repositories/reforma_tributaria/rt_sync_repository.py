from __future__ import annotations

import psycopg


class ReformaTributariaSyncRepository:
  TRIBUTOS_LEGADOS_NFE = ("ICMS", "IPI", "PIS", "COFINS")
  TRIBUTOS_LEGADOS_SPED = ("ICMS",)
  TRIBUTOS_REFORMA = ("CBS", "IBS", "IBS_UF", "IBS_MUN", "IS")

  def listar_periodos_nfe(self, cur, cnpj: str) -> list[tuple[int, int, int]]:
    cur.execute(
      """
      SELECT
        EXTRACT(YEAR FROM n.data_emissao)::int AS periodo_ano,
        EXTRACT(MONTH FROM n.data_emissao)::int AS periodo_mes,
        COUNT(DISTINCT n.id) AS documentos
      FROM public.notas n
      WHERE regexp_replace(UPPER(n.emitente_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND n.data_emissao IS NOT NULL
      GROUP BY 1, 2
      ORDER BY 1, 2;
      """,
      (cnpj,),
    )
    return cur.fetchall()

  def listar_periodos_sped(self, cur, cnpj: str) -> list[tuple[int, int, int]]:
    cur.execute(
      """
      SELECT
        EXTRACT(YEAR FROM d.data_emissao)::int AS periodo_ano,
        EXTRACT(MONTH FROM d.data_emissao)::int AS periodo_mes,
        COUNT(DISTINCT d.id) AS documentos
      FROM public.sped_documentos_fiscais d
      WHERE regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND d.data_emissao IS NOT NULL
      GROUP BY 1, 2
      ORDER BY 1, 2;
      """,
      (cnpj,),
    )
    return cur.fetchall()

  def sincronizar_sped_apuracao_icms(self, cur, cnpj: str) -> None:
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
      WHERE regexp_replace(UPPER(a.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
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

  def garantir_tributos_base(self, cur) -> list[str]:
    cur.execute(
      """
      INSERT INTO public.tributos (codigo, nome, esfera, tipo, descricao, ativo)
      VALUES
        ('ICMS', 'Imposto sobre Circulacao de Mercadorias e Servicos', 'estadual', 'atual', 'Tributo estadual vigente antes da Reforma Tributaria do Consumo.', TRUE),
        ('ICMS_ST', 'ICMS Substituicao Tributaria', 'estadual', 'atual', 'Modalidade de recolhimento por substituicao tributaria do ICMS.', TRUE),
        ('IPI', 'Imposto sobre Produtos Industrializados', 'federal', 'atual', 'Tributo federal vigente antes da Reforma Tributaria do Consumo.', TRUE),
        ('PIS', 'Programa de Integracao Social', 'federal', 'atual', 'Contribuicao federal a ser substituida/absorvida no contexto da CBS.', TRUE),
        ('COFINS', 'Contribuicao para o Financiamento da Seguridade Social', 'federal', 'atual', 'Contribuicao federal a ser substituida/absorvida no contexto da CBS.', TRUE),
        ('ISS', 'Imposto sobre Servicos', 'municipal', 'atual', 'Tributo municipal vigente antes da Reforma Tributaria do Consumo.', TRUE),
        ('CBS', 'Contribuicao sobre Bens e Servicos', 'federal', 'reforma', 'Novo tributo federal da Reforma Tributaria do Consumo.', TRUE),
        ('IBS', 'Imposto sobre Bens e Servicos', 'compartilhada', 'reforma', 'Novo tributo compartilhado entre estados, Distrito Federal e municipios.', TRUE),
        ('IBS_UF', 'IBS Parcela Estadual', 'estadual', 'reforma', 'Componente estadual do IBS.', TRUE),
        ('IBS_MUN', 'IBS Parcela Municipal', 'municipal', 'reforma', 'Componente municipal do IBS.', TRUE),
        ('IS', 'Imposto Seletivo', 'federal', 'reforma', 'Imposto Seletivo incidente sobre bens e servicos especificos.', TRUE)
      ON CONFLICT (codigo) DO UPDATE SET
        nome = EXCLUDED.nome,
        esfera = EXCLUDED.esfera,
        tipo = EXCLUDED.tipo,
        descricao = EXCLUDED.descricao,
        ativo = TRUE,
        atualizado_em = CURRENT_TIMESTAMP;
      """
    )
    cur.execute(
      """
      SELECT codigo
      FROM public.tributos
      WHERE codigo = ANY(%s)
      ORDER BY codigo;
      """,
      (list(self.TRIBUTOS_LEGADOS_NFE + self.TRIBUTOS_REFORMA),),
    )
    return [row[0] for row in cur.fetchall()]

  def remover_tributos_nfe_periodo(
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
        AND regexp_replace(UPPER(n.emitente_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND EXTRACT(YEAR FROM n.data_emissao) = %s
        AND EXTRACT(MONTH FROM n.data_emissao) = %s;
      """,
      (list(self.TRIBUTOS_LEGADOS_NFE), cnpj, periodo_ano, periodo_mes),
    )

  def remover_tributos_sped(self, cur, cnpj: str) -> None:
    cur.execute(
      """
      DELETE FROM public.memoria_calculo_tributaria m
      USING public.tributos t
      WHERE m.tributo_id = t.id
        AND regexp_replace(UPPER(m.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND m.fonte_dados = 'sped'
        AND t.codigo = ANY(%s);
      """,
      (cnpj, list(self.TRIBUTOS_LEGADOS_SPED)),
    )
    cur.execute(
      """
      DELETE FROM public.creditos_tributarios c
      USING public.documentos_fiscais_tributos dt, public.tributos t
      WHERE c.documento_tributo_id = dt.id
        AND c.tributo_id = t.id
        AND dt.sped_documento_id IS NOT NULL
        AND dt.origem = 'sped'
        AND regexp_replace(UPPER(c.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND t.codigo = ANY(%s);
      """,
      (cnpj, list(self.TRIBUTOS_LEGADOS_SPED)),
    )
    cur.execute(
      """
      DELETE FROM public.debitos_tributarios d
      USING public.documentos_fiscais_tributos dt, public.tributos t
      WHERE d.documento_tributo_id = dt.id
        AND d.tributo_id = t.id
        AND dt.sped_documento_id IS NOT NULL
        AND dt.origem = 'sped'
        AND regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND t.codigo = ANY(%s);
      """,
      (cnpj, list(self.TRIBUTOS_LEGADOS_SPED)),
    )
    cur.execute(
      """
      DELETE FROM public.documentos_fiscais_tributos dt
      USING public.tributos t
      WHERE dt.tributo_id = t.id
        AND dt.sped_documento_id IS NOT NULL
        AND dt.origem = 'sped'
        AND regexp_replace(UPPER(dt.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND t.codigo = ANY(%s);
      """,
      (cnpj, list(self.TRIBUTOS_LEGADOS_SPED)),
    )

  def inserir_documentos_tributos_sped_icms(self, cur, cnpj: str) -> None:
    cur.execute(
      """
      WITH documentos AS (
        SELECT
          d.*,
          EXTRACT(YEAR FROM d.data_emissao)::int AS periodo_ano,
          EXTRACT(MONTH FROM d.data_emissao)::int AS periodo_mes,
          SUM(COALESCE(d.valor_total, 0)) OVER (
            PARTITION BY EXTRACT(YEAR FROM d.data_emissao), EXTRACT(MONTH FROM d.data_emissao), d.tipo_operacao
          ) AS total_operacao_periodo
        FROM public.sped_documentos_fiscais d
        WHERE regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
          AND d.data_emissao IS NOT NULL
          AND d.tipo_operacao IN ('entrada', 'saida')
      ),
      valores AS (
        SELECT
          d.id AS sped_documento_id,
          d.empresa_cnpj,
          d.periodo_ano,
          d.periodo_mes,
          d.modelo::varchar AS modelo_documento,
          COALESCE(NULLIF(d.chave_acesso, ''), d.numero::varchar) AS chave_acesso,
          d.tipo_operacao,
          d.data_emissao,
          COALESCE(NULLIF(d.valor_produtos, 0), d.valor_total, 0) AS base_calculo,
          CASE
            WHEN d.tipo_operacao = 'saida' AND COALESCE(d.total_operacao_periodo, 0) > 0
              THEN ROUND((COALESCE(d.valor_total, 0) / d.total_operacao_periodo) * COALESCE(a.total_debitos, 0), 2)
            WHEN d.tipo_operacao = 'entrada' AND COALESCE(d.total_operacao_periodo, 0) > 0
              THEN ROUND((COALESCE(d.valor_total, 0) / d.total_operacao_periodo) * COALESCE(a.total_creditos, 0), 2)
            ELSE 0
          END AS valor_tributo
        FROM documentos d
        JOIN public.sped_apuracao_icms a
          ON regexp_replace(UPPER(a.empresa_cnpj), '[^0-9A-Z]', '', 'g') = regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g')
         AND a.periodo_ano = d.periodo_ano
         AND a.periodo_mes = d.periodo_mes
      )
      INSERT INTO public.documentos_fiscais_tributos (
        sped_documento_id,
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
        status,
        observacoes
      )
      SELECT
        v.sped_documento_id,
        t.id,
        v.empresa_cnpj,
        v.periodo_ano,
        v.periodo_mes,
        v.modelo_documento,
        v.chave_acesso,
        v.tipo_operacao,
        v.data_emissao,
        v.base_calculo,
        CASE WHEN v.tipo_operacao = 'saida' THEN v.valor_tributo ELSE 0 END,
        CASE WHEN v.tipo_operacao = 'entrada' THEN v.valor_tributo ELSE 0 END,
        v.valor_tributo,
        CASE WHEN v.tipo_operacao = 'entrada' THEN 'credito' ELSE 'debito' END,
        'sped',
        'ativo',
        'Valor distribuido proporcionalmente a partir da apuracao ICMS do SPED.'
      FROM valores v
      JOIN public.tributos t ON t.codigo = 'ICMS'
      WHERE COALESCE(v.valor_tributo, 0) <> 0;
      """,
      (cnpj,),
    )

  def inserir_itens_tributos_sped_icms(self, cur, cnpj: str) -> None:
    cur.execute(
      """
      WITH itens AS (
        SELECT
          i.*,
          d.empresa_cnpj,
          EXTRACT(YEAR FROM d.data_emissao)::int AS periodo_ano,
          EXTRACT(MONTH FROM d.data_emissao)::int AS periodo_mes,
          p.codigo AS produto_codigo,
          p.ncm,
          SUM(COALESCE(i.valor_total, 0)) OVER (PARTITION BY i.documento_id) AS total_itens_documento
        FROM public.sped_documento_itens i
        JOIN public.sped_documentos_fiscais d ON d.id = i.documento_id
        LEFT JOIN public.sped_produtos p ON p.id = i.produto_id
        WHERE regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
      )
      INSERT INTO public.itens_documentos_fiscais_tributos (
        documento_tributo_id,
        sped_item_id,
        tributo_id,
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        numero_item,
        produto_codigo,
        ncm_codigo,
        cfop,
        base_calculo,
        valor_debito,
        valor_credito,
        valor_tributo,
        natureza,
        origem,
        status,
        observacoes
      )
      SELECT
        dt.id,
        i.id,
        dt.tributo_id,
        i.empresa_cnpj,
        i.periodo_ano,
        i.periodo_mes,
        i.numero_item,
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
        COALESCE(i.valor_total, 0),
        CASE WHEN dt.natureza = 'debito' THEN
          CASE
            WHEN COALESCE(i.total_itens_documento, 0) > 0
              THEN ROUND((COALESCE(i.valor_total, 0) / i.total_itens_documento) * dt.valor_tributo, 2)
            ELSE 0
          END
        ELSE 0 END,
        CASE WHEN dt.natureza = 'credito' THEN
          CASE
            WHEN COALESCE(i.total_itens_documento, 0) > 0
              THEN ROUND((COALESCE(i.valor_total, 0) / i.total_itens_documento) * dt.valor_tributo, 2)
            ELSE 0
          END
        ELSE 0 END,
        CASE
          WHEN COALESCE(i.total_itens_documento, 0) > 0
            THEN ROUND((COALESCE(i.valor_total, 0) / i.total_itens_documento) * dt.valor_tributo, 2)
          ELSE 0
        END,
        dt.natureza,
        'sped',
        'ativo',
        'Valor do item distribuido proporcionalmente a partir da apuracao ICMS do SPED.'
      FROM itens i
      JOIN public.documentos_fiscais_tributos dt ON dt.sped_documento_id = i.documento_id
       AND dt.origem = 'sped'
      JOIN public.tributos t ON t.id = dt.tributo_id
      WHERE t.codigo = 'ICMS';
      """,
      (cnpj,),
    )

  def inserir_creditos_debitos_sped_icms(self, cur, cnpj: str) -> None:
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
        status,
        observacoes
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
        'disponivel',
        'Credito ICMS distribuido a partir do SPED.'
      FROM public.itens_documentos_fiscais_tributos it
      JOIN public.documentos_fiscais_tributos dt ON dt.id = it.documento_tributo_id
      JOIN public.tributos t ON t.id = it.tributo_id
      WHERE regexp_replace(UPPER(it.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND dt.sped_documento_id IS NOT NULL
        AND dt.origem = 'sped'
        AND it.natureza = 'credito'
        AND t.codigo = 'ICMS'
        AND COALESCE(NULLIF(it.valor_credito, 0), it.valor_tributo, 0) > 0;
      """,
      (cnpj,),
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
        status,
        observacoes
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
        'aberto',
        'Debito ICMS distribuido a partir do SPED.'
      FROM public.itens_documentos_fiscais_tributos it
      JOIN public.documentos_fiscais_tributos dt ON dt.id = it.documento_tributo_id
      JOIN public.tributos t ON t.id = it.tributo_id
      WHERE regexp_replace(UPPER(it.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND dt.sped_documento_id IS NOT NULL
        AND dt.origem = 'sped'
        AND it.natureza = 'debito'
        AND t.codigo = 'ICMS'
        AND COALESCE(NULLIF(it.valor_debito, 0), it.valor_tributo, 0) > 0;
      """,
      (cnpj,),
    )

  def inserir_memoria_sped_icms(self, cur, cnpj: str) -> None:
    cur.execute(
      """
      INSERT INTO public.memoria_calculo_tributaria (
        documento_tributo_id,
        item_tributo_id,
        tributo_id,
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        etapa_calculo,
        base_origem,
        base_calculo,
        valor_calculado,
        formula_calculo,
        parametros_calculo,
        resultado_calculo,
        fonte_dados,
        hash_calculo,
        observacoes
      )
      SELECT
        it.documento_tributo_id,
        it.id,
        it.tributo_id,
        it.empresa_cnpj,
        it.periodo_ano,
        it.periodo_mes,
        'rateio_sped_icms',
        it.base_calculo,
        it.base_calculo,
        COALESCE(NULLIF(it.valor_tributo, 0), NULLIF(it.valor_debito, 0), NULLIF(it.valor_credito, 0), 0),
        'Valor de ICMS distribuido proporcionalmente por documento e item do SPED.',
        jsonb_build_object(
          'origem', 'sped',
          'sped_item_id', it.sped_item_id,
          'documento_tributo_id', it.documento_tributo_id,
          'natureza', it.natureza
        ),
        jsonb_build_object(
          'valor_debito', it.valor_debito,
          'valor_credito', it.valor_credito,
          'valor_tributo', it.valor_tributo
        ),
        'sped',
        md5(concat_ws(
          '|',
          'sped',
          it.id,
          it.documento_tributo_id,
          it.tributo_id,
          it.valor_tributo,
          it.valor_debito,
          it.valor_credito
        )),
        'Memoria gerada a partir do rateio do ICMS informado na apuracao SPED.'
      FROM public.itens_documentos_fiscais_tributos it
      JOIN public.documentos_fiscais_tributos dt ON dt.id = it.documento_tributo_id
      JOIN public.tributos t ON t.id = it.tributo_id
      WHERE regexp_replace(UPPER(it.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND it.sped_item_id IS NOT NULL
        AND dt.origem = 'sped'
        AND t.codigo = 'ICMS'
        AND COALESCE(NULLIF(it.valor_tributo, 0), NULLIF(it.valor_debito, 0), NULLIF(it.valor_credito, 0), 0) <> 0;
      """,
      (cnpj,),
    )

  def remover_creditos_debitos_nfe_periodo(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
    codigos_tributos: tuple[str, ...],
  ) -> None:
    params = (cnpj, periodo_ano, periodo_mes, list(codigos_tributos))
    cur.execute(
      """
      DELETE FROM public.creditos_tributarios c
      USING public.tributos t
      WHERE c.tributo_id = t.id
        AND regexp_replace(UPPER(c.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
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
        AND regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND d.periodo_ano = %s
        AND d.periodo_mes = %s
        AND t.codigo = ANY(%s)
        AND d.origem_debito = 'saida';
      """,
      params,
    )

  def remover_memoria_nfe_periodo(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
    codigos_tributos: tuple[str, ...],
  ) -> None:
    cur.execute(
      """
      DELETE FROM public.memoria_calculo_tributaria m
      USING public.tributos t
      WHERE m.tributo_id = t.id
        AND regexp_replace(UPPER(m.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND m.periodo_ano = %s
        AND m.periodo_mes = %s
        AND m.fonte_dados = 'xml'
        AND t.codigo = ANY(%s);
      """,
      (cnpj, periodo_ano, periodo_mes, list(codigos_tributos)),
    )

  def inserir_documentos_tributos_nfe(
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
        WHERE regexp_replace(UPPER(n.emitente_cnpj), '[^0-9A-Z]', '', 'g') = %s
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

  def inserir_itens_tributos_nfe(
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
        WHERE regexp_replace(UPPER(n.emitente_cnpj), '[^0-9A-Z]', '', 'g') = %s
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

  def tabela_xml_importados_existe(self, cur) -> bool:
    cur.execute("SELECT to_regclass('public.notas_xml_importados')")
    row = cur.fetchone()
    return bool(row and row[0])

  def listar_xmls_importados(self, cur, cnpj: str) -> list[tuple[int, str, bytes]]:
    cur.execute(
      """
      SELECT id, nome_arquivo, conteudo_xml
      FROM public.notas_xml_importados
      WHERE regexp_replace(UPPER(cnpj_emitente), '[^0-9A-Z]', '', 'g') = %s
        AND conteudo_xml IS NOT NULL
      ORDER BY id ASC;
      """,
      (cnpj,),
    )
    return cur.fetchall()

  def buscar_item_nfe_para_xml_importado(
    self,
    cur,
    cnpj: str,
    numero_nf: str,
    modelo: str | None,
    data_emissao,
    numero_item: int,
    produto_codigo: str,
  ) -> tuple[int, int, str] | None:
    cur.execute(
      """
      SELECT n.id, ni.id, n.emitente_cnpj
      FROM public.notas n
      JOIN public.notas_itens ni ON ni.nota_id = n.id
      WHERE regexp_replace(UPPER(n.emitente_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND n.numero_nf = %s
        AND COALESCE(n.modelo, '') = COALESCE(%s, '')
        AND n.data_emissao = %s
        AND ni.item_numero = %s
      ORDER BY CASE WHEN COALESCE(ni.produto_codigo, '') = COALESCE(%s, '') THEN 0 ELSE 1 END
      LIMIT 1;
      """,
      (cnpj, str(numero_nf), modelo, data_emissao, numero_item, produto_codigo),
    )
    return cur.fetchone()

  def inserir_creditos_debitos_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
    codigos_tributos: tuple[str, ...],
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
      WHERE regexp_replace(UPPER(it.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND it.periodo_ano = %s
        AND it.periodo_mes = %s
        AND it.natureza = 'credito'
        AND t.codigo = ANY(%s)
        AND COALESCE(NULLIF(it.valor_credito, 0), it.valor_tributo, 0) > 0;
      """,
      (cnpj, periodo_ano, periodo_mes, list(codigos_tributos)),
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
      WHERE regexp_replace(UPPER(it.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND it.periodo_ano = %s
        AND it.periodo_mes = %s
        AND it.natureza = 'debito'
        AND t.codigo = ANY(%s)
        AND COALESCE(NULLIF(it.valor_debito, 0), it.valor_tributo, 0) > 0;
      """,
      (cnpj, periodo_ano, periodo_mes, list(codigos_tributos)),
    )

  def inserir_memoria_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    cur.execute(
      """
      INSERT INTO public.memoria_calculo_tributaria (
        documento_tributo_id,
        item_tributo_id,
        tributo_id,
        empresa_cnpj,
        periodo_ano,
        periodo_mes,
        etapa_calculo,
        base_origem,
        base_calculo,
        aliquota_aplicada,
        valor_calculado,
        formula_calculo,
        parametros_calculo,
        resultado_calculo,
        fonte_dados,
        hash_calculo,
        observacoes
      )
      SELECT
        it.documento_tributo_id,
        it.id,
        it.tributo_id,
        it.empresa_cnpj,
        it.periodo_ano,
        it.periodo_mes,
        CASE
          WHEN t.tipo = 'reforma' THEN 'extracao_xml_reforma'
          ELSE 'sincronizacao_xml_legado'
        END,
        COALESCE(NULLIF(it.base_calculo, 0), it.valor_tributo, 0),
        COALESCE(NULLIF(it.base_calculo, 0), it.valor_tributo, 0),
        it.aliquota,
        COALESCE(NULLIF(it.valor_tributo, 0), NULLIF(it.valor_debito, 0), NULLIF(it.valor_credito, 0), 0),
        CASE
          WHEN t.tipo = 'reforma' THEN 'Valor extraido das tags da Reforma Tributaria no XML.'
          ELSE 'Valor sincronizado a partir dos tributos legados do XML.'
        END,
        jsonb_build_object(
          'origem', 'xml',
          'nota_item_id', it.nota_item_id,
          'documento_tributo_id', it.documento_tributo_id,
          'natureza', it.natureza
        ),
        jsonb_build_object(
          'valor_debito', it.valor_debito,
          'valor_credito', it.valor_credito,
          'valor_tributo', it.valor_tributo
        ),
        'xml',
        md5(concat_ws(
          '|',
          'xml',
          it.id,
          it.documento_tributo_id,
          it.tributo_id,
          it.valor_tributo,
          it.valor_debito,
          it.valor_credito
        )),
        CASE
          WHEN t.tipo = 'reforma' THEN 'Memoria gerada a partir dos campos CBS/IBS/IS extraidos do XML.'
          ELSE 'Memoria gerada a partir da distribuicao dos tributos legados por item.'
        END
      FROM public.itens_documentos_fiscais_tributos it
      JOIN public.tributos t ON t.id = it.tributo_id
      WHERE regexp_replace(UPPER(it.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
        AND it.periodo_ano = %s
        AND it.periodo_mes = %s
        AND it.nota_item_id IS NOT NULL
        AND it.origem = 'xml'
        AND t.codigo = ANY(%s)
        AND COALESCE(NULLIF(it.valor_tributo, 0), NULLIF(it.valor_debito, 0), NULLIF(it.valor_credito, 0), 0) <> 0;
      """,
      (cnpj, periodo_ano, periodo_mes, list(self.TRIBUTOS_LEGADOS_NFE + self.TRIBUTOS_REFORMA)),
    )

  def atualizar_apuracao_nfe(
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
        WHERE regexp_replace(UPPER(empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
          AND periodo_ano = %s
          AND periodo_mes = %s
        UNION
        SELECT DISTINCT tributo_id
        FROM public.creditos_tributarios
        WHERE regexp_replace(UPPER(empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
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
              AND regexp_replace(UPPER(d.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
              AND d.periodo_ano = %s
              AND d.periodo_mes = %s
          ), 0) AS total_debitos,
          COALESCE((
            SELECT SUM(valor_saldo)
            FROM public.creditos_tributarios c
            WHERE c.tributo_id = tp.tributo_id
              AND regexp_replace(UPPER(c.empresa_cnpj), '[^0-9A-Z]', '', 'g') = %s
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
