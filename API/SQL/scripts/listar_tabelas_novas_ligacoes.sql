-- Lista as tabelas novas/relacionadas e suas ligacoes por chave estrangeira.
-- Banco alvo: PostgreSQL
-- Uso: execute este script no banco e consulte os tres result sets gerados.

WITH tabelas_alvo(nome) AS (
    VALUES
        ('ajustes_tributarios'),
        ('aliquotas_tributarias'),
        ('apuracao_tributaria'),
        ('creditos_tributarios'),
        ('debitos_tributarios'),
        ('documentos_fiscais_tributos'),
        ('empresas'),
        ('itens_documentos_fiscais_tributos'),
        ('login'),
        ('memoria_calculo_tributaria'),
        ('municipios_catalogo'),
        ('ncm_catalogo'),
        ('ncm_tributacao'),
        ('notas'),
        ('notas_cfops'),
        ('notas_itens'),
        ('notas_kpis'),
        ('notas_processamento_erros'),
        ('notas_processamentos'),
        ('notas_xml_importados'),
        ('regras_tributarias'),
        ('regras_tributarias_vigencias'),
        ('sped_ajustes_fiscais'),
        ('sped_apuracao_icms'),
        ('sped_apuracao_ipi'),
        ('sped_documento_itens'),
        ('sped_documentos_fiscais'),
        ('sped_empresas'),
        ('sped_inventario'),
        ('sped_kpis_fiscal'),
        ('sped_participantes'),
        ('sped_produtos'),
        ('sped_resumo_cfop_cst'),
        ('sped_importacoes'),
        ('sped_importacoes'),
        ('sped_tributos_itens'),
        ('tributos')
)
SELECT
    t.table_schema,
    t.table_name,
    CASE WHEN c.relname IS NULL THEN 'nao encontrada' ELSE 'encontrada' END AS status
FROM tabelas_alvo ta
LEFT JOIN information_schema.tables t
    ON t.table_schema = 'public'
   AND t.table_name = ta.nome
LEFT JOIN pg_class c
    ON c.relname = ta.nome
   AND c.relnamespace = 'public'::regnamespace
ORDER BY ta.nome;


WITH tabelas_alvo(nome) AS (
    VALUES
        ('ajustes_tributarios'),
        ('aliquotas_tributarias'),
        ('apuracao_tributaria'),
        ('creditos_tributarios'),
        ('debitos_tributarios'),
        ('documentos_fiscais_tributos'),
        ('empresas'),
        ('itens_documentos_fiscais_tributos'),
        ('login'),
        ('memoria_calculo_tributaria'),
        ('municipios_catalogo'),
        ('ncm_catalogo'),
        ('ncm_tributacao'),
        ('notas'),
        ('notas_cfops'),
        ('notas_itens'),
        ('notas_kpis'),
        ('notas_processamento_erros'),
        ('notas_processamentos'),
        ('notas_xml_importados'),
        ('regras_tributarias'),
        ('regras_tributarias_vigencias'),
        ('sped_ajustes_fiscais'),
        ('sped_apuracao_icms'),
        ('sped_apuracao_ipi'),
        ('sped_documento_itens'),
        ('sped_documentos_fiscais'),
        ('sped_empresas'),
        ('sped_inventario'),
        ('sped_kpis_fiscal'),
        ('sped_participantes'),
        ('sped_produtos'),
        ('sped_resumo_cfop_cst'),
        ('sped_sped_importacoes'),
        ('sped_importacoes'),
        ('sped_tributos_itens'),
        ('tributos')
)
SELECT
    c.table_schema,
    c.table_name,
    c.ordinal_position,
    c.column_name,
    c.data_type,
    COALESCE(c.character_maximum_length::text, c.numeric_precision::text, '') AS tamanho_precisao,
    c.is_nullable,
    c.column_default,
    CASE WHEN pk.column_name IS NOT NULL THEN 'sim' ELSE 'nao' END AS chave_primaria
FROM information_schema.columns c
JOIN tabelas_alvo ta
    ON ta.nome = c.table_name
LEFT JOIN (
    SELECT
        ku.table_schema,
        ku.table_name,
        ku.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage ku
        ON ku.constraint_schema = tc.constraint_schema
       AND ku.constraint_name = tc.constraint_name
       AND ku.table_schema = tc.table_schema
       AND ku.table_name = tc.table_name
    WHERE tc.constraint_type = 'PRIMARY KEY'
) pk
    ON pk.table_schema = c.table_schema
   AND pk.table_name = c.table_name
   AND pk.column_name = c.column_name
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;


WITH tabelas_alvo(nome) AS (
    VALUES
        ('ajustes_tributarios'),
        ('aliquotas_tributarias'),
        ('apuracao_tributaria'),
        ('creditos_tributarios'),
        ('debitos_tributarios'),
        ('documentos_fiscais_tributos'),
        ('empresas'),
        ('itens_documentos_fiscais_tributos'),
        ('login'),
        ('memoria_calculo_tributaria'),
        ('municipios_catalogo'),
        ('ncm_catalogo'),
        ('ncm_tributacao'),
        ('notas'),
        ('notas_cfops'),
        ('notas_itens'),
        ('notas_kpis'),
        ('notas_processamento_erros'),
        ('notas_processamentos'),
        ('notas_xml_importados'),
        ('regras_tributarias'),
        ('regras_tributarias_vigencias'),
        ('sped_ajustes_fiscais'),
        ('sped_apuracao_icms'),
        ('sped_apuracao_ipi'),
        ('sped_documento_itens'),
        ('sped_documentos_fiscais'),
        ('sped_empresas'),
        ('sped_inventario'),
        ('sped_kpis_fiscal'),
        ('sped_participantes'),
        ('sped_produtos'),
        ('sped_resumo_cfop_cst'),
        ('sped_sped_importacoes'),
        ('sped_importacoes'),
        ('sped_tributos_itens'),
        ('tributos')
),
fk_cols AS (
    SELECT
        con.oid AS constraint_oid,
        con.conname AS constraint_name,
        src_ns.nspname AS origem_schema,
        src.relname AS origem_tabela,
        src_att.attname AS origem_coluna,
        dst_ns.nspname AS destino_schema,
        dst.relname AS destino_tabela,
        dst_att.attname AS destino_coluna,
        ord.n AS ordem_coluna,
        con.confdeltype AS delete_action_code,
        con.confupdtype AS update_action_code
    FROM pg_constraint con
    JOIN pg_class src
        ON src.oid = con.conrelid
    JOIN pg_namespace src_ns
        ON src_ns.oid = src.relnamespace
    JOIN pg_class dst
        ON dst.oid = con.confrelid
    JOIN pg_namespace dst_ns
        ON dst_ns.oid = dst.relnamespace
    JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS src_key(attnum, n)
        ON TRUE
    JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS dst_key(attnum, n)
        ON dst_key.n = src_key.n
    JOIN pg_attribute src_att
        ON src_att.attrelid = src.oid
       AND src_att.attnum = src_key.attnum
    JOIN pg_attribute dst_att
        ON dst_att.attrelid = dst.oid
       AND dst_att.attnum = dst_key.attnum
    JOIN LATERAL (SELECT src_key.n) ord
        ON TRUE
    WHERE con.contype = 'f'
      AND src_ns.nspname = 'public'
      AND dst_ns.nspname = 'public'
      AND (
          src.relname IN (SELECT nome FROM tabelas_alvo)
          OR dst.relname IN (SELECT nome FROM tabelas_alvo)
      )
)
SELECT
    constraint_name,
    origem_schema,
    origem_tabela,
    string_agg(origem_coluna, ', ' ORDER BY ordem_coluna) AS origem_colunas,
    destino_schema,
    destino_tabela,
    string_agg(destino_coluna, ', ' ORDER BY ordem_coluna) AS destino_colunas,
    CASE max(delete_action_code)
        WHEN 'a' THEN 'NO ACTION'
        WHEN 'r' THEN 'RESTRICT'
        WHEN 'c' THEN 'CASCADE'
        WHEN 'n' THEN 'SET NULL'
        WHEN 'd' THEN 'SET DEFAULT'
    END AS on_delete,
    CASE max(update_action_code)
        WHEN 'a' THEN 'NO ACTION'
        WHEN 'r' THEN 'RESTRICT'
        WHEN 'c' THEN 'CASCADE'
        WHEN 'n' THEN 'SET NULL'
        WHEN 'd' THEN 'SET DEFAULT'
    END AS on_update,
    origem_tabela || ' -> ' || destino_tabela AS ligacao
FROM fk_cols
GROUP BY
    constraint_oid,
    constraint_name,
    origem_schema,
    origem_tabela,
    destino_schema,
    destino_tabela
ORDER BY origem_tabela, destino_tabela, constraint_name;
