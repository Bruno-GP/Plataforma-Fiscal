CREATE TABLE IF NOT EXISTS public.ncm_tributacao (
    id BIGSERIAL PRIMARY KEY,
    ncm_codigo CHAR(8) NOT NULL,
    uf CHAR(2) NOT NULL,
    nacional_federal NUMERIC(6,2),
    importados_federal NUMERIC(6,2),
    estadual NUMERIC(6,2),
    municipal NUMERIC(6,2),
    vigencia_inicio DATE,
    vigencia_fim DATE,
    versao VARCHAR(20),
    fonte VARCHAR(100),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ncm_tributacao_ncm_uf UNIQUE (ncm_codigo, uf),
    CONSTRAINT fk_ncm_tributacao_catalogo
        FOREIGN KEY (ncm_codigo)
        REFERENCES public.ncm_catalogo (codigo)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ncm_tributacao_codigo
ON public.ncm_tributacao (ncm_codigo);

CREATE INDEX IF NOT EXISTS idx_ncm_tributacao_uf
ON public.ncm_tributacao (uf);
