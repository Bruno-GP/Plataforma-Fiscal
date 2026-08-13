# Metas com Análise de Indicadores (fase 1 — backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backend completo do módulo Metas — modelo de dados, motor de análise de indicador
(`AnaliseMetaService`), job Celery que materializa `indicador_historico` a partir de `notas_kpis`,
e endpoints REST `/api/metas` e `/api/indicadores`. Sem frontend (spec seguinte).

**Architecture:** Segue `docs/backend-target-structure.md` — `api/metas/` (rotas finas) →
`services/metas/` (orquestração + regra pura de análise) → `repositories/metas/` (único lugar
com SQL) → `models/metas/schemas.py` (contratos Pydantic). Novo domínio `metas`, perfil XML/NFe
only nesta fase. Fonte de dado é a tabela `notas_kpis` já existente — nenhuma leitura nova de
`notas`/`notas_itens`.

**Tech Stack:** FastAPI, Pydantic v2 (`pydantic==2.8.2`), psycopg3 (`psycopg[binary]==3.2.1`),
Alembic, Celery + Redis, `statistics` (stdlib, sem numpy/scipy), pytest.

## Global Constraints

- Tenant key: `empresas.id` (BIGINT), nunca UUID. Todo filtro usa `current_user.empresa_id` do
  token — nenhuma rota de Metas aceita `empresa_id` como query param.
- Perfil desta fase: só `tem_xml = true`. Não implementar nada de SPED.
- `indicadores` é catálogo fixo seedado por migration nesta fase — sem rota de escrita.
- Sem `HTTPException` em `services/` ou `repositories/` — exceções de domínio próprias, convertidas
  em `HTTPException` só na rota (`docs/backend-error-handling.md`).
- Sem SQL fora de `repositories/`.
- CNPJ é comparado sempre normalizado: `regexp_replace(UPPER(COALESCE(col, '')), '[^0-9A-Z]', '', 'g')`
  no SQL, `app.services.nfe.empresa_service.normalizar_cnpj` no Python — ver
  `API/app/repositories/nfe/consulta_repository.py:15` e memória de projeto `project_cnpj_alfanumerico`.
- Valores monetários: `Decimal`, coluna `NUMERIC(18,2)`.
- Todo teste de rota usa a fixture `client` de `API/app/tests/conftest.py` (usuário anônimo
  `empresa_id=1`, `cnpj="12345678000190"`, `tem_sped=False`).

---

### Task 1: Migration — tabelas `indicadores`, `indicador_historico`, `metas`

**Files:**
- Create: `API/app/alembic/versions/20260813_0012_metas_tabelas.py`

**Interfaces:**
- Produces: tabelas `indicadores` (seed com 6 linhas), `indicador_historico`, `metas` — nomes de
  coluna exatamente como listados abaixo. Todas as tasks seguintes dependem desses nomes.

- [ ] **Step 1: Criar a migration**

```python
"""cria tabelas do modulo Metas: indicadores, indicador_historico, metas

Contexto: fase 1 do modulo de Metas (docs/superpowers/specs/2026-08-13-metas-design.md).
indicadores e catalogo fixo (seed nesta migration, perfil xml, fonte notas_kpis).
indicador_historico e materializado por job Celery (app/workers/metas_tasks.py) a partir
de notas_kpis, nao recalcula de notas/notas_itens.

Revision ID: 20260813_0012
Revises: 20260731_0011
Create Date: 2026-08-13
"""

from alembic import op


revision = "20260813_0012"
down_revision = "20260731_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS indicadores (
            id              BIGSERIAL       PRIMARY KEY,
            chave           VARCHAR(50)     NOT NULL UNIQUE,
            nome            VARCHAR(120)    NOT NULL,
            unidade         VARCHAR(20)     NOT NULL CHECK (unidade IN ('moeda','percentual','numero','dias')),
            fonte           VARCHAR(50)     NOT NULL DEFAULT 'notas_kpis',
            direcao_boa     VARCHAR(20)     NOT NULL CHECK (direcao_boa IN ('maior_melhor','menor_melhor')),
            perfil          VARCHAR(10)     NOT NULL DEFAULT 'xml' CHECK (perfil IN ('xml','sped')),
            ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
            criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS indicador_historico (
            id                  BIGSERIAL       PRIMARY KEY,
            empresa_id          BIGINT          NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            indicador_id        BIGINT          NOT NULL REFERENCES indicadores(id) ON DELETE CASCADE,
            periodo_referencia  DATE            NOT NULL,
            valor               NUMERIC(18,2)   NOT NULL,
            calculado_em        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            UNIQUE (empresa_id, indicador_id, periodo_referencia)
        );

        CREATE INDEX IF NOT EXISTS idx_indicador_historico_busca
            ON indicador_historico (empresa_id, indicador_id, periodo_referencia);

        CREATE TABLE IF NOT EXISTS metas (
            id              BIGSERIAL       PRIMARY KEY,
            empresa_id      BIGINT          NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            indicador_id    BIGINT          NOT NULL REFERENCES indicadores(id),
            titulo          VARCHAR(200)    NOT NULL,
            descricao       TEXT,
            valor_alvo      NUMERIC(18,2)   NOT NULL,
            tipo_meta       VARCHAR(20)     NOT NULL CHECK (tipo_meta IN ('crescimento','reducao','manutencao')),
            periodo_tipo    VARCHAR(20)     NOT NULL CHECK (periodo_tipo IN ('mensal','trimestral','anual','custom')),
            periodo_inicio  DATE            NOT NULL,
            periodo_fim     DATE            NOT NULL,
            status          VARCHAR(20)     NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa','atingida','nao_atingida','cancelada')),
            criado_por      BIGINT          NOT NULL REFERENCES login(id),
            criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            atualizado_em   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
            CHECK (periodo_fim >= periodo_inicio)
        );

        CREATE INDEX IF NOT EXISTS idx_metas_empresa_status ON metas (empresa_id, status);

        INSERT INTO indicadores (chave, nome, unidade, fonte, direcao_boa, perfil) VALUES
            ('faturamento', 'Faturamento', 'moeda', 'notas_kpis', 'maior_melhor', 'xml'),
            ('ticket_medio', 'Ticket médio', 'moeda', 'notas_kpis', 'maior_melhor', 'xml'),
            ('quantidade_notas', 'Quantidade de notas', 'numero', 'notas_kpis', 'maior_melhor', 'xml'),
            ('total_icms', 'ICMS pago', 'moeda', 'notas_kpis', 'menor_melhor', 'xml'),
            ('total_ipi', 'IPI pago', 'moeda', 'notas_kpis', 'menor_melhor', 'xml'),
            ('total_pis_cofins', 'PIS+COFINS pago', 'moeda', 'notas_kpis', 'menor_melhor', 'xml')
        ON CONFLICT (chave) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS metas;
        DROP TABLE IF EXISTS indicador_historico;
        DROP TABLE IF EXISTS indicadores;
        """
    )
```

- [ ] **Step 2: Validar sintaxe SQL sem depender de Postgres real**

Run: `cd API && .\.venv-local\Scripts\python.exe -c "import ast; ast.parse(open('app/alembic/versions/20260813_0012_metas_tabelas.py').read())"`
Expected: sem saída (arquivo Python válido).

- [ ] **Step 3: Rodar a suite rápida pra garantir que nada quebrou por import**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q`
Expected: mesma contagem de PASS de antes (migration nova não é executada pela suite rápida,
só pelos testes de `test_database_schema.py` que exigem `PLATAFORMA_FISCAL_TEST_DATABASE_URL`).

- [ ] **Step 4: Commit**

```bash
git add API/app/alembic/versions/20260813_0012_metas_tabelas.py
git commit -m "feat: cria tabelas indicadores, indicador_historico e metas"
```

---

### Task 2: Schemas Pydantic (`app/models/metas/schemas.py`)

**Files:**
- Create: `API/app/models/metas/schemas.py`

**Interfaces:**
- Consumes: nada (schemas puros).
- Produces: `TipoMeta`, `PeriodoTipo`, `StatusMeta`, `UnidadeIndicador`, `DirecaoBoa`,
  `IndicadorPerfil`, `IndicadorResponse`, `IndicadorHistoricoPontoResponse`,
  `IndicadorHistoricoResponse`, `MetaCreateRequest`, `MetaUpdateRequest`, `MetaResponse`,
  `MetaListResponse`, `AnaliseMetaResponse` — usados por `services/metas` e `api/metas` nas
  próximas tasks.

- [ ] **Step 1: Criar o arquivo de schemas**

```python
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class TipoMeta(StrEnum):
    CRESCIMENTO = "crescimento"
    REDUCAO = "reducao"
    MANUTENCAO = "manutencao"


class PeriodoTipo(StrEnum):
    MENSAL = "mensal"
    TRIMESTRAL = "trimestral"
    ANUAL = "anual"
    CUSTOM = "custom"


class StatusMeta(StrEnum):
    ATIVA = "ativa"
    ATINGIDA = "atingida"
    NAO_ATINGIDA = "nao_atingida"
    CANCELADA = "cancelada"


class UnidadeIndicador(StrEnum):
    MOEDA = "moeda"
    PERCENTUAL = "percentual"
    NUMERO = "numero"
    DIAS = "dias"


class DirecaoBoa(StrEnum):
    MAIOR_MELHOR = "maior_melhor"
    MENOR_MELHOR = "menor_melhor"


class IndicadorPerfil(StrEnum):
    XML = "xml"
    SPED = "sped"


class IndicadorResponse(BaseModel):
    id: int
    chave: str
    nome: str
    unidade: UnidadeIndicador
    direcao_boa: DirecaoBoa
    perfil: IndicadorPerfil


class IndicadorListResponse(BaseModel):
    resultados: list[IndicadorResponse]


class IndicadorHistoricoPontoResponse(BaseModel):
    periodo: date
    valor: Decimal


class IndicadorHistoricoResponse(BaseModel):
    indicador_id: int
    resultados: list[IndicadorHistoricoPontoResponse]


class MetaCreateRequest(BaseModel):
    indicador_id: int
    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = None
    valor_alvo: Decimal = Field(gt=0)
    tipo_meta: TipoMeta
    periodo_tipo: PeriodoTipo
    periodo_inicio: date
    periodo_fim: date

    @field_validator("periodo_fim")
    @classmethod
    def periodo_fim_nao_pode_ser_antes_do_inicio(cls, valor: date, info) -> date:
        periodo_inicio = info.data.get("periodo_inicio")
        if periodo_inicio is not None and valor < periodo_inicio:
            raise ValueError("periodo_fim nao pode ser anterior a periodo_inicio")
        return valor


class MetaUpdateRequest(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descricao: str | None = None
    valor_alvo: Decimal | None = Field(default=None, gt=0)
    status: StatusMeta | None = None


class MetaResponse(BaseModel):
    id: int
    empresa_id: int
    indicador_id: int
    titulo: str
    descricao: str | None = None
    valor_alvo: Decimal
    tipo_meta: TipoMeta
    periodo_tipo: PeriodoTipo
    periodo_inicio: date
    periodo_fim: date
    status: StatusMeta
    criado_em: datetime
    atualizado_em: datetime


class MetaListResponse(BaseModel):
    total: int
    resultados: list[MetaResponse]


class AnaliseMetaResponse(BaseModel):
    meta_id: int
    valor_alvo: Decimal
    valor_realizado_atual: Decimal
    percentual_atingido: Decimal
    tempo_decorrido_pct: Decimal
    status_ritmo: str
    tendencia: str
    media_periodos_anteriores: Decimal
    mediana_periodos_anteriores: Decimal
    desvio_padrao_periodos_anteriores: Decimal
    variacao_vs_media_pct: Decimal | None
    diagnostico: str
    serie_historica: list[IndicadorHistoricoPontoResponse]
    projecao_fim_periodo: Decimal
    comparativo_ano_anterior_pct: Decimal | None = None
```

- [ ] **Step 2: Testar que o módulo importa e valida os casos básicos**

```python
# API/app/tests/test_metas_schemas.py
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.metas.schemas import MetaCreateRequest, TipoMeta, PeriodoTipo


def test_meta_create_request_aceita_payload_valido():
    meta = MetaCreateRequest(
        indicador_id=1,
        titulo="Crescer faturamento",
        valor_alvo=Decimal("50000.00"),
        tipo_meta=TipoMeta.CRESCIMENTO,
        periodo_tipo=PeriodoTipo.MENSAL,
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
    )
    assert meta.valor_alvo == Decimal("50000.00")


def test_meta_create_request_rejeita_periodo_fim_antes_do_inicio():
    with pytest.raises(ValidationError):
        MetaCreateRequest(
            indicador_id=1,
            titulo="Meta invalida",
            valor_alvo=Decimal("1000.00"),
            tipo_meta=TipoMeta.CRESCIMENTO,
            periodo_tipo=PeriodoTipo.MENSAL,
            periodo_inicio=date(2026, 8, 31),
            periodo_fim=date(2026, 8, 1),
        )


def test_meta_create_request_rejeita_valor_alvo_zero():
    with pytest.raises(ValidationError):
        MetaCreateRequest(
            indicador_id=1,
            titulo="Meta invalida",
            valor_alvo=Decimal("0"),
            tipo_meta=TipoMeta.CRESCIMENTO,
            periodo_tipo=PeriodoTipo.MENSAL,
            periodo_inicio=date(2026, 8, 1),
            periodo_fim=date(2026, 8, 31),
        )
```

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_schemas.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.models.metas'`) até o Step 1 existir —
como o Step 1 já foi escrito acima, rode o teste depois de criar o arquivo do Step 1 e confirme
PASS direto.

- [ ] **Step 3: Rodar e confirmar PASS**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_schemas.py -q`
Expected: `3 passed`

- [ ] **Step 4: Commit**

```bash
git add API/app/models/metas/schemas.py API/app/tests/test_metas_schemas.py
git commit -m "feat: adiciona schemas Pydantic do modulo Metas"
```

---

### Task 3: `AnaliseMetaService` — motor de análise puro

**Files:**
- Create: `API/app/services/metas/analise_meta_service.py`
- Test: `API/app/tests/test_analise_meta_service.py`

**Interfaces:**
- Consumes: nada (função pura — sem banco, sem FastAPI).
- Produces: `PontoHistorico(periodo: date, valor: Decimal)`, `Tendencia` (StrEnum),
  `StatusRitmo` (StrEnum), `AnaliseMeta` (dataclass), `analisar_meta(...) -> AnaliseMeta`,
  `gerar_diagnostico(...) -> str`. `services/metas/metas_service.py` (Task 8) chama
  `analisar_meta` diretamente.

- [ ] **Step 1: Escrever os testes primeiro (séries sintéticas, sem banco)**

```python
# API/app/tests/test_analise_meta_service.py
from datetime import date
from decimal import Decimal

from app.services.metas.analise_meta_service import (
    PontoHistorico,
    StatusRitmo,
    Tendencia,
    analisar_meta,
    calcular_tendencia,
)


def _serie_mensal(valores: list[str], ano: int = 2026, mes_inicial: int = 1) -> list[PontoHistorico]:
    pontos = []
    ano_corrente, mes_corrente = ano, mes_inicial
    for valor in valores:
        pontos.append(PontoHistorico(periodo=date(ano_corrente, mes_corrente, 1), valor=Decimal(valor)))
        mes_corrente += 1
        if mes_corrente > 12:
            mes_corrente = 1
            ano_corrente += 1
    return pontos


def test_tendencia_crescimento_forte():
    serie = [p.valor for p in _serie_mensal(["10000", "11500", "13000", "14500", "16000", "17500"])]
    assert calcular_tendencia(serie) == Tendencia.CRESCIMENTO_FORTE


def test_tendencia_queda_forte():
    serie = [p.valor for p in _serie_mensal(["17500", "16000", "14500", "13000", "11500", "10000"])]
    assert calcular_tendencia(serie) == Tendencia.QUEDA_FORTE


def test_tendencia_estavel():
    serie = [p.valor for p in _serie_mensal(["10000", "10100", "9950", "10050", "9980", "10020"])]
    assert calcular_tendencia(serie) == Tendencia.ESTAVEL


def test_tendencia_serie_curta_nao_quebra():
    assert calcular_tendencia([Decimal("100")]) == Tendencia.ESTAVEL
    assert calcular_tendencia([]) == Tendencia.ESTAVEL


def test_analisar_meta_no_caminho_maior_melhor():
    serie_anterior = _serie_mensal(["30000", "31000", "32000", "33000", "34000", "35000"], mes_inicial=2)
    analise = analisar_meta(
        valor_alvo=Decimal("50000.00"),
        direcao_boa="maior_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 22),
        valor_realizado_atual=Decimal("36000.00"),
        serie_historica=serie_anterior,
    )
    assert analise.tendencia == Tendencia.CRESCIMENTO_FORTE
    assert analise.status_ritmo == StatusRitmo.NO_CAMINHO
    assert analise.projecao_fim_periodo > Decimal("50000.00")


def test_analisar_meta_fora_da_rota_maior_melhor():
    serie_anterior = _serie_mensal(["35000", "34000", "33000", "32000", "31000", "30000"], mes_inicial=2)
    analise = analisar_meta(
        valor_alvo=Decimal("50000.00"),
        direcao_boa="maior_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 22),
        valor_realizado_atual=Decimal("15000.00"),
        serie_historica=serie_anterior,
    )
    assert analise.tendencia == Tendencia.QUEDA_FORTE
    assert analise.status_ritmo == StatusRitmo.FORA_DA_ROTA
    assert "faltam" in analise.diagnostico.lower() or "não será" in analise.diagnostico.lower()


def test_analisar_meta_menor_melhor_inverte_ritmo():
    # meta de reducao de ICMS: realizado MAIOR que o alvo = fora da rota, nao no caminho
    serie_anterior = _serie_mensal(["5000", "5100", "5200", "5300", "5400", "5500"], mes_inicial=2)
    analise = analisar_meta(
        valor_alvo=Decimal("4000.00"),
        direcao_boa="menor_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 22),
        valor_realizado_atual=Decimal("5600.00"),
        serie_historica=serie_anterior,
    )
    assert analise.status_ritmo == StatusRitmo.FORA_DA_ROTA


def test_analisar_meta_sazonalidade_com_doze_meses():
    serie_anterior = _serie_mensal(
        ["10000", "10200", "10400", "10600", "10800", "11000",
         "11200", "11400", "11600", "11800", "12000", "12200"],
        ano=2025,
        mes_inicial=8,
    )
    analise = analisar_meta(
        valor_alvo=Decimal("15000.00"),
        direcao_boa="maior_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 15),
        valor_realizado_atual=Decimal("12500.00"),
        serie_historica=serie_anterior,
    )
    assert analise.comparativo_ano_anterior_pct is not None


def test_analisar_meta_sem_historico_suficiente_nao_quebra():
    analise = analisar_meta(
        valor_alvo=Decimal("10000.00"),
        direcao_boa="maior_melhor",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        data_referencia=date(2026, 8, 5),
        valor_realizado_atual=Decimal("1000.00"),
        serie_historica=[],
    )
    assert analise.tendencia == Tendencia.ESTAVEL
    assert analise.comparativo_ano_anterior_pct is None
    assert analise.variacao_vs_media_pct is None
```

- [ ] **Step 2: Rodar e confirmar que falha por módulo ausente**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_analise_meta_service.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.services.metas'`)

- [ ] **Step 3: Implementar `analise_meta_service.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
import statistics


class Tendencia(StrEnum):
    CRESCIMENTO_FORTE = "crescimento_forte"
    CRESCIMENTO_LEVE = "crescimento_leve"
    ESTAVEL = "estavel"
    QUEDA_LEVE = "queda_leve"
    QUEDA_FORTE = "queda_forte"


class StatusRitmo(StrEnum):
    NO_CAMINHO = "no_caminho"
    EM_RISCO = "em_risco"
    FORA_DA_ROTA = "fora_da_rota"


MAIOR_MELHOR = "maior_melhor"
MENOR_MELHOR = "menor_melhor"

_LIMIAR_TENDENCIA_FORTE = Decimal("10")
_LIMIAR_TENDENCIA_LEVE = Decimal("3")


@dataclass(frozen=True)
class PontoHistorico:
    periodo: date
    valor: Decimal


@dataclass(frozen=True)
class AnaliseMeta:
    valor_alvo: Decimal
    valor_realizado_atual: Decimal
    percentual_atingido: Decimal
    tempo_decorrido_pct: Decimal
    status_ritmo: StatusRitmo
    tendencia: Tendencia
    media_periodos_anteriores: Decimal
    mediana_periodos_anteriores: Decimal
    desvio_padrao_periodos_anteriores: Decimal
    variacao_vs_media_pct: Decimal | None
    projecao_fim_periodo: Decimal
    diagnostico: str
    serie_historica: list[PontoHistorico]
    comparativo_ano_anterior_pct: Decimal | None = None


def calcular_estatisticas(serie: list[Decimal]) -> tuple[Decimal, Decimal, Decimal]:
    if not serie:
        return Decimal("0"), Decimal("0"), Decimal("0")
    media = statistics.mean(serie)
    mediana = statistics.median(serie)
    desvio = statistics.pstdev(serie) if len(serie) > 1 else Decimal("0")
    return Decimal(media), Decimal(mediana), Decimal(desvio)


def calcular_tendencia(serie: list[Decimal]) -> Tendencia:
    n = len(serie)
    if n < 2:
        return Tendencia.ESTAVEL

    xs = list(range(n))
    media_x = (n - 1) / 2
    media_y = float(sum(serie)) / n

    numerador = sum((x - media_x) * (float(y) - media_y) for x, y in zip(xs, serie))
    denominador = sum((x - media_x) ** 2 for x in xs)
    if denominador == 0 or media_y == 0:
        return Tendencia.ESTAVEL

    slope = numerador / denominador
    variacao_pct = Decimal(str((slope * (n - 1)) / media_y * 100))

    if variacao_pct > _LIMIAR_TENDENCIA_FORTE:
        return Tendencia.CRESCIMENTO_FORTE
    if variacao_pct > _LIMIAR_TENDENCIA_LEVE:
        return Tendencia.CRESCIMENTO_LEVE
    if variacao_pct < -_LIMIAR_TENDENCIA_FORTE:
        return Tendencia.QUEDA_FORTE
    if variacao_pct < -_LIMIAR_TENDENCIA_LEVE:
        return Tendencia.QUEDA_LEVE
    return Tendencia.ESTAVEL


def calcular_tempo_decorrido_pct(periodo_inicio: date, periodo_fim: date, data_referencia: date) -> Decimal:
    dias_totais = (periodo_fim - periodo_inicio).days + 1
    if dias_totais <= 0:
        return Decimal("100")
    dias_decorridos = (min(data_referencia, periodo_fim) - periodo_inicio).days + 1
    dias_decorridos = max(0, dias_decorridos)
    pct = Decimal(dias_decorridos) / Decimal(dias_totais) * 100
    return min(pct, Decimal("100")).quantize(Decimal("0.01"))


def calcular_projecao(valor_realizado_atual: Decimal, tempo_decorrido_pct: Decimal) -> Decimal:
    if tempo_decorrido_pct <= 0:
        return valor_realizado_atual
    return (valor_realizado_atual / (tempo_decorrido_pct / 100)).quantize(Decimal("0.01"))


def classificar_ritmo(projecao: Decimal, valor_alvo: Decimal, direcao_boa: str) -> StatusRitmo:
    if valor_alvo == 0:
        return StatusRitmo.EM_RISCO

    ratio_pct = (projecao / valor_alvo * 100).quantize(Decimal("0.01"))

    if direcao_boa == MENOR_MELHOR:
        if ratio_pct <= 105:
            return StatusRitmo.NO_CAMINHO
        if ratio_pct <= 120:
            return StatusRitmo.EM_RISCO
        return StatusRitmo.FORA_DA_ROTA

    if ratio_pct >= 95:
        return StatusRitmo.NO_CAMINHO
    if ratio_pct >= 80:
        return StatusRitmo.EM_RISCO
    return StatusRitmo.FORA_DA_ROTA


def comparar_sazonalidade(
    serie_historica: list[PontoHistorico], valor_atual: Decimal, mes_referencia: int, ano_referencia: int
) -> Decimal | None:
    if len(serie_historica) < 12:
        return None
    ano_anterior = ano_referencia - 1
    ponto_ano_anterior = next(
        (p for p in serie_historica if p.periodo.year == ano_anterior and p.periodo.month == mes_referencia),
        None,
    )
    if ponto_ano_anterior is None or ponto_ano_anterior.valor == 0:
        return None
    return ((valor_atual - ponto_ano_anterior.valor) / ponto_ano_anterior.valor * 100).quantize(Decimal("0.01"))


def gerar_diagnostico(
    *,
    tendencia: Tendencia,
    status_ritmo: StatusRitmo,
    direcao_boa: str,
    variacao_vs_media_pct: Decimal | None,
    valor_alvo: Decimal,
    valor_realizado_atual: Decimal,
) -> str:
    diferenca = valor_alvo - valor_realizado_atual if direcao_boa == MAIOR_MELHOR else valor_realizado_atual - valor_alvo

    if variacao_vs_media_pct is None:
        base = "Ainda não há histórico suficiente pra comparar com a média dos períodos anteriores."
    elif variacao_vs_media_pct >= 0:
        base = f"Você está {abs(variacao_vs_media_pct)}% acima da média dos períodos anteriores."
    else:
        base = f"Você está {abs(variacao_vs_media_pct)}% abaixo da média dos períodos anteriores."

    if status_ritmo == StatusRitmo.NO_CAMINHO:
        conclusao = "No ritmo atual, a meta deve ser batida até o fim do período."
    elif status_ritmo == StatusRitmo.EM_RISCO:
        conclusao = f"No ritmo atual, a meta está em risco — faltam {abs(diferenca)} pra chegar ao alvo."
    else:
        tendencia_texto = "caindo" if tendencia in (Tendencia.QUEDA_LEVE, Tendencia.QUEDA_FORTE) else "sem crescer o suficiente"
        conclusao = f"O indicador está {tendencia_texto}. Nesse ritmo, a meta não será atingida — faltam {abs(diferenca)} pra chegar ao alvo."

    return f"{base} {conclusao}"


def analisar_meta(
    *,
    valor_alvo: Decimal,
    direcao_boa: str,
    periodo_inicio: date,
    periodo_fim: date,
    data_referencia: date,
    valor_realizado_atual: Decimal,
    serie_historica: list[PontoHistorico],
    n_periodos_referencia: int = 6,
) -> AnaliseMeta:
    periodos_base = serie_historica[-n_periodos_referencia:] if serie_historica else []
    valores_base = [p.valor for p in periodos_base]

    media, mediana, desvio = calcular_estatisticas(valores_base)
    tendencia = calcular_tendencia(valores_base)

    variacao_vs_media_pct: Decimal | None = None
    if media != 0:
        variacao_vs_media_pct = ((valor_realizado_atual - media) / media * 100).quantize(Decimal("0.01"))

    tempo_decorrido_pct = calcular_tempo_decorrido_pct(periodo_inicio, periodo_fim, data_referencia)
    projecao = calcular_projecao(valor_realizado_atual, tempo_decorrido_pct)
    status_ritmo = classificar_ritmo(projecao, valor_alvo, direcao_boa)

    percentual_atingido = Decimal("0")
    if valor_alvo != 0:
        percentual_atingido = (valor_realizado_atual / valor_alvo * 100).quantize(Decimal("0.01"))

    comparativo_ano_anterior_pct = comparar_sazonalidade(
        serie_historica, valor_realizado_atual, periodo_inicio.month, periodo_inicio.year
    )

    diagnostico = gerar_diagnostico(
        tendencia=tendencia,
        status_ritmo=status_ritmo,
        direcao_boa=direcao_boa,
        variacao_vs_media_pct=variacao_vs_media_pct,
        valor_alvo=valor_alvo,
        valor_realizado_atual=valor_realizado_atual,
    )

    return AnaliseMeta(
        valor_alvo=valor_alvo,
        valor_realizado_atual=valor_realizado_atual,
        percentual_atingido=percentual_atingido,
        tempo_decorrido_pct=tempo_decorrido_pct,
        status_ritmo=status_ritmo,
        tendencia=tendencia,
        media_periodos_anteriores=media,
        mediana_periodos_anteriores=mediana,
        desvio_padrao_periodos_anteriores=desvio,
        variacao_vs_media_pct=variacao_vs_media_pct,
        projecao_fim_periodo=projecao,
        diagnostico=diagnostico,
        serie_historica=serie_historica,
        comparativo_ano_anterior_pct=comparativo_ano_anterior_pct,
    )
```

Crie também `API/app/services/metas/__init__.py` vazio (pacote Python).

- [ ] **Step 4: Rodar os testes e confirmar PASS**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_analise_meta_service.py -v`
Expected: todos os 9 testes com `PASSED`. Se algum `assert` de texto do diagnóstico falhar,
ajuste a string do teste pra bater com o texto real gerado — o que importa é a classificação
(`tendencia`/`status_ritmo`), não a redação exata.

- [ ] **Step 5: Commit**

```bash
git add API/app/services/metas/analise_meta_service.py API/app/services/metas/__init__.py API/app/tests/test_analise_meta_service.py
git commit -m "feat: implementa AnaliseMetaService (motor de analise puro do modulo Metas)"
```

---

### Task 4: `IndicadoresRepository` — catálogo e histórico (leitura)

**Files:**
- Create: `API/app/repositories/metas/__init__.py` (vazio)
- Create: `API/app/repositories/metas/indicadores_repository.py`
- Test: `API/app/tests/test_indicadores_repository.py`

**Interfaces:**
- Consumes: `app.services.nfe.postres_config.carregar_config_postgres`,
  `opcoes_conexao_postgres` (mesmo padrão de `JobsRepository`, ver
  `API/app/repositories/jobs_repository.py:13,35-44`).
- Produces: `IndicadoresRepository` com `listar(perfil: str = "xml") -> list[dict]`,
  `obter_por_id(indicador_id: int) -> dict | None`,
  `historico(empresa_id: int, indicador_id: int, meses: int = 12) -> list[dict]`. Usado por
  `services/metas/metas_service.py` (Task 8) e `api/metas/indicadores_routes.py` (Task 9).

- [ ] **Step 1: Escrever o teste com conexão fake**

```python
# API/app/tests/test_indicadores_repository.py
from app.repositories.metas.indicadores_repository import IndicadoresRepository


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _FakeCursor(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_listar_filtra_por_perfil(monkeypatch):
    repo = IndicadoresRepository()
    fake_rows = [{"id": 1, "chave": "faturamento", "nome": "Faturamento", "unidade": "moeda", "direcao_boa": "maior_melhor", "perfil": "xml"}]
    fake_conn = _FakeConn(fake_rows)
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.listar(perfil="xml")

    assert resultado == fake_rows


def test_historico_retorna_lista_vazia_sem_dado(monkeypatch):
    repo = IndicadoresRepository()
    fake_conn = _FakeConn([])
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.historico(empresa_id=1, indicador_id=1, meses=12)

    assert resultado == []
```

- [ ] **Step 2: Rodar e confirmar falha por módulo ausente**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_indicadores_repository.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementar o repository**

```python
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class IndicadoresRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def _connect(self):
        last_error: Exception | None = None
        for options in opcoes_conexao_postgres(self.config):
            try:
                return psycopg.connect(**options, row_factory=dict_row)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def listar(self, perfil: str = "xml") -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, chave, nome, unidade, direcao_boa, perfil
                    FROM indicadores
                    WHERE perfil = %s AND ativo = TRUE
                    ORDER BY nome
                    """,
                    (perfil,),
                )
                return [dict(row) for row in cur.fetchall()]

    def obter_por_id(self, indicador_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, chave, nome, unidade, direcao_boa, perfil, ativo
                    FROM indicadores
                    WHERE id = %s
                    """,
                    (indicador_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def historico(self, empresa_id: int, indicador_id: int, meses: int = 12) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT periodo_referencia AS periodo, valor
                    FROM indicador_historico
                    WHERE empresa_id = %s AND indicador_id = %s
                    ORDER BY periodo_referencia DESC
                    LIMIT %s
                    """,
                    (empresa_id, indicador_id, meses),
                )
                rows = [dict(row) for row in cur.fetchall()]
        return list(reversed(rows))
```

- [ ] **Step 4: Rodar e confirmar PASS**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_indicadores_repository.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add API/app/repositories/metas/__init__.py API/app/repositories/metas/indicadores_repository.py API/app/tests/test_indicadores_repository.py
git commit -m "feat: adiciona IndicadoresRepository (catalogo e historico)"
```

---

### Task 5: `MetasHistoricoRepository` + `MetasHistoricoService` — agregação de `notas_kpis`

**Files:**
- Create: `API/app/repositories/metas/metas_historico_repository.py`
- Create: `API/app/services/metas/metas_historico_service.py`
- Test: `API/app/tests/test_metas_historico_service.py`

**Interfaces:**
- Consumes: `IndicadoresRepository.listar` (Task 4).
- Produces: `MetasHistoricoRepository.agregar_por_empresa(cnpj_normalizado: str) -> list[dict]`
  (uma linha por mês, com todas as chaves de indicador), `MetasHistoricoRepository.upsert_historico(empresa_id: int, indicador_id_por_chave: dict[str, int], linhas: list[dict]) -> int`,
  `MetasHistoricoService.materializar_empresa(empresa_id: int, cnpj: str) -> int` (retorna
  quantidade de linhas gravadas) — consumido pela task Celery na Task 6 e pela rota de análise
  na Task 9.

- [ ] **Step 1: Escrever o teste do service com repositórios fake**

```python
# API/app/tests/test_metas_historico_service.py
from decimal import Decimal

from app.services.metas.metas_historico_service import MetasHistoricoService


class FakeIndicadoresRepository:
    def __init__(self, indicadores):
        self._indicadores = indicadores

    def listar(self, perfil="xml"):
        return self._indicadores


class FakeHistoricoRepository:
    def __init__(self, linhas_agregadas):
        self._linhas_agregadas = linhas_agregadas
        self.upserts = []

    def agregar_por_empresa(self, cnpj_normalizado):
        return self._linhas_agregadas

    def upsert_historico(self, empresa_id, indicador_id_por_chave, linhas):
        self.upserts.append((empresa_id, indicador_id_por_chave, linhas))
        return len(linhas) * len(indicador_id_por_chave)


def test_materializar_empresa_grava_uma_linha_por_indicador_por_mes():
    indicadores = [
        {"id": 1, "chave": "faturamento"},
        {"id": 2, "chave": "ticket_medio"},
    ]
    linhas_agregadas = [
        {"periodo_referencia": "2026-06-01", "faturamento": Decimal("10000.00"), "ticket_medio": Decimal("500.00")},
        {"periodo_referencia": "2026-07-01", "faturamento": Decimal("12000.00"), "ticket_medio": Decimal("550.00")},
    ]
    historico_repo = FakeHistoricoRepository(linhas_agregadas)
    service = MetasHistoricoService(
        indicadores_repository=FakeIndicadoresRepository(indicadores),
        historico_repository=historico_repo,
    )

    total_gravado = service.materializar_empresa(empresa_id=1, cnpj="11111111000191")

    assert total_gravado == 4  # 2 meses x 2 indicadores
    empresa_id, indicador_id_por_chave, linhas = historico_repo.upserts[0]
    assert empresa_id == 1
    assert indicador_id_por_chave == {"faturamento": 1, "ticket_medio": 2}
    assert linhas == linhas_agregadas


def test_materializar_empresa_sem_dado_retorna_zero():
    service = MetasHistoricoService(
        indicadores_repository=FakeIndicadoresRepository([{"id": 1, "chave": "faturamento"}]),
        historico_repository=FakeHistoricoRepository([]),
    )

    total_gravado = service.materializar_empresa(empresa_id=1, cnpj="11111111000191")

    assert total_gravado == 0
```

- [ ] **Step 2: Rodar e confirmar falha por módulo ausente**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_historico_service.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.services.metas.metas_historico_service'`)

- [ ] **Step 3: Implementar o repository de agregação**

```python
# API/app/repositories/metas/metas_historico_repository.py
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class MetasHistoricoRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def _connect(self):
        last_error: Exception | None = None
        for options in opcoes_conexao_postgres(self.config):
            try:
                return psycopg.connect(**options, row_factory=dict_row)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def agregar_por_empresa(self, cnpj_normalizado: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        DATE_TRUNC('month', MAKE_DATE(periodo_ano, periodo_mes, 1))::date AS periodo_referencia,
                        SUM(total_vendas) AS faturamento,
                        SUM(quantidade_notas) AS quantidade_notas,
                        CASE WHEN SUM(quantidade_notas) > 0
                             THEN SUM(total_vendas) / SUM(quantidade_notas)
                             ELSE 0 END AS ticket_medio,
                        SUM(total_icms) AS total_icms,
                        SUM(total_ipi) AS total_ipi,
                        SUM(total_pis) + SUM(total_cofins) AS total_pis_cofins
                    FROM notas_kpis
                    WHERE regexp_replace(UPPER(COALESCE(emitente_cnpj, '')), '[^0-9A-Z]', '', 'g') = %s
                      AND periodo_ano IS NOT NULL AND periodo_mes IS NOT NULL
                    GROUP BY periodo_ano, periodo_mes
                    ORDER BY periodo_ano, periodo_mes
                    """,
                    (cnpj_normalizado,),
                )
                return [dict(row) for row in cur.fetchall()]

    def upsert_historico(
        self,
        empresa_id: int,
        indicador_id_por_chave: dict[str, int],
        linhas: list[dict[str, Any]],
    ) -> int:
        if not linhas or not indicador_id_por_chave:
            return 0

        valores: list[tuple[Any, ...]] = []
        for linha in linhas:
            for chave, indicador_id in indicador_id_por_chave.items():
                if chave not in linha:
                    continue
                valores.append((empresa_id, indicador_id, linha["periodo_referencia"], linha[chave]))

        if not valores:
            return 0

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO indicador_historico (empresa_id, indicador_id, periodo_referencia, valor)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (empresa_id, indicador_id, periodo_referencia)
                    DO UPDATE SET valor = EXCLUDED.valor, calculado_em = NOW()
                    """,
                    valores,
                )
            conn.commit()
        return len(valores)
```

- [ ] **Step 4: Implementar o service**

```python
# API/app/services/metas/metas_historico_service.py
from __future__ import annotations

from app.repositories.metas.indicadores_repository import IndicadoresRepository
from app.repositories.metas.metas_historico_repository import MetasHistoricoRepository
from app.services.nfe.empresa_service import normalizar_cnpj


class MetasHistoricoService:
    """Materializa indicador_historico a partir de notas_kpis (fonte ja persistida por import)."""

    def __init__(
        self,
        indicadores_repository: IndicadoresRepository | None = None,
        historico_repository: MetasHistoricoRepository | None = None,
    ) -> None:
        self.indicadores_repository = indicadores_repository or IndicadoresRepository()
        self.historico_repository = historico_repository or MetasHistoricoRepository()

    def materializar_empresa(self, empresa_id: int, cnpj: str) -> int:
        indicadores = self.indicadores_repository.listar(perfil="xml")
        indicador_id_por_chave = {i["chave"]: i["id"] for i in indicadores}

        linhas = self.historico_repository.agregar_por_empresa(normalizar_cnpj(cnpj))
        if not linhas:
            return 0

        return self.historico_repository.upsert_historico(empresa_id, indicador_id_por_chave, linhas)
```

- [ ] **Step 5: Rodar e confirmar PASS**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_historico_service.py -q`
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add API/app/repositories/metas/metas_historico_repository.py API/app/services/metas/metas_historico_service.py API/app/tests/test_metas_historico_service.py
git commit -m "feat: adiciona agregacao de notas_kpis para indicador_historico"
```

---

### Task 6: Task Celery `materializar_indicadores_historico_task`

**Files:**
- Create: `API/app/workers/metas_tasks.py`
- Create: `API/app/repositories/metas/empresas_repository.py`
- Modify: `API/app/workers/celery_app.py:53-81` (adicionar `app.workers.metas_tasks` em `include` e
  entrada em `beat_schedule`)
- Test: `API/app/tests/test_metas_task.py`

**Interfaces:**
- Consumes: `MetasHistoricoService.materializar_empresa` (Task 5).
- Produces: task Celery `materializar_indicadores_historico_task` (fila `default`), registrada no
  beat diariamente às 4h (o sync de KPIs de vendas do Conta Azul já roda às 3h — ver
  `celery_app.py:78`).

- [ ] **Step 1: Escrever o teste da task (mesmo padrão de `test_conta_azul_task.py`)**

```python
# API/app/tests/test_metas_task.py
from app.workers import metas_tasks


class FakeEmpresasRepository:
    def __init__(self, empresas):
        self._empresas = empresas

    def listar_empresas_xml_ativas(self):
        return self._empresas


def test_materializa_todas_empresas_xml(monkeypatch):
    monkeypatch.setattr(
        metas_tasks,
        "_repositorio_empresas",
        lambda: FakeEmpresasRepository([(1, "11111111000191"), (2, "22222222000192")]),
    )

    chamadas = []
    monkeypatch.setattr(
        metas_tasks,
        "_materializar_empresa",
        lambda empresa_id, cnpj: chamadas.append((empresa_id, cnpj)) or 4,
    )

    resultado = metas_tasks.materializar_indicadores_historico_task.run()

    assert resultado["status"] == "SUCCESS"
    assert resultado["empresas_processadas"] == 2
    assert resultado["linhas_gravadas"] == 8
    assert chamadas == [(1, "11111111000191"), (2, "22222222000192")]


def test_falha_em_uma_empresa_nao_aborta_as_demais(monkeypatch):
    monkeypatch.setattr(
        metas_tasks,
        "_repositorio_empresas",
        lambda: FakeEmpresasRepository([(1, "11111111000191"), (2, "22222222000192")]),
    )

    def _materializar(empresa_id, cnpj):
        if empresa_id == 2:
            raise RuntimeError("falha de conexao")
        return 4

    monkeypatch.setattr(metas_tasks, "_materializar_empresa", _materializar)

    resultado = metas_tasks.materializar_indicadores_historico_task.run()

    assert resultado["status"] == "SUCCESS"
    assert resultado["empresas_processadas"] == 1
    assert resultado["empresas_falha"] == 1
```

- [ ] **Step 2: Rodar e confirmar falha por módulo ausente**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_task.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.workers.metas_tasks'`)

- [ ] **Step 3: Criar o repository de empresas do worker**

Espelha `API/app/repositories/conta_azul/conta_azul_repository.py:26-34`:

```python
# API/app/repositories/metas/empresas_repository.py
from __future__ import annotations

import psycopg

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class MetasEmpresasRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def listar_empresas_xml_ativas(self) -> list[tuple[int, str]]:
        for options in opcoes_conexao_postgres(self.config):
            try:
                with psycopg.connect(**options) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id, cnpj FROM empresas WHERE tem_xml = true")
                        return cur.fetchall()
            except psycopg.Error:
                continue
        return []
```

- [ ] **Step 4: Implementar a task**

```python
# API/app/workers/metas_tasks.py
from __future__ import annotations

import logging

from app.repositories.metas.empresas_repository import MetasEmpresasRepository
from app.services.metas.metas_historico_service import MetasHistoricoService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _repositorio_empresas() -> MetasEmpresasRepository:
    return MetasEmpresasRepository()


def _materializar_empresa(empresa_id: int, cnpj: str) -> int:
    return MetasHistoricoService().materializar_empresa(empresa_id, cnpj)


@celery_app.task(name="materializar_indicadores_historico_task")
def materializar_indicadores_historico_task() -> dict:
    """Roda diariamente (via beat_schedule em celery_app.py): agrega notas_kpis por
    empresa com tem_xml=true e materializa indicador_historico. Nao recalcula de
    notas/notas_itens - so agrega o que ja esta persistido em notas_kpis.
    """
    empresas = _repositorio_empresas().listar_empresas_xml_ativas()
    resultado = {"empresas_processadas": 0, "empresas_falha": 0, "linhas_gravadas": 0}

    for empresa_id, cnpj in empresas:
        try:
            linhas_gravadas = _materializar_empresa(empresa_id, cnpj)
            resultado["empresas_processadas"] += 1
            resultado["linhas_gravadas"] += linhas_gravadas
        except Exception:
            resultado["empresas_falha"] += 1
            logger.exception(
                "metas_historico_materializacao_falhou",
                extra={"empresa_id": empresa_id, "cnpj": cnpj},
            )

    resultado["status"] = "SUCCESS"
    return resultado
```

- [ ] **Step 5: Registrar a task no `celery_app.py`**

Em `API/app/workers/celery_app.py`, no bloco `include=[...]` (linha ~53-57), adicionar:

```python
        include=[
            "app.workers.nfe_tasks",
            "app.workers.sped_tasks",
            "app.workers.conta_azul_tasks",
            "app.workers.metas_tasks",
        ],
```

E no `beat_schedule` (linha ~75-81), adicionar uma segunda entrada:

```python
        beat_schedule={
            "sincronizar-kpis-conta-azul-diario": {
                "task": "sincronizar_kpis_conta_azul_task",
                "schedule": crontab(hour=3, minute=0),
                "options": {"queue": "conta_azul"},
            },
            "materializar-indicadores-historico-diario": {
                "task": "materializar_indicadores_historico_task",
                "schedule": crontab(hour=4, minute=0),
                "options": {"queue": "default"},
            },
        },
```

- [ ] **Step 6: Rodar e confirmar PASS**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_task.py -q`
Expected: `2 passed`

- [ ] **Step 7: Rodar a suite completa (garante que o `include` novo não quebrou o import do Celery app)**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q`
Expected: todos os testes existentes continuam passando, mais os novos desta task.

- [ ] **Step 8: Commit**

```bash
git add API/app/workers/metas_tasks.py API/app/workers/celery_app.py API/app/repositories/metas/empresas_repository.py API/app/tests/test_metas_task.py
git commit -m "feat: adiciona task Celery de materializacao do indicador_historico"
```

---

### Task 7: `MetasRepository` — CRUD de `metas`

**Files:**
- Create: `API/app/repositories/metas/metas_repository.py`
- Test: `API/app/tests/test_metas_repository.py`

**Interfaces:**
- Produces: `MetasRepository` com `criar(**campos) -> dict`, `obter(meta_id: int, empresa_id: int) -> dict | None`,
  `listar(empresa_id: int, status: str | None, indicador_id: int | None) -> list[dict]`,
  `atualizar(meta_id: int, empresa_id: int, campos: dict) -> dict | None`,
  `cancelar(meta_id: int, empresa_id: int) -> bool`. Todo método recebe `empresa_id` e filtra por
  ele — nenhuma query sem esse filtro. Usado por `services/metas/metas_service.py` (Task 8).

- [ ] **Step 1: Escrever o teste com conexão fake**

```python
# API/app/tests/test_metas_repository.py
from app.repositories.metas.metas_repository import MetasRepository


class _FakeCursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def execute(self, sql, params=None):
        pass

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows

    def cursor(self):
        return _FakeCursor(row=self._row, rows=self._rows)

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_obter_filtra_por_empresa_id(monkeypatch):
    repo = MetasRepository()
    row = {"id": 1, "empresa_id": 1, "titulo": "Meta X"}
    fake_conn = _FakeConn(row=row)
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.obter(meta_id=1, empresa_id=1)

    assert resultado == row


def test_obter_retorna_none_quando_nao_encontrado(monkeypatch):
    repo = MetasRepository()
    fake_conn = _FakeConn(row=None)
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.obter(meta_id=999, empresa_id=1)

    assert resultado is None


def test_listar_retorna_linhas(monkeypatch):
    repo = MetasRepository()
    rows = [{"id": 1, "empresa_id": 1}, {"id": 2, "empresa_id": 1}]
    fake_conn = _FakeConn(rows=rows)
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.listar(empresa_id=1, status=None, indicador_id=None)

    assert resultado == rows
```

- [ ] **Step 2: Rodar e confirmar falha por módulo ausente**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_repository.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementar o repository**

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


class MetasRepository:
    def __init__(self) -> None:
        self.config = carregar_config_postgres()

    def _connect(self):
        last_error: Exception | None = None
        for options in opcoes_conexao_postgres(self.config):
            try:
                return psycopg.connect(**options, row_factory=dict_row)
            except psycopg.Error as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Configuracao PostgreSQL invalida.")

    def criar(
        self,
        *,
        empresa_id: int,
        indicador_id: int,
        titulo: str,
        descricao: str | None,
        valor_alvo: Decimal,
        tipo_meta: str,
        periodo_tipo: str,
        periodo_inicio: date,
        periodo_fim: date,
        criado_por: int,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO metas (
                        empresa_id, indicador_id, titulo, descricao, valor_alvo,
                        tipo_meta, periodo_tipo, periodo_inicio, periodo_fim, criado_por
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        empresa_id, indicador_id, titulo, descricao, valor_alvo,
                        tipo_meta, periodo_tipo, periodo_inicio, periodo_fim, criado_por,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row)

    def obter(self, meta_id: int, empresa_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM metas WHERE id = %s AND empresa_id = %s",
                    (meta_id, empresa_id),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def listar(
        self, empresa_id: int, status: str | None = None, indicador_id: int | None = None
    ) -> list[dict[str, Any]]:
        filtros = ["empresa_id = %s"]
        params: list[Any] = [empresa_id]
        if status:
            filtros.append("status = %s")
            params.append(status)
        if indicador_id:
            filtros.append("indicador_id = %s")
            params.append(indicador_id)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT * FROM metas
                    WHERE {' AND '.join(filtros)}
                    ORDER BY criado_em DESC
                    """,
                    params,
                )
                return [dict(row) for row in cur.fetchall()]

    def atualizar(self, meta_id: int, empresa_id: int, campos: dict[str, Any]) -> dict[str, Any] | None:
        if not campos:
            return self.obter(meta_id, empresa_id)

        sets = ", ".join(f"{coluna} = %s" for coluna in campos)
        params = [*campos.values(), meta_id, empresa_id]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE metas
                    SET {sets}, atualizado_em = NOW()
                    WHERE id = %s AND empresa_id = %s
                    RETURNING *
                    """,
                    params,
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row) if row else None

    def cancelar(self, meta_id: int, empresa_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE metas SET status = 'cancelada', atualizado_em = NOW()
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (meta_id, empresa_id),
                )
                encontrado = cur.rowcount > 0
            conn.commit()
        return encontrado
```

- [ ] **Step 4: Rodar e confirmar PASS**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_repository.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add API/app/repositories/metas/metas_repository.py API/app/tests/test_metas_repository.py
git commit -m "feat: adiciona MetasRepository (CRUD)"
```

---

### Task 8: `MetasService` — orquestração (CRUD + análise)

**Files:**
- Create: `API/app/services/metas/metas_service.py`
- Test: `API/app/tests/test_metas_service.py`

**Interfaces:**
- Consumes: `MetasRepository` (Task 7), `IndicadoresRepository` (Task 4),
  `analisar_meta`/`PontoHistorico` (Task 3).
- Produces: exceções `MetaNaoEncontradaError`, `IndicadorInvalidoError`; `MetasService` com
  `criar(...)`, `obter(meta_id, empresa_id)`, `listar(...)`, `atualizar(...)`, `cancelar(...)`,
  `analisar(meta_id, empresa_id, *, valor_realizado_atual, data_referencia=None) -> AnaliseMeta`.
  Consumido por `api/metas/routes.py` (Task 9), que converte as exceções em `HTTPException`.

- [ ] **Step 1: Escrever os testes com repositórios fake**

```python
# API/app/tests/test_metas_service.py
from datetime import date
from decimal import Decimal

import pytest

from app.services.metas.metas_service import IndicadorInvalidoError, MetaNaoEncontradaError, MetasService


class FakeMetasRepository:
    def __init__(self, metas=None):
        self._metas = metas or {}
        self._next_id = max(self._metas.keys(), default=0) + 1

    def criar(self, **campos):
        meta_id = self._next_id
        self._next_id += 1
        meta = {"id": meta_id, "status": "ativa", "criado_em": "2026-08-13T00:00:00", "atualizado_em": "2026-08-13T00:00:00", **campos}
        self._metas[meta_id] = meta
        return meta

    def obter(self, meta_id, empresa_id):
        meta = self._metas.get(meta_id)
        if not meta or meta["empresa_id"] != empresa_id:
            return None
        return meta

    def listar(self, empresa_id, status=None, indicador_id=None):
        return [m for m in self._metas.values() if m["empresa_id"] == empresa_id]

    def atualizar(self, meta_id, empresa_id, campos):
        meta = self.obter(meta_id, empresa_id)
        if not meta:
            return None
        meta.update(campos)
        return meta

    def cancelar(self, meta_id, empresa_id):
        meta = self.obter(meta_id, empresa_id)
        if not meta:
            return False
        meta["status"] = "cancelada"
        return True


class FakeIndicadoresRepository:
    def __init__(self, indicadores):
        self._indicadores = {i["id"]: i for i in indicadores}

    def obter_por_id(self, indicador_id):
        return self._indicadores.get(indicador_id)

    def historico(self, empresa_id, indicador_id, meses=12):
        return []


def _service(metas=None, indicadores=None):
    return MetasService(
        metas_repository=FakeMetasRepository(metas),
        indicadores_repository=FakeIndicadoresRepository(indicadores or [{"id": 1, "chave": "faturamento", "direcao_boa": "maior_melhor", "ativo": True}]),
    )


def test_criar_meta_com_indicador_valido():
    service = _service()

    meta = service.criar(
        empresa_id=1,
        indicador_id=1,
        titulo="Crescer faturamento",
        descricao=None,
        valor_alvo=Decimal("50000.00"),
        tipo_meta="crescimento",
        periodo_tipo="mensal",
        periodo_inicio=date(2026, 8, 1),
        periodo_fim=date(2026, 8, 31),
        criado_por=1,
    )

    assert meta["indicador_id"] == 1
    assert meta["empresa_id"] == 1


def test_criar_meta_com_indicador_inexistente_levanta_erro():
    service = _service(indicadores=[])

    with pytest.raises(IndicadorInvalidoError):
        service.criar(
            empresa_id=1,
            indicador_id=999,
            titulo="Meta invalida",
            descricao=None,
            valor_alvo=Decimal("1000.00"),
            tipo_meta="crescimento",
            periodo_tipo="mensal",
            periodo_inicio=date(2026, 8, 1),
            periodo_fim=date(2026, 8, 31),
            criado_por=1,
        )


def test_obter_meta_de_outra_empresa_levanta_nao_encontrada():
    service = _service(metas={1: {"id": 1, "empresa_id": 2, "indicador_id": 1, "titulo": "X", "valor_alvo": Decimal("100"), "periodo_inicio": date(2026, 8, 1), "periodo_fim": date(2026, 8, 31), "status": "ativa"}})

    with pytest.raises(MetaNaoEncontradaError):
        service.obter(meta_id=1, empresa_id=1)


def test_analisar_meta_usa_indicador_e_historico():
    metas = {
        1: {
            "id": 1, "empresa_id": 1, "indicador_id": 1, "titulo": "X",
            "valor_alvo": Decimal("50000.00"), "periodo_inicio": date(2026, 8, 1),
            "periodo_fim": date(2026, 8, 31), "status": "ativa",
        }
    }
    service = _service(metas=metas)

    analise = service.analisar(meta_id=1, empresa_id=1, valor_realizado_atual=Decimal("30000.00"), data_referencia=date(2026, 8, 20))

    assert analise.valor_alvo == Decimal("50000.00")
```

- [ ] **Step 2: Rodar e confirmar falha por módulo ausente**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_service.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementar o service**

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.repositories.metas.indicadores_repository import IndicadoresRepository
from app.repositories.metas.metas_repository import MetasRepository
from app.services.metas.analise_meta_service import AnaliseMeta, PontoHistorico, analisar_meta


class MetaNaoEncontradaError(Exception):
    pass


class IndicadorInvalidoError(Exception):
    pass


class MetasService:
    def __init__(
        self,
        metas_repository: MetasRepository | None = None,
        indicadores_repository: IndicadoresRepository | None = None,
    ) -> None:
        self.metas_repository = metas_repository or MetasRepository()
        self.indicadores_repository = indicadores_repository or IndicadoresRepository()

    def _validar_indicador(self, indicador_id: int) -> dict[str, Any]:
        indicador = self.indicadores_repository.obter_por_id(indicador_id)
        if not indicador or not indicador.get("ativo", True):
            raise IndicadorInvalidoError(f"Indicador {indicador_id} nao existe ou esta inativo.")
        return indicador

    def criar(
        self,
        *,
        empresa_id: int,
        indicador_id: int,
        titulo: str,
        descricao: str | None,
        valor_alvo: Decimal,
        tipo_meta: str,
        periodo_tipo: str,
        periodo_inicio: date,
        periodo_fim: date,
        criado_por: int,
    ) -> dict[str, Any]:
        self._validar_indicador(indicador_id)
        return self.metas_repository.criar(
            empresa_id=empresa_id,
            indicador_id=indicador_id,
            titulo=titulo,
            descricao=descricao,
            valor_alvo=valor_alvo,
            tipo_meta=tipo_meta,
            periodo_tipo=periodo_tipo,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            criado_por=criado_por,
        )

    def obter(self, meta_id: int, empresa_id: int) -> dict[str, Any]:
        meta = self.metas_repository.obter(meta_id, empresa_id)
        if not meta:
            raise MetaNaoEncontradaError(f"Meta {meta_id} nao encontrada.")
        return meta

    def listar(self, empresa_id: int, status: str | None = None, indicador_id: int | None = None) -> list[dict[str, Any]]:
        return self.metas_repository.listar(empresa_id, status=status, indicador_id=indicador_id)

    def atualizar(self, meta_id: int, empresa_id: int, campos: dict[str, Any]) -> dict[str, Any]:
        self.obter(meta_id, empresa_id)
        meta = self.metas_repository.atualizar(meta_id, empresa_id, campos)
        if not meta:
            raise MetaNaoEncontradaError(f"Meta {meta_id} nao encontrada.")
        return meta

    def cancelar(self, meta_id: int, empresa_id: int) -> None:
        self.obter(meta_id, empresa_id)
        if not self.metas_repository.cancelar(meta_id, empresa_id):
            raise MetaNaoEncontradaError(f"Meta {meta_id} nao encontrada.")

    def analisar(
        self,
        meta_id: int,
        empresa_id: int,
        *,
        valor_realizado_atual: Decimal,
        data_referencia: date | None = None,
    ) -> AnaliseMeta:
        meta = self.obter(meta_id, empresa_id)
        indicador = self._validar_indicador(meta["indicador_id"])

        n_periodos = 4 if meta["periodo_tipo"] == "trimestral" else 6
        historico_bruto = self.indicadores_repository.historico(
            empresa_id=empresa_id, indicador_id=meta["indicador_id"], meses=max(n_periodos, 12)
        )
        serie_historica = [PontoHistorico(periodo=p["periodo"], valor=Decimal(str(p["valor"]))) for p in historico_bruto]

        return analisar_meta(
            valor_alvo=Decimal(str(meta["valor_alvo"])),
            direcao_boa=indicador["direcao_boa"],
            periodo_inicio=meta["periodo_inicio"],
            periodo_fim=meta["periodo_fim"],
            data_referencia=data_referencia or date.today(),
            valor_realizado_atual=valor_realizado_atual,
            serie_historica=serie_historica,
            n_periodos_referencia=n_periodos,
        )
```

- [ ] **Step 4: Rodar e confirmar PASS**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_service.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add API/app/services/metas/metas_service.py API/app/tests/test_metas_service.py
git commit -m "feat: adiciona MetasService (orquestracao CRUD e analise)"
```

---

### Task 9: Endpoints `/api/metas` e `/api/indicadores`

**Files:**
- Create: `API/app/api/metas/__init__.py` (vazio)
- Create: `API/app/api/metas/routes.py`
- Create: `API/app/api/metas/indicadores_routes.py`
- Modify: `API/app/api/routes.py` (registrar os dois novos routers)

**Interfaces:**
- Consumes: `MetasService` (Task 8), `IndicadoresRepository` (Task 4), `MetasHistoricoRepository`
  (Task 5), schemas da Task 2, `AuthenticatedUser`/`get_current_user` (`app.core.security`).
- Produces: rotas HTTP montadas em `/api/metas` e `/api/indicadores`, registradas no
  `api_router` agregador consumido por `app/main.py:86`.

**Nota de dado real (`valor_realizado_atual`):** o endpoint `/api/metas/{id}/analise` precisa do
valor já realizado no período corrente da meta. Essa informação vem do mesmo `notas_kpis`
agregado pro mês corrente — reaproveita `MetasHistoricoRepository.agregar_por_empresa`
(Task 5) filtrando a linha cujo `periodo_referencia` cai dentro de `[periodo_inicio, periodo_fim]`
da meta. Se não houver linha (mês corrente ainda sem KPI calculado), usa `Decimal("0")`.

- [ ] **Step 1: Implementar `routes.py`**

```python
# API/app/api/metas/routes.py
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import AuthenticatedUser, get_current_user
from app.models.metas.schemas import (
    AnaliseMetaResponse,
    IndicadorHistoricoPontoResponse,
    MetaCreateRequest,
    MetaListResponse,
    MetaResponse,
    MetaUpdateRequest,
)
from app.repositories.metas.metas_historico_repository import MetasHistoricoRepository
from app.services.metas.metas_service import IndicadorInvalidoError, MetaNaoEncontradaError, MetasService
from app.services.nfe.empresa_service import normalizar_cnpj

router = APIRouter(prefix="/metas", tags=["Metas"])

_metas_service: MetasService | None = None


def get_metas_service() -> MetasService:
    global _metas_service
    if _metas_service is None:
        _metas_service = MetasService()
    return _metas_service


def _valor_realizado_atual(indicador_chave: str, periodo_inicio: date, periodo_fim: date, cnpj: str) -> Decimal:
    linhas = MetasHistoricoRepository().agregar_por_empresa(normalizar_cnpj(cnpj))
    for linha in linhas:
        periodo_referencia = linha["periodo_referencia"]
        if periodo_inicio <= periodo_referencia <= periodo_fim and indicador_chave in linha:
            return Decimal(str(linha[indicador_chave]))
    return Decimal("0")


@router.post("", response_model=MetaResponse, status_code=status.HTTP_201_CREATED)
def criar_meta(
    payload: MetaCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    try:
        meta = service.criar(
            empresa_id=current_user.empresa_id,
            indicador_id=payload.indicador_id,
            titulo=payload.titulo,
            descricao=payload.descricao,
            valor_alvo=payload.valor_alvo,
            tipo_meta=payload.tipo_meta.value,
            periodo_tipo=payload.periodo_tipo.value,
            periodo_inicio=payload.periodo_inicio,
            periodo_fim=payload.periodo_fim,
            criado_por=current_user.login_id,
        )
    except IndicadorInvalidoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MetaResponse(**meta)


@router.get("", response_model=MetaListResponse)
def listar_metas(
    status_filter: str | None = Query(default=None, alias="status"),
    indicador_id: int | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    resultados = service.listar(current_user.empresa_id, status=status_filter, indicador_id=indicador_id)
    return MetaListResponse(total=len(resultados), resultados=[MetaResponse(**m) for m in resultados])


@router.get("/{meta_id}", response_model=MetaResponse)
def obter_meta(
    meta_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    try:
        meta = service.obter(meta_id, current_user.empresa_id)
    except MetaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada.") from exc
    return MetaResponse(**meta)


@router.patch("/{meta_id}", response_model=MetaResponse)
def atualizar_meta(
    meta_id: int,
    payload: MetaUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    campos = {chave: (valor.value if hasattr(valor, "value") else valor) for chave, valor in payload.model_dump(exclude_unset=True).items()}
    try:
        meta = service.atualizar(meta_id, current_user.empresa_id, campos)
    except MetaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada.") from exc
    return MetaResponse(**meta)


@router.delete("/{meta_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_meta(
    meta_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    try:
        service.cancelar(meta_id, current_user.empresa_id)
    except MetaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada.") from exc


@router.get("/{meta_id}/analise", response_model=AnaliseMetaResponse)
def analisar_meta_endpoint(
    meta_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: MetasService = Depends(get_metas_service),
):
    try:
        meta = service.obter(meta_id, current_user.empresa_id)
    except MetaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada.") from exc

    indicador = service.indicadores_repository.obter_por_id(meta["indicador_id"])
    valor_atual = _valor_realizado_atual(
        indicador["chave"], meta["periodo_inicio"], meta["periodo_fim"], current_user.cnpj
    )

    analise = service.analisar(meta_id, current_user.empresa_id, valor_realizado_atual=valor_atual)

    return AnaliseMetaResponse(
        meta_id=meta_id,
        valor_alvo=analise.valor_alvo,
        valor_realizado_atual=analise.valor_realizado_atual,
        percentual_atingido=analise.percentual_atingido,
        tempo_decorrido_pct=analise.tempo_decorrido_pct,
        status_ritmo=analise.status_ritmo.value,
        tendencia=analise.tendencia.value,
        media_periodos_anteriores=analise.media_periodos_anteriores,
        mediana_periodos_anteriores=analise.mediana_periodos_anteriores,
        desvio_padrao_periodos_anteriores=analise.desvio_padrao_periodos_anteriores,
        variacao_vs_media_pct=analise.variacao_vs_media_pct,
        diagnostico=analise.diagnostico,
        serie_historica=[IndicadorHistoricoPontoResponse(periodo=p.periodo, valor=p.valor) for p in analise.serie_historica],
        projecao_fim_periodo=analise.projecao_fim_periodo,
        comparativo_ano_anterior_pct=analise.comparativo_ano_anterior_pct,
    )
```

- [ ] **Step 2: Implementar `indicadores_routes.py`**

```python
# API/app/api/metas/indicadores_routes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.security import AuthenticatedUser, get_current_user
from app.models.metas.schemas import IndicadorHistoricoPontoResponse, IndicadorHistoricoResponse, IndicadorListResponse, IndicadorResponse
from app.repositories.metas.indicadores_repository import IndicadoresRepository

router = APIRouter(prefix="/indicadores", tags=["Indicadores"])

_indicadores_repository: IndicadoresRepository | None = None


def get_indicadores_repository() -> IndicadoresRepository:
    global _indicadores_repository
    if _indicadores_repository is None:
        _indicadores_repository = IndicadoresRepository()
    return _indicadores_repository


@router.get("", response_model=IndicadorListResponse)
def listar_indicadores(
    perfil: str = Query(default="xml"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: IndicadoresRepository = Depends(get_indicadores_repository),
):
    resultados = repository.listar(perfil=perfil)
    return IndicadorListResponse(resultados=[IndicadorResponse(**i) for i in resultados])


@router.get("/{indicador_id}/historico", response_model=IndicadorHistoricoResponse)
def historico_indicador(
    indicador_id: int,
    meses: int = Query(default=12, ge=1, le=36),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: IndicadoresRepository = Depends(get_indicadores_repository),
):
    resultados = repository.historico(empresa_id=current_user.empresa_id, indicador_id=indicador_id, meses=meses)
    return IndicadorHistoricoResponse(
        indicador_id=indicador_id,
        resultados=[IndicadorHistoricoPontoResponse(periodo=r["periodo"], valor=r["valor"]) for r in resultados],
    )
```

- [ ] **Step 3: Registrar os routers no agregador**

Editar `API/app/api/routes.py`, adicionando os imports:

```python
from app.api.metas.routes import router as metas_router
from app.api.metas.indicadores_routes import router as indicadores_router
```

E as chamadas de registro:

```python
router.include_router(metas_router)
router.include_router(indicadores_router)
```

- [ ] **Step 4: Rodar a suite completa pra garantir que a aplicação sobe sem erro de import**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q`
Expected: nenhuma falha de import/coleta nova (os testes de rota vêm na Task 10).

- [ ] **Step 5: Commit**

```bash
git add API/app/api/metas API/app/api/routes.py
git commit -m "feat: adiciona endpoints /api/metas e /api/indicadores"
```

---

### Task 10: Testes de integração das rotas

**Files:**
- Create: `API/app/tests/test_metas_routes.py`

**Interfaces:**
- Consumes: fixture `client` de `API/app/tests/conftest.py` (usuário `empresa_id=1`), monkeypatch
  em `app.api.metas.routes.get_metas_service` e `app.api.metas.indicadores_routes.get_indicadores_repository`.

- [ ] **Step 1: Escrever os testes de rota com serviço/repositório fake**

```python
# API/app/tests/test_metas_routes.py
from datetime import date, datetime
from decimal import Decimal

from app.api.metas import indicadores_routes, routes as metas_routes
from app.services.metas.metas_service import IndicadorInvalidoError, MetaNaoEncontradaError


class FakeMetasService:
    def __init__(self):
        self.metas = {}
        self._next_id = 1
        self.indicadores_repository = FakeIndicadoresRepository()

    def criar(self, **campos):
        meta_id = self._next_id
        self._next_id += 1
        if campos["indicador_id"] != 1:
            raise IndicadorInvalidoError("indicador invalido")
        meta = {
            "id": meta_id,
            "criado_em": datetime(2026, 8, 13),
            "atualizado_em": datetime(2026, 8, 13),
            "status": "ativa",
            **campos,
        }
        self.metas[meta_id] = meta
        return meta

    def obter(self, meta_id, empresa_id):
        meta = self.metas.get(meta_id)
        if not meta or meta["empresa_id"] != empresa_id:
            raise MetaNaoEncontradaError("nao encontrada")
        return meta

    def listar(self, empresa_id, status=None, indicador_id=None):
        return [m for m in self.metas.values() if m["empresa_id"] == empresa_id]

    def atualizar(self, meta_id, empresa_id, campos):
        meta = self.obter(meta_id, empresa_id)
        meta.update(campos)
        return meta

    def cancelar(self, meta_id, empresa_id):
        meta = self.obter(meta_id, empresa_id)
        meta["status"] = "cancelada"

    def analisar(self, meta_id, empresa_id, *, valor_realizado_atual, data_referencia=None):
        from app.services.metas.analise_meta_service import AnaliseMeta, StatusRitmo, Tendencia

        meta = self.obter(meta_id, empresa_id)
        return AnaliseMeta(
            valor_alvo=meta["valor_alvo"],
            valor_realizado_atual=valor_realizado_atual,
            percentual_atingido=Decimal("62.00"),
            tempo_decorrido_pct=Decimal("70.00"),
            status_ritmo=StatusRitmo.EM_RISCO,
            tendencia=Tendencia.QUEDA_LEVE,
            media_periodos_anteriores=Decimal("33500.00"),
            mediana_periodos_anteriores=Decimal("33000.00"),
            desvio_padrao_periodos_anteriores=Decimal("1000.00"),
            variacao_vs_media_pct=Decimal("-7.50"),
            projecao_fim_periodo=Decimal("43500.00"),
            diagnostico="Você está 7.5% abaixo da média dos períodos anteriores.",
            serie_historica=[],
            comparativo_ano_anterior_pct=None,
        )


class FakeIndicadoresRepository:
    def obter_por_id(self, indicador_id):
        return {"id": indicador_id, "chave": "faturamento", "direcao_boa": "maior_melhor", "ativo": True}

    def listar(self, perfil="xml"):
        return [{"id": 1, "chave": "faturamento", "nome": "Faturamento", "unidade": "moeda", "direcao_boa": "maior_melhor", "perfil": "xml"}]

    def historico(self, empresa_id, indicador_id, meses=12):
        return [{"periodo": date(2026, 7, 1), "valor": Decimal("1000.00")}]


def _payload_meta_valida():
    return {
        "indicador_id": 1,
        "titulo": "Crescer faturamento",
        "valor_alvo": "50000.00",
        "tipo_meta": "crescimento",
        "periodo_tipo": "mensal",
        "periodo_inicio": "2026-08-01",
        "periodo_fim": "2026-08-31",
    }


def test_criar_meta(client, monkeypatch):
    fake_service = FakeMetasService()
    client.app.dependency_overrides[metas_routes.get_metas_service] = lambda: fake_service

    response = client.post("/api/metas", json=_payload_meta_valida())

    assert response.status_code == 201
    assert response.json()["indicador_id"] == 1


def test_criar_meta_com_indicador_invalido_retorna_400(client):
    fake_service = FakeMetasService()
    client.app.dependency_overrides[metas_routes.get_metas_service] = lambda: fake_service

    payload = _payload_meta_valida()
    payload["indicador_id"] = 999
    response = client.post("/api/metas", json=payload)

    assert response.status_code == 400


def test_criar_meta_com_periodo_invalido_retorna_422(client):
    payload = _payload_meta_valida()
    payload["periodo_inicio"] = "2026-08-31"
    payload["periodo_fim"] = "2026-08-01"

    response = client.post("/api/metas", json=payload)

    assert response.status_code == 422


def test_obter_meta_de_outra_empresa_retorna_404(client):
    fake_service = FakeMetasService()
    fake_service.metas[1] = {
        "id": 1, "empresa_id": 999, "indicador_id": 1, "titulo": "Outra empresa",
        "descricao": None, "valor_alvo": Decimal("100.00"), "tipo_meta": "crescimento",
        "periodo_tipo": "mensal", "periodo_inicio": date(2026, 8, 1), "periodo_fim": date(2026, 8, 31),
        "status": "ativa", "criado_em": datetime(2026, 8, 13), "atualizado_em": datetime(2026, 8, 13),
    }
    client.app.dependency_overrides[metas_routes.get_metas_service] = lambda: fake_service

    response = client.get("/api/metas/1")

    assert response.status_code == 404


def test_analise_meta(client, monkeypatch):
    fake_service = FakeMetasService()
    fake_service.metas[1] = fake_service.criar(
        empresa_id=1, indicador_id=1, titulo="Crescer", descricao=None,
        valor_alvo=Decimal("50000.00"), tipo_meta="crescimento", periodo_tipo="mensal",
        periodo_inicio=date(2026, 8, 1), periodo_fim=date(2026, 8, 31), criado_por=1,
    )
    client.app.dependency_overrides[metas_routes.get_metas_service] = lambda: fake_service
    monkeypatch.setattr(
        metas_routes.MetasHistoricoRepository,
        "agregar_por_empresa",
        lambda self, cnpj: [{"periodo_referencia": date(2026, 8, 1), "faturamento": Decimal("31000.00")}],
    )

    response = client.get("/api/metas/1/analise")

    assert response.status_code == 200
    assert response.json()["status_ritmo"] == "em_risco"


def test_listar_indicadores(client):
    client.app.dependency_overrides[indicadores_routes.get_indicadores_repository] = lambda: FakeIndicadoresRepository()

    response = client.get("/api/indicadores")

    assert response.status_code == 200
    assert response.json()["resultados"][0]["chave"] == "faturamento"


def test_historico_indicador(client):
    client.app.dependency_overrides[indicadores_routes.get_indicadores_repository] = lambda: FakeIndicadoresRepository()

    response = client.get("/api/indicadores/1/historico")

    assert response.status_code == 200
    assert response.json()["resultados"][0]["valor"] == "1000.00"
```

- [ ] **Step 2: Rodar e ajustar até tudo passar**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests/test_metas_routes.py -v`
Expected: todos os testes `PASSED`. Ponto de atenção: `client.app.dependency_overrides[...]`
sobrescreve por cima do que `conftest.py` já define pra `get_current_user`/
`require_company_scope` — não remova essas duas entradas ao configurar os overrides desta task.

- [ ] **Step 3: Rodar a suite completa do backend**

Run: `cd API && .\.venv-local\Scripts\python.exe -m pytest app/tests -q`
Expected: `passed` para toda a suite, sem nenhuma regressão nos testes pré-existentes.

- [ ] **Step 4: Commit**

```bash
git add API/app/tests/test_metas_routes.py
git commit -m "test: adiciona testes de integracao das rotas de Metas"
```

---

### Task 11: Documentação — `docs/api-contracts.md` e `docs/database.md`

**Files:**
- Modify: `docs/api-contracts.md`
- Modify: `docs/database.md`

- [ ] **Step 1: Adicionar seção de contrato em `docs/api-contracts.md`**

Inserir no fim do arquivo (mesmo estilo das seções existentes):

```markdown
## Metas

### `POST /api/metas`

- Autenticacao: sessao ativa. Escopo por `current_user.empresa_id` (sem `empresa_id` de query).
- Body obrigatorio: `indicador_id`, `titulo`, `valor_alvo`, `tipo_meta`, `periodo_tipo`, `periodo_inicio`, `periodo_fim`.
- Body opcional: `descricao`.
- Erros: `400` indicador inexistente/inativo, `422` `periodo_fim < periodo_inicio` ou `valor_alvo <= 0`.

### `GET /api/metas?status=&indicador_id=`

- Lista metas da empresa da sessao, mais recentes primeiro.

### `GET /api/metas/{id}`

- `404` se a meta nao existe ou pertence a outra empresa.

### `GET /api/metas/{id}/analise`

- Retorna `AnaliseMetaResponse`: `percentual_atingido`, `tempo_decorrido_pct`, `status_ritmo`
  (`no_caminho`/`em_risco`/`fora_da_rota`), `tendencia` (5 faixas), `diagnostico` (texto gerado
  por template), `serie_historica`, `projecao_fim_periodo`, `comparativo_ano_anterior_pct`
  (`null` se histórico < 12 meses).

### `PATCH /api/metas/{id}`

- Body opcional: `titulo`, `descricao`, `valor_alvo`, `status`.

### `DELETE /api/metas/{id}`

- Soft delete (`status = 'cancelada'`). Responde `204`.

### `GET /api/indicadores?perfil=xml`

- Catálogo fixo (seed via migration). Nesta fase só `perfil=xml` tem dado.

### `GET /api/indicadores/{id}/historico?meses=12`

- Série mensal de `indicador_historico`, ordenada por período ascendente. Materializada pela
  task Celery `materializar_indicadores_historico_task` (diária, 4h) a partir de `notas_kpis`.
```

- [ ] **Step 2: Adicionar as tabelas novas em `docs/database.md`**

Na seção "Tabelas por origem de criacao" > "Criadas ou alteradas por migrations manuais",
adicionar:

```markdown
- Alembic `20260813_0012`: cria `indicadores` (catálogo fixo, seed de 6 indicadores XML),
  `indicador_historico` (materializado por `materializar_indicadores_historico_task`, fonte
  `notas_kpis`) e `metas`.
```

- [ ] **Step 3: Commit**

```bash
git add docs/api-contracts.md docs/database.md
git commit -m "docs: documenta contratos e tabelas do modulo Metas"
```

---

## Self-Review (executado ao escrever este plano)

**Cobertura do spec:** catálogo de indicadores → Task 1 (seed). Modelo de dados → Task 1.
Job de materialização → Tasks 5/6. `AnaliseMetaService` (estatística, tendência, projeção,
diagnóstico, sazonalidade) → Task 3. Endpoints → Tasks 9/10. Erros HTTP → Tasks 9/10 (400/404/422).
Testes (unitários puros + repository + rota) → Tasks 3/4/5/6/7/8/10. Fora de escopo (frontend,
SPED, LLM, alerta) → não implementado, conforme spec.

**Placeholders:** nenhum `TBD`/`TODO` — todo step tem código completo.

**Consistência de tipos:** `PontoHistorico`, `AnaliseMeta`, `Tendencia`, `StatusRitmo` definidos
na Task 3 e reusados com os mesmos nomes nas Tasks 8, 9 e 10. `IndicadoresRepository.historico`
retorna `periodo`/`valor` (Task 4) — é o mesmo shape consumido em `MetasService.analisar` (Task 8)
e no teste de rota (Task 10). `MetasHistoricoRepository.agregar_por_empresa` retorna
`periodo_referencia` + uma chave por indicador (`faturamento`, `ticket_medio`, etc.) — mesmo shape
usado em `MetasHistoricoRepository.upsert_historico` (Task 5) e em `_valor_realizado_atual`
(Task 9).
