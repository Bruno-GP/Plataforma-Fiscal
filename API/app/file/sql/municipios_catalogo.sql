-- Catálogo de municípios
-- Estrutura para armazenar metadados de municípios utilizados pela aplicação.
-- A geometria pesada de LL-municipios.json permanece em arquivo local.

CREATE TABLE IF NOT EXISTS municipios_catalogo (
    codigo_ibge CHAR(7) PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    uf CHAR(2) NOT NULL,
    regiao VARCHAR(20),
    mesorregiao VARCHAR(100),
    microrregiao VARCHAR(100),
    capital BOOLEAN,
    codigo_uf CHAR(2),
    fonte_arquivo VARCHAR(255),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_municipios_catalogo_uf
ON municipios_catalogo (uf);

CREATE INDEX IF NOT EXISTS idx_municipios_catalogo_nome
ON municipios_catalogo (nome);

CREATE INDEX IF NOT EXISTS idx_municipios_catalogo_codigo_uf
ON municipios_catalogo (codigo_uf);

COMMENT ON TABLE municipios_catalogo IS 'Catálogo de municípios para consultas por código IBGE, nome e UF.';
COMMENT ON COLUMN municipios_catalogo.codigo_ibge IS 'Código IBGE do município com 7 dígitos.';
COMMENT ON COLUMN municipios_catalogo.nome IS 'Nome do município.';
COMMENT ON COLUMN municipios_catalogo.uf IS 'Sigla da unidade federativa.';
COMMENT ON COLUMN municipios_catalogo.regiao IS 'Região geográfica do município, quando disponível.';
COMMENT ON COLUMN municipios_catalogo.mesorregiao IS 'Mesorregião do município, quando disponível.';
COMMENT ON COLUMN municipios_catalogo.microrregiao IS 'Microrregião do município, quando disponível.';
COMMENT ON COLUMN municipios_catalogo.capital IS 'Indica se o município é capital.';
COMMENT ON COLUMN municipios_catalogo.codigo_uf IS 'Prefixo/código IBGE da UF, quando disponível.';
COMMENT ON COLUMN municipios_catalogo.fonte_arquivo IS 'Nome do arquivo JSON usado na carga.';
