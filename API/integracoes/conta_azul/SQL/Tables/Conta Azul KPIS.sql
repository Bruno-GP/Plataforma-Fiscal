CREATE TABLE IF NOT EXISTS conta_azul_kpis (
  id               SERIAL          PRIMARY KEY,
  empresa_id       BIGINT          NOT NULL,
  mes              DATE            NOT NULL,               -- primeiro dia do mês (ex: 2026-01-01)
  total_pedidos    INTEGER         NOT NULL DEFAULT 0,
  clientes_ativos  INTEGER         NOT NULL DEFAULT 0,
  receita_total    NUMERIC(15, 2)  NOT NULL DEFAULT 0,
  ticket_medio     NUMERIC(15, 2)  NOT NULL DEFAULT 0,
  criado_em        TIMESTAMPTZ     NOT NULL DEFAULT now(),
  atualizado_em    TIMESTAMPTZ     NOT NULL DEFAULT now(),
  CONSTRAINT fk_ca_kpis_empresa
      FOREIGN KEY (empresa_id) REFERENCES empresas(id)
      ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT uq_ca_kpis_empresa_mes UNIQUE (empresa_id, mes)
);
