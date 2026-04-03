-- Catálogo NCM
-- Estrutura para armazenar a tabela NCM vigente importada de arquivos JSON.

CREATE TABLE IF NOT EXISTS ncm_catalogo (
    codigo CHAR(8) PRIMARY KEY,
    descricao TEXT NOT NULL,
    codigo_formatado VARCHAR(20),
    vigencia DATE,
    fonte_arquivo VARCHAR(255),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ncm_catalogo_descricao
ON ncm_catalogo (descricao);

CREATE INDEX IF NOT EXISTS idx_ncm_catalogo_vigencia
ON ncm_catalogo (vigencia);

COMMENT ON TABLE ncm_catalogo IS 'Catálogo de códigos NCM carregado a partir de arquivos JSON.';
COMMENT ON COLUMN ncm_catalogo.codigo IS 'Código NCM normalizado com 8 dígitos.';
COMMENT ON COLUMN ncm_catalogo.descricao IS 'Descrição oficial do NCM.';
COMMENT ON COLUMN ncm_catalogo.codigo_formatado IS 'Código NCM no formato original do arquivo, se necessário.';
COMMENT ON COLUMN ncm_catalogo.vigencia IS 'Data de vigência da tabela importada.';
COMMENT ON COLUMN ncm_catalogo.fonte_arquivo IS 'Nome do arquivo JSON usado na carga.';
